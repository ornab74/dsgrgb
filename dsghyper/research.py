from __future__ import annotations

"""v23 communication research primitives.

Implemented here:
- claim freshness/expiry scoring;
- deterministic information-market allocation under hard budgets;
- claim-level causal credit propagation over an epistemic graph;
- conflict-focused specialist planning with hard quotas;
- multi-model quorum bookkeeping (adapter-agnostic; not truth probability);
- proof-carrying policy envelopes using HMAC authentication;
- deterministic replay snapshots and counterfactual budget evaluation;
- capability/status contracts for threshold/PQ/ORAM/PIR/ZK backends.

The module never labels an unavailable cryptographic/privacy primitive as active.
"""

import hashlib
import hmac
import json
import math
import secrets
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Protocol, Sequence

from .protocol import AgentResult, clamp, digest_json, safe_text, stable_json


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    ttl_rounds: int = 4
    half_life_rounds: float = 2.0
    min_freshness: float = 0.08

    def score(self, created_round: int, current_round: int) -> float:
        age = max(0, int(current_round) - int(created_round))
        if age > max(0, self.ttl_rounds):
            return 0.0
        half = max(0.25, float(self.half_life_rounds))
        value = 2.0 ** (-age / half)
        return round(max(self.min_freshness, min(1.0, value)), 6)

    def expired(self, created_round: int, current_round: int) -> bool:
        return max(0, int(current_round) - int(created_round)) > max(0, self.ttl_rounds)


@dataclass(frozen=True, slots=True)
class MarketBid:
    bid_id: str
    sender: str
    recipient: str
    artifact_id: str
    utility: float
    confidence: float
    salience: float
    freshness: float
    estimated_tokens: int
    payload: dict[str, Any]

    @property
    def score(self) -> float:
        benefit = (
            0.34 * clamp(self.utility)
            + 0.24 * clamp(self.confidence)
            + 0.22 * clamp(self.salience)
            + 0.20 * clamp(self.freshness)
        )
        cost = max(1, int(self.estimated_tokens))
        return benefit / math.sqrt(cost)


@dataclass(frozen=True, slots=True)
class MarketAllocation:
    recipient: str
    token_budget: int
    tokens_used: int
    winners: tuple[MarketBid, ...]
    rejected: tuple[str, ...]
    allocation_digest: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "recipient": self.recipient,
            "token_budget": self.token_budget,
            "tokens_used": self.tokens_used,
            "winners": [
                {
                    "bid_id": bid.bid_id,
                    "sender": bid.sender,
                    "artifact_id": bid.artifact_id,
                    "utility": bid.utility,
                    "confidence": bid.confidence,
                    "salience": bid.salience,
                    "freshness": bid.freshness,
                    "estimated_tokens": bid.estimated_tokens,
                    "market_score": round(bid.score, 8),
                    "payload": bid.payload,
                }
                for bid in self.winners
            ],
            "rejected": list(self.rejected),
            "allocation_digest": self.allocation_digest,
        }


class InformationMarket:
    """Deterministic utility-per-cost allocation; no currency or learning side effects."""

    def __init__(self, token_budget: int = 4096, max_winners: int = 16):
        self.token_budget = max(128, int(token_budget))
        self.max_winners = max(1, min(128, int(max_winners)))

    def allocate(self, recipient: str, bids: Iterable[MarketBid]) -> MarketAllocation:
        candidates = [bid for bid in bids if bid.recipient == recipient and bid.estimated_tokens > 0]
        candidates.sort(key=lambda b: (-b.score, b.bid_id))
        winners: list[MarketBid] = []
        rejected: list[str] = []
        used = 0
        for bid in candidates:
            if len(winners) >= self.max_winners or used + bid.estimated_tokens > self.token_budget:
                rejected.append(bid.bid_id)
                continue
            winners.append(bid)
            used += bid.estimated_tokens
        digest = digest_json({
            "recipient": recipient,
            "token_budget": self.token_budget,
            "tokens_used": used,
            "winners": [b.bid_id for b in winners],
            "rejected": rejected,
        })
        return MarketAllocation(recipient, self.token_budget, used, tuple(winners), tuple(rejected), digest)


@dataclass(frozen=True, slots=True)
class CausalCredit:
    claim_id: str
    direct_credit: float
    propagated_credit: float
    total_credit: float
    paths: int


class CausalCreditEngine:
    """Bounded graph credit assignment, not proof of real-world causality."""

    POSITIVE = {"supports": 0.72, "refines": 0.82, "depends_on": 0.55}
    NEGATIVE = {"contradicts": -0.55, "challenges": -0.40}

    def assign(
        self,
        claim_ids: Sequence[str],
        edges: Sequence[Any],
        selected_claim_ids: Iterable[str],
        *,
        max_depth: int = 4,
        decay: float = 0.68,
    ) -> dict[str, CausalCredit]:
        selected = set(selected_claim_ids)
        incoming: dict[str, list[tuple[str, float]]] = {cid: [] for cid in claim_ids}
        for edge in edges:
            source = getattr(edge, "source_claim_id", None)
            target = getattr(edge, "target_claim_id", None)
            kind = getattr(edge, "kind", "")
            confidence = clamp(getattr(edge, "confidence", 0.5))
            if not source or source not in incoming or target not in incoming:
                continue
            weight = self.POSITIVE.get(kind, self.NEGATIVE.get(kind, 0.0)) * confidence
            if weight:
                incoming[target].append((source, weight))

        propagated = {cid: 0.0 for cid in claim_ids}
        paths = {cid: 0 for cid in claim_ids}
        frontier = [(cid, 1.0, 0, frozenset({cid})) for cid in selected if cid in incoming]
        while frontier:
            target, mass, depth, visited = frontier.pop(0)
            if depth >= max_depth:
                continue
            for source, edge_weight in incoming.get(target, []):
                if source in visited:
                    continue
                contribution = mass * edge_weight * (decay ** (depth + 1))
                propagated[source] += contribution
                paths[source] += 1
                frontier.append((source, contribution, depth + 1, visited | {source}))

        output: dict[str, CausalCredit] = {}
        for cid in claim_ids:
            direct = 1.0 if cid in selected else 0.0
            prop = max(-1.0, min(1.0, propagated[cid]))
            total = max(-1.0, min(1.0, direct + prop))
            output[cid] = CausalCredit(cid, round(direct, 6), round(prop, 6), round(total, 6), paths[cid])
        return output


@dataclass(frozen=True, slots=True)
class SpecialistPlan:
    specialist_id: str
    target_claim_id: str
    role: str
    objective: str
    quota_cost: int
    conflict_score: float


class SpecialistScheduler:
    """Plans bounded specialists. It does not spawn unbounded autonomous processes."""

    ROLE_ORDER = ("verifier", "causal-auditor", "evidence-auditor", "counterexample")

    def __init__(self, max_specialists: int = 2, token_quota: int = 3000, min_conflict: float = 0.35):
        self.max_specialists = max(0, min(8, int(max_specialists)))
        self.token_quota = max(0, int(token_quota))
        self.min_conflict = clamp(min_conflict)

    def plan(self, contested_claims: Sequence[dict[str, Any]]) -> tuple[SpecialistPlan, ...]:
        ranked: list[tuple[float, str]] = []
        for item in contested_claims:
            quorum = item.get("quorum", {}) if isinstance(item, dict) else {}
            cid = str(quorum.get("claim_id") or item.get("claim", {}).get("global_id") or "")
            support = float(quorum.get("support_mass", 0.0) or 0.0)
            challenge = float(quorum.get("challenge_mass", 0.0) or 0.0)
            diversity = float(quorum.get("review_diversity", 0.0) or 0.0)
            conflict = min(1.0, min(support, challenge) + 0.08 * diversity)
            if cid and conflict >= self.min_conflict:
                ranked.append((conflict, cid))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        remaining = self.token_quota
        plans: list[SpecialistPlan] = []
        for index, (score, cid) in enumerate(ranked[: self.max_specialists]):
            if remaining < 512:
                break
            quota = min(1500, remaining)
            role = self.ROLE_ORDER[index % len(self.ROLE_ORDER)]
            plans.append(SpecialistPlan(
                specialist_id=f"spec_{index + 1}_{hashlib.sha256(cid.encode()).hexdigest()[:8]}",
                target_claim_id=cid,
                role=role,
                objective=f"Resolve the highest-information uncertainty around {cid} without broadening scope.",
                quota_cost=quota,
                conflict_score=round(score, 6),
            ))
            remaining -= quota
        return tuple(plans)


@dataclass(frozen=True, slots=True)
class QuorumVote:
    model_id: str
    result_digest: str
    confidence: float
    status: str
    answer_fingerprint: str


@dataclass(frozen=True, slots=True)
class QuorumReport:
    votes: tuple[QuorumVote, ...]
    response_diversity: float
    confidence_mean: float
    status_counts: dict[str, int]
    quorum_digest: str


class MultiModelQuorum:
    """Bookkeeping over independently produced results; never a truth oracle."""

    def summarize(self, model_results: Sequence[tuple[str, AgentResult]]) -> QuorumReport:
        votes: list[QuorumVote] = []
        statuses: dict[str, int] = {}
        fingerprints: set[str] = set()
        confidences: list[float] = []
        for model_id, result in model_results:
            fingerprint = hashlib.sha256(result.answer.strip().lower().encode()).hexdigest()[:16]
            fingerprints.add(fingerprint)
            confidences.append(result.confidence)
            statuses[result.status] = statuses.get(result.status, 0) + 1
            votes.append(QuorumVote(
                model_id=safe_text(model_id, 120),
                result_digest=digest_json(result.public_dict()),
                confidence=result.confidence,
                status=result.status,
                answer_fingerprint=fingerprint,
            ))
        n = len(votes)
        diversity = len(fingerprints) / n if n else 0.0
        mean = sum(confidences) / n if n else 0.0
        digest = digest_json([asdict(v) for v in votes])
        return QuorumReport(tuple(votes), round(diversity, 6), round(mean, 6), statuses, digest)


@dataclass(frozen=True, slots=True)
class PolicyEnvelope:
    envelope_id: str
    sender: str
    audience: str
    purpose: str
    operations: tuple[str, ...]
    payload_digest: str
    issued_at: int
    expires_at: int
    nonce: str
    policy_digest: str
    authenticator: str


class PolicyEnvelopeAuthority:
    """HMAC-authenticated policy envelope. Not zero-knowledge and not threshold auth."""

    def __init__(self, key: bytes):
        if len(key) < 32:
            raise ValueError("policy envelope key must be at least 32 bytes")
        self.key = key
        self.seen_nonces: set[str] = set()

    def issue(self, *, sender: str, audience: str, purpose: str, operations: Iterable[str], payload: Any, ttl_seconds: int = 300) -> PolicyEnvelope:
        issued = int(time.time())
        expires = issued + max(1, min(86400, int(ttl_seconds)))
        nonce = secrets.token_hex(16)
        body = {
            "envelope_id": "policy_" + secrets.token_hex(10),
            "sender": safe_text(sender, 120),
            "audience": safe_text(audience, 120),
            "purpose": safe_text(purpose, 240),
            "operations": sorted(set(safe_text(x, 80) for x in operations)),
            "payload_digest": digest_json(payload),
            "issued_at": issued,
            "expires_at": expires,
            "nonce": nonce,
        }
        policy_digest = digest_json(body)
        auth = hmac.new(self.key, policy_digest.encode(), hashlib.sha256).hexdigest()
        return PolicyEnvelope(**body, policy_digest=policy_digest, authenticator=auth)

    def verify(self, envelope: PolicyEnvelope, *, audience: str, operation: str, payload: Any, consume_nonce: bool = False) -> bool:
        if int(time.time()) > envelope.expires_at:
            return False
        if envelope.audience not in {"*", audience} or operation not in envelope.operations:
            return False
        if digest_json(payload) != envelope.payload_digest:
            return False
        body = {k: v for k, v in asdict(envelope).items() if k not in {"policy_digest", "authenticator"}}
        if digest_json(body) != envelope.policy_digest:
            return False
        expected = hmac.new(self.key, envelope.policy_digest.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, envelope.authenticator):
            return False
        if consume_nonce:
            if envelope.nonce in self.seen_nonces:
                return False
            self.seen_nonces.add(envelope.nonce)
        return True


@dataclass(frozen=True, slots=True)
class SecurityCapability:
    name: str
    implemented: bool
    active: bool
    backend: str | None
    guarantee: str
    warning: str | None = None


class AdvancedSecuritySurface:
    """Truthful capability registry for research-grade optional backends."""

    def __init__(self):
        self._caps: dict[str, SecurityCapability] = {
            "threshold_authenticated_identity": SecurityCapability(
                "threshold_authenticated_identity", False, False, None,
                "No threshold signature guarantee is provided.",
                "Interface reserved; requires a vetted threshold-signature backend.",
            ),
            "post_quantum_transport_identity": SecurityCapability(
                "post_quantum_transport_identity", False, False, None,
                "No post-quantum transport-authentication guarantee is provided.",
                "Requires a vetted ML-DSA/ML-KEM or equivalent hybrid backend.",
            ),
            "oram_access_pattern_hiding": SecurityCapability(
                "oram_access_pattern_hiding", False, False, None,
                "No ORAM access-pattern hiding is provided.",
                "Current semantic routing leaks timing/count/similarity access structure.",
            ),
            "pir_private_retrieval": SecurityCapability(
                "pir_private_retrieval", False, False, None,
                "No PIR query privacy is provided.",
                "Requires a real PIR backend and protocol integration.",
            ),
            "zero_knowledge_authorization": SecurityCapability(
                "zero_knowledge_authorization", False, False, None,
                "No zero-knowledge authorization proof is provided.",
                "Current policy envelopes are HMAC-authenticated attestations, not ZK proofs.",
            ),
        }

    def register_backend(self, name: str, *, backend: str, guarantee: str) -> None:
        if name not in self._caps:
            raise KeyError(name)
        self._caps[name] = SecurityCapability(name, True, True, safe_text(backend, 160), safe_text(guarantee, 400), None)

    def status(self) -> dict[str, Any]:
        return {name: asdict(cap) for name, cap in self._caps.items()}


@dataclass(frozen=True, slots=True)
class ReplaySnapshot:
    trace_id: str
    request_digest: str
    mesh_digest: str
    influence_digest: str
    market_digests: tuple[str, ...]
    final_digest: str
    snapshot_digest: str


class DeterministicReplay:
    def capture(self, *, trace_id: str, request: str, mesh_digest: str, influence: Any, allocations: Sequence[MarketAllocation], final: AgentResult) -> ReplaySnapshot:
        body = {
            "trace_id": trace_id,
            "request_digest": hashlib.sha256(request.encode()).hexdigest(),
            "mesh_digest": mesh_digest,
            "influence_digest": digest_json(influence),
            "market_digests": [a.allocation_digest for a in allocations],
            "final_digest": digest_json(final.public_dict()),
        }
        return ReplaySnapshot(**body, snapshot_digest=digest_json(body))

    def compare(self, left: ReplaySnapshot, right: ReplaySnapshot) -> dict[str, Any]:
        fields = ("request_digest", "mesh_digest", "influence_digest", "market_digests", "final_digest")
        differences = [field for field in fields if getattr(left, field) != getattr(right, field)]
        return {
            "deterministic_match": not differences,
            "differences": differences,
            "left": left.snapshot_digest,
            "right": right.snapshot_digest,
        }

    def counterfactual_market(self, recipient: str, bids: Sequence[MarketBid], budgets: Iterable[int]) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []
        for budget in sorted(set(max(128, int(x)) for x in budgets)):
            allocation = InformationMarket(token_budget=budget).allocate(recipient, bids)
            reports.append({
                "budget": budget,
                "tokens_used": allocation.tokens_used,
                "winner_ids": [bid.bid_id for bid in allocation.winners],
                "allocation_digest": allocation.allocation_digest,
            })
        return reports


class QuorumModelAdapter(Protocol):
    async def invoke(self, agent: str, system: str, packet: dict[str, Any]) -> AgentResult: ...
