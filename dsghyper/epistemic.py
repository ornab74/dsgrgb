from __future__ import annotations

"""Deterministic epistemic routing for DSG HyperCommunication v22.

The mesh is deliberately ordinary software. It does not infer truth from agreement.
It converts immutable agent artifacts into a bounded claim graph, resolves explicit
support/challenge/dependency edges, routes only role-relevant prior information, and
produces a calibrated quorum summary for Sync.
"""

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .protocol import (
    AgentResult,
    Challenge,
    Claim,
    InformationRequest,
    Relation,
    Spectrum,
    WORKERS,
    digest_json,
    safe_text,
)


@dataclass(frozen=True, slots=True)
class CommunicationBudget:
    max_claims: int = 12
    max_chars: int = 18000
    max_requests: int = 8
    max_peer_notes: int = 8
    max_peer_note_chars: int = 6000
    max_sync_claims: int = 48


@dataclass(frozen=True, slots=True)
class ClaimNode:
    global_id: str
    round_no: int
    agent: str
    claim: Claim

    def public_dict(self) -> dict[str, Any]:
        return {
            "global_id": self.global_id,
            "round": self.round_no,
            "agent": self.agent,
            **asdict(self.claim),
        }


@dataclass(frozen=True, slots=True)
class GraphEdge:
    actor: str
    kind: str
    source_claim_id: str | None
    target_claim_id: str
    confidence: float
    reason: str = ""
    round_no: int = 0


@dataclass(frozen=True, slots=True)
class RoutedRequest:
    requester: str
    recipient: str
    question: str
    reason: str
    utility: float
    related_claim_id: str | None
    round_no: int


@dataclass(slots=True)
class RoutingMetrics:
    claim_deliveries: int = 0
    request_deliveries: int = 0
    delivered_chars: int = 0
    dropped_claims_budget: int = 0
    dropped_requests_budget: int = 0
    unresolved_relations: int = 0
    unresolved_challenges: int = 0


@dataclass(frozen=True, slots=True)
class IngestReport:
    accepted_claims: int
    accepted_relations: int
    accepted_challenges: int
    accepted_requests: int
    resolved_challenges: tuple[GraphEdge, ...]


class EpistemicMesh:
    RELATION_KINDS = {"supports", "contradicts", "depends_on", "refines", "duplicates"}

    def __init__(self, budget: CommunicationBudget | None = None):
        self.budget = budget or CommunicationBudget()
        self.nodes: dict[str, ClaimNode] = {}
        self.edges: list[GraphEdge] = []
        self.requests: list[RoutedRequest] = []
        self._latest_by_local: dict[tuple[str, str], str] = {}
        self.metrics = RoutingMetrics()

    @staticmethod
    def _global_id(round_no: int, agent: str, claim_id: str) -> str:
        local = safe_text(claim_id or "claim", 96).replace(" ", "_")
        return f"r{round_no}:{agent}:{local}"

    def _resolve_claim(self, ref: str | None, *, actor: str | None = None) -> str | None:
        if not ref:
            return None
        ref = safe_text(ref, 180)
        if ref in self.nodes:
            return ref
        if actor and (actor, ref) in self._latest_by_local:
            return self._latest_by_local[(actor, ref)]
        matches = [gid for (agent, local), gid in self._latest_by_local.items() if local == ref]
        return matches[-1] if len(matches) == 1 else None

    def ingest_round(self, round_no: int, results: dict[str, AgentResult]) -> IngestReport:
        accepted_claims = 0
        for agent, result in results.items():
            seen_local: set[str] = set()
            for claim in result.claims:
                local_id = claim.claim_id
                if local_id in seen_local:
                    continue
                seen_local.add(local_id)
                gid = self._global_id(round_no, agent, local_id)
                node = ClaimNode(gid, round_no, agent, claim)
                self.nodes[gid] = node
                self._latest_by_local[(agent, local_id)] = gid
                accepted_claims += 1

        accepted_relations = 0
        accepted_challenges: list[GraphEdge] = []
        accepted_requests = 0
        for agent, result in results.items():
            for relation in result.relations:
                source = self._resolve_claim(relation.source_claim_id, actor=agent)
                target = self._resolve_claim(relation.target_claim_id)
                if relation.kind not in self.RELATION_KINDS or target is None:
                    self.metrics.unresolved_relations += 1
                    continue
                edge = GraphEdge(
                    actor=agent,
                    kind=relation.kind,
                    source_claim_id=source,
                    target_claim_id=target,
                    confidence=relation.confidence,
                    reason=relation.reason,
                    round_no=round_no,
                )
                self.edges.append(edge)
                accepted_relations += 1

            for challenge in result.challenges:
                target = self._resolve_challenge_target(challenge)
                if target is None:
                    self.metrics.unresolved_challenges += 1
                    continue
                edge = GraphEdge(
                    actor=agent,
                    kind="challenges",
                    source_claim_id=None,
                    target_claim_id=target,
                    confidence=challenge.confidence * challenge.severity,
                    reason=challenge.reason,
                    round_no=round_no,
                )
                self.edges.append(edge)
                accepted_challenges.append(edge)

            for request in result.information_requests:
                related = self._resolve_claim(request.related_claim_id, actor=agent)
                self.requests.append(RoutedRequest(
                    requester=agent,
                    recipient=request.recipient,
                    question=request.question,
                    reason=request.reason,
                    utility=request.utility,
                    related_claim_id=related,
                    round_no=round_no,
                ))
                accepted_requests += 1

        return IngestReport(
            accepted_claims=accepted_claims,
            accepted_relations=accepted_relations,
            accepted_challenges=len(accepted_challenges),
            accepted_requests=accepted_requests,
            resolved_challenges=tuple(accepted_challenges),
        )

    def _resolve_challenge_target(self, challenge: Challenge) -> str | None:
        if challenge.claim_id in self.nodes:
            node = self.nodes[challenge.claim_id]
            return challenge.claim_id if node.agent == challenge.target_agent else None
        return self._latest_by_local.get((challenge.target_agent, challenge.claim_id))

    @staticmethod
    def _influence_value(influence: dict[str, Any], agent: str) -> float:
        value = influence.get(agent, 0.7)
        if isinstance(value, dict):
            value = value.get("influence", 0.7)
        try:
            return max(0.1, min(0.95, float(value)))
        except (TypeError, ValueError):
            return 0.7

    def quorum(self, claim_id: str, influence: dict[str, Any]) -> dict[str, Any]:
        node = self.nodes[claim_id]
        author_weight = self._influence_value(influence, node.agent)
        support = node.claim.confidence * author_weight
        challenge = 0.0
        supporters = {node.agent}
        challengers: set[str] = set()
        dependencies = 0
        for edge in self.edges:
            if edge.target_claim_id != claim_id:
                continue
            actor_weight = self._influence_value(influence, edge.actor)
            mass = edge.confidence * actor_weight
            if edge.kind in {"supports", "refines"}:
                support += mass
                supporters.add(edge.actor)
            elif edge.kind in {"contradicts", "challenges"}:
                challenge += mass
                challengers.add(edge.actor)
            elif edge.kind == "depends_on":
                dependencies += 1
        total = support + challenge
        net = support / total if total > 1e-9 else 0.5
        diversity = len(supporters | challengers)
        if challenge > 0.2 and support > 0.2:
            status = "contested"
        elif support >= 0.9 and diversity >= 2:
            status = "cross_supported"
        elif support >= 0.45:
            status = "provisional"
        else:
            status = "weak"
        return {
            "claim_id": claim_id,
            "status": status,
            "support_mass": round(support, 4),
            "challenge_mass": round(challenge, 4),
            "support_fraction": round(net, 4),
            "review_diversity": diversity,
            "dependencies": dependencies,
            "supporters": sorted(supporters),
            "challengers": sorted(challengers),
        }

    def _claim_route_score(self, node: ClaimNode, recipient: str, spectrum: Spectrum, influence: dict[str, Any]) -> float:
        q = self.quorum(node.global_id, influence)
        evidence_strength = min(1.0, len(node.claim.evidence) / 3.0)
        contested = 1.0 if q["status"] == "contested" else 0.0
        age_bonus = min(0.25, node.round_no * 0.03)
        author_weight = self._influence_value(influence, node.agent)
        base = 0.28 * node.claim.salience + 0.23 * node.claim.confidence + 0.12 * evidence_strength + 0.10 * author_weight + age_bonus

        if recipient == "red":
            role = 0.28 * node.claim.salience + (0.12 if node.agent in {"green", "gamma"} else 0.0)
        elif recipient == "green":
            role = 0.24 if node.agent == "red" else 0.10 * q["support_fraction"]
        elif recipient == "blue":
            role = 0.30 * (1.0 - evidence_strength) + 0.24 * contested + 0.08 * node.claim.confidence
        elif recipient == "gamma":
            role = 0.25 * contested + (0.14 if q["review_diversity"] >= 2 else 0.0)
        else:
            role = 0.0
        spectrum_weight = getattr(spectrum, recipient, 0.2)
        return base + role + 0.12 * spectrum_weight

    def _requests_for(self, recipient: str, current_round: int) -> list[dict[str, Any]]:
        candidates = [r for r in self.requests if r.recipient == recipient and r.round_no < current_round]
        candidates.sort(key=lambda r: (r.utility, r.round_no), reverse=True)
        delivered: list[dict[str, Any]] = []
        for request in candidates[: self.budget.max_requests]:
            delivered.append(asdict(request))
            self.metrics.request_deliveries += 1
        if len(candidates) > self.budget.max_requests:
            self.metrics.dropped_requests_budget += len(candidates) - self.budget.max_requests
        return delivered

    def route_for(self, recipient: str, *, current_round: int, spectrum: Spectrum, influence: dict[str, Any]) -> dict[str, Any]:
        if recipient not in WORKERS:
            return {"claims": [], "information_requests": [], "budget": {}}
        candidates = [node for node in self.nodes.values() if node.round_no < current_round]
        ranked = sorted(candidates, key=lambda node: self._claim_route_score(node, recipient, spectrum, influence), reverse=True)
        selected: list[dict[str, Any]] = []
        used_chars = 0
        for node in ranked:
            if len(selected) >= self.budget.max_claims:
                self.metrics.dropped_claims_budget += 1
                continue
            item = {
                "claim": node.public_dict(),
                "quorum": self.quorum(node.global_id, influence),
                "route_score": round(self._claim_route_score(node, recipient, spectrum, influence), 4),
            }
            size = len(str(item))
            if used_chars + size > self.budget.max_chars:
                self.metrics.dropped_claims_budget += 1
                continue
            selected.append(item)
            used_chars += size
            self.metrics.claim_deliveries += 1
            self.metrics.delivered_chars += size
        return {
            "claims": selected,
            "information_requests": self._requests_for(recipient, current_round),
            "budget": {
                "max_claims": self.budget.max_claims,
                "max_chars": self.budget.max_chars,
                "used_claims": len(selected),
                "used_chars": used_chars,
            },
        }

    def sync_summary(self, influence: dict[str, Any]) -> dict[str, Any]:
        ranked = sorted(
            self.nodes.values(),
            key=lambda n: (n.claim.salience * 0.55 + n.claim.confidence * 0.45) * self._influence_value(influence, n.agent),
            reverse=True,
        )[: self.budget.max_sync_claims]
        claims = [{"claim": node.public_dict(), "quorum": self.quorum(node.global_id, influence)} for node in ranked]
        contested = [item for item in claims if item["quorum"]["status"] == "contested"]
        unresolved_requests = [asdict(r) for r in self.requests[-self.budget.max_requests :]]
        summary = {
            "claims": claims,
            "contested_claims": contested[:16],
            "recent_information_requests": unresolved_requests,
            "graph": {
                "claim_nodes": len(self.nodes),
                "edges": len(self.edges),
                "information_requests": len(self.requests),
                "digest": self.digest(influence),
            },
        }
        return summary

    def digest(self, influence: dict[str, Any]) -> str:
        material = {
            "nodes": [node.public_dict() for node in self.nodes.values()],
            "edges": [asdict(edge) for edge in self.edges],
            "requests": [asdict(request) for request in self.requests],
            "influence": influence,
        }
        return digest_json(material)

    def metrics_dict(self) -> dict[str, Any]:
        return {
            **asdict(self.metrics),
            "claim_nodes": len(self.nodes),
            "edges": len(self.edges),
            "information_requests": len(self.requests),
        }
