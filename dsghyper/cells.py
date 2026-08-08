from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import Any, Sequence

from .model import ModelClient
from .protocol import AgentResult, safe_text
from .research import MultiModelQuorum, QuorumReport, SpecialistPlan


SPECIALIST_SYSTEM = """
You are a bounded conflict-resolution specialist. Work only on the assigned claim and objective.
Do not broaden scope, invent external evidence, or override the primary worker roles.
Return exactly one JSON object with answer, claims, relations, challenges,
information_requests, uncertainties, next_checks, peer_notes, confidence, and status.
Your output is advisory evidence for Sync, not authority and not a replacement worker result.
""".strip()


QUORUM_SYSTEM = """
You are an independent quorum-cell reviewer. Analyze the supplied Sync packet independently.
Do not coordinate with other quorum models and do not infer truth from expected agreement.
Return exactly one JSON object with answer, claims, relations, challenges,
information_requests, uncertainties, next_checks, peer_notes, confidence, and status.
""".strip()


@dataclass(frozen=True, slots=True)
class SpecialistExecution:
    specialist_id: str
    role: str
    target_claim_id: str
    result: AgentResult
    token_cap: int


@dataclass(frozen=True, slots=True)
class SpecialistBatch:
    enabled: bool
    executions: tuple[SpecialistExecution, ...]
    quota_tokens: int
    tokens_reserved: int
    skipped: tuple[str, ...]

    def public_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "quota_tokens": self.quota_tokens,
            "tokens_reserved": self.tokens_reserved,
            "skipped": list(self.skipped),
            "executions": [
                {
                    "specialist_id": x.specialist_id,
                    "role": x.role,
                    "target_claim_id": x.target_claim_id,
                    "token_cap": x.token_cap,
                    "result": x.result.public_dict(),
                }
                for x in self.executions
            ],
        }


class SpecialistExecutor:
    def __init__(
        self,
        model: ModelClient,
        *,
        enabled: bool = False,
        max_specialists: int = 2,
        total_token_quota: int = 3000,
        timeout: float = 120.0,
    ):
        self.model = model
        self.enabled = bool(enabled)
        self.max_specialists = max(0, min(8, int(max_specialists)))
        self.total_token_quota = max(0, int(total_token_quota))
        self.timeout = max(1.0, float(timeout))

    async def execute(
        self,
        plans: Sequence[SpecialistPlan],
        *,
        task: str,
        epistemic_context: dict[str, Any],
    ) -> SpecialistBatch:
        if not self.enabled or not plans or self.max_specialists <= 0 or self.total_token_quota < 128:
            return SpecialistBatch(False, (), self.total_token_quota, 0, tuple(plan.specialist_id for plan in plans))

        selected: list[tuple[SpecialistPlan, int]] = []
        skipped: list[str] = []
        remaining = self.total_token_quota
        for plan in plans[: self.max_specialists]:
            cap = max(128, min(plan.quota_cost, remaining, self.model.config.max_output_tokens))
            if remaining < 128:
                skipped.append(plan.specialist_id)
                continue
            selected.append((plan, cap))
            remaining -= cap
        skipped.extend(plan.specialist_id for plan in plans[len(selected): self.max_specialists])

        async def one(plan: SpecialistPlan, cap: int) -> SpecialistExecution:
            packet = {
                "task": safe_text(task, self.model.config.max_prompt_chars),
                "specialist": asdict(plan),
                "epistemic_context": epistemic_context,
                "instruction": "Resolve this one conflict with the highest-information analysis possible inside the quota.",
            }
            try:
                result = await asyncio.wait_for(
                    self.model.invoke(
                        f"specialist:{plan.role}",
                        SPECIALIST_SYSTEM,
                        packet,
                        max_tokens_override=cap,
                    ),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                result = AgentResult.failure(f"specialist:{plan.role}", "specialist timeout", status="timeout")
            return SpecialistExecution(plan.specialist_id, plan.role, plan.target_claim_id, result, cap)

        executions = await asyncio.gather(*(one(plan, cap) for plan, cap in selected))
        return SpecialistBatch(True, tuple(executions), self.total_token_quota, sum(cap for _, cap in selected), tuple(skipped))


@dataclass(frozen=True, slots=True)
class QuorumCellResult:
    active: bool
    configured_models: tuple[str, ...]
    model_results: tuple[tuple[str, AgentResult], ...]
    report: QuorumReport
    timed_out_models: tuple[str, ...]

    def public_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "configured_models": list(self.configured_models),
            "timed_out_models": list(self.timed_out_models),
            "report": {
                "votes": [asdict(v) for v in self.report.votes],
                "response_diversity": self.report.response_diversity,
                "confidence_mean": self.report.confidence_mean,
                "status_counts": self.report.status_counts,
                "quorum_digest": self.report.quorum_digest,
            },
            "model_results": [
                {"model": model_id, "result": result.public_dict()}
                for model_id, result in self.model_results
            ],
            "truth_probability": None,
            "note": "Quorum diversity/agreement is diagnostic bookkeeping, not a truth probability.",
        }


class QuorumCell:
    def __init__(
        self,
        model: ModelClient,
        model_ids: Sequence[str],
        *,
        max_models: int = 4,
        timeout: float = 120.0,
        max_tokens_per_model: int = 1600,
    ):
        self.model = model
        unique: list[str] = []
        for item in model_ids:
            item = safe_text(item, 160).strip()
            if item and item not in unique:
                unique.append(item)
        self.model_ids = tuple(unique[: max(0, min(8, int(max_models)))])
        self.timeout = max(1.0, float(timeout))
        self.max_tokens_per_model = max(128, min(model.config.max_output_tokens, int(max_tokens_per_model)))
        self.quorum = MultiModelQuorum()

    async def evaluate(self, packet: dict[str, Any]) -> QuorumCellResult:
        if not self.model_ids:
            empty = self.quorum.summarize([])
            return QuorumCellResult(False, (), (), empty, ())

        async def one(model_id: str) -> tuple[str, AgentResult, bool]:
            try:
                result = await asyncio.wait_for(
                    self.model.invoke(
                        "sync",
                        QUORUM_SYSTEM,
                        packet,
                        model_override=model_id,
                        max_tokens_override=self.max_tokens_per_model,
                    ),
                    timeout=self.timeout,
                )
                return model_id, result, False
            except asyncio.TimeoutError:
                return model_id, AgentResult.failure("sync", f"quorum model {model_id} timeout", status="timeout"), True

        rows = await asyncio.gather(*(one(model_id) for model_id in self.model_ids))
        pairs = tuple((model_id, result) for model_id, result, _ in rows)
        timed_out = tuple(model_id for model_id, _, timeout in rows if timeout)
        return QuorumCellResult(True, self.model_ids, pairs, self.quorum.summarize(pairs), timed_out)
