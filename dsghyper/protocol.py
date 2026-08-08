from __future__ import annotations

import hashlib
import json
import math
import re
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

AGENTS = ("red", "green", "blue", "gamma", "sync")
WORKERS = ("red", "green", "blue", "gamma")
RELATION_KINDS = ("supports", "contradicts", "depends_on", "refines", "duplicates")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = lo
    return max(lo, min(hi, value))


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_json(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def safe_text(value: Any, limit: int = 20000) -> str:
    text = value if isinstance(value, str) else stable_json(value)
    return text.replace("\x00", "")[: max(0, int(limit))]


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


@dataclass(frozen=True, slots=True)
class Spectrum:
    red: float = 0.2
    green: float = 0.2
    blue: float = 0.2
    gamma: float = 0.2
    sync: float = 0.2

    def normalized(self) -> "Spectrum":
        values = [max(0.0, float(v)) for v in asdict(self).values()]
        total = sum(values) or 1.0
        return Spectrum(*(v / total for v in values))

    def entropy(self) -> float:
        values = asdict(self.normalized()).values()
        return -sum(v * math.log2(v) for v in values if v > 1e-12) / math.log2(5)

    def dominant(self) -> str:
        values = asdict(self.normalized())
        return max(values, key=values.get)

    @classmethod
    def infer(cls, text: str) -> "Spectrum":
        lower = text.lower()
        groups = {
            "red": ("urgent", "risk", "attack", "failure", "danger", "blocker", "threat"),
            "green": ("build", "design", "plan", "improve", "solution", "recover", "implement"),
            "blue": ("verify", "evidence", "check", "source", "test", "prove", "audit"),
            "gamma": ("novel", "connect", "combine", "cross", "discover", "invent", "emergent"),
            "sync": ("final", "decide", "consensus", "summary", "choose", "answer", "reconcile"),
        }
        scores = {name: 1.0 + sum(lower.count(token) for token in tokens) for name, tokens in groups.items()}
        return cls(**scores).normalized()


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    text: str
    provenance: str = "INFERRED"

    @classmethod
    def from_any(cls, value: Any) -> "EvidenceRef":
        if isinstance(value, dict):
            return cls(safe_text(value.get("text", value), 1200), safe_text(value.get("provenance", "INFERRED"), 80))
        return cls(safe_text(value, 1200), "INFERRED")


@dataclass(frozen=True, slots=True)
class Claim:
    claim_id: str
    text: str
    confidence: float
    provenance: str
    evidence: tuple[EvidenceRef, ...] = ()
    salience: float = 0.5

    @classmethod
    def from_any(cls, value: Any, index: int) -> "Claim":
        if not isinstance(value, dict):
            return cls(f"claim_{index}", safe_text(value, 2500), 0.35, "INFERRED", (), 0.5)
        evidence_raw = value.get("evidence", [])
        if not isinstance(evidence_raw, list):
            evidence_raw = [evidence_raw]
        return cls(
            safe_text(value.get("claim_id", f"claim_{index}"), 120),
            safe_text(value.get("text", ""), 2500),
            clamp(value.get("confidence", 0.5)),
            safe_text(value.get("provenance", "INFERRED"), 80),
            tuple(EvidenceRef.from_any(item) for item in evidence_raw[:12]),
            clamp(value.get("salience", 0.5)),
        )


@dataclass(frozen=True, slots=True)
class Challenge:
    target_agent: str
    claim_id: str
    reason: str
    severity: float
    confidence: float

    @classmethod
    def from_any(cls, value: Any) -> "Challenge | None":
        if not isinstance(value, dict):
            return None
        target = safe_text(value.get("target_agent", ""), 32).lower()
        if target not in AGENTS:
            return None
        return cls(
            target,
            safe_text(value.get("claim_id", "unknown"), 180),
            safe_text(value.get("reason", ""), 2000),
            clamp(value.get("severity", 0.5)),
            clamp(value.get("confidence", 0.5)),
        )


@dataclass(frozen=True, slots=True)
class Relation:
    kind: str
    source_claim_id: str | None
    target_claim_id: str
    reason: str
    confidence: float

    @classmethod
    def from_any(cls, value: Any) -> "Relation | None":
        if not isinstance(value, dict):
            return None
        kind = safe_text(value.get("kind", ""), 32).lower()
        if kind not in RELATION_KINDS:
            return None
        target = safe_text(value.get("target_claim_id", ""), 180)
        if not target:
            return None
        source = safe_text(value.get("source_claim_id", ""), 180) or None
        return cls(kind, source, target, safe_text(value.get("reason", ""), 1600), clamp(value.get("confidence", 0.5)))


@dataclass(frozen=True, slots=True)
class InformationRequest:
    recipient: str
    question: str
    reason: str
    utility: float
    related_claim_id: str | None = None

    @classmethod
    def from_any(cls, value: Any) -> "InformationRequest | None":
        if not isinstance(value, dict):
            return None
        recipient = safe_text(value.get("recipient", ""), 32).lower()
        if recipient not in WORKERS:
            return None
        question = safe_text(value.get("question", ""), 1800)
        if not question:
            return None
        return cls(
            recipient,
            question,
            safe_text(value.get("reason", ""), 1200),
            clamp(value.get("utility", 0.5)),
            safe_text(value.get("related_claim_id", ""), 180) or None,
        )


@dataclass(frozen=True, slots=True)
class PeerNote:
    recipient: str
    topic: str
    content: str
    priority: int = 50

    @classmethod
    def from_any(cls, value: Any) -> "PeerNote | None":
        if not isinstance(value, dict):
            return None
        recipient = safe_text(value.get("recipient", value.get("to", "")), 32).lower()
        if isinstance(value.get("to"), list):
            to_list = value.get("to") or []
            recipient = safe_text(to_list[0], 32).lower() if to_list else ""
        if recipient not in WORKERS:
            return None
        try:
            priority = max(1, min(100, int(value.get("priority", 50))))
        except (TypeError, ValueError):
            priority = 50
        return cls(recipient, safe_text(value.get("topic", "peer.note"), 120), safe_text(value.get("content", ""), 4000), priority)


@dataclass(frozen=True, slots=True)
class AgentResult:
    agent: str
    answer: str
    claims: tuple[Claim, ...]
    challenges: tuple[Challenge, ...]
    uncertainties: tuple[str, ...]
    next_checks: tuple[str, ...]
    peer_notes: tuple[PeerNote, ...]
    confidence: float
    relations: tuple[Relation, ...] = ()
    information_requests: tuple[InformationRequest, ...] = ()
    status: str = "ok"
    error: str | None = None
    result_id: str = field(default_factory=lambda: new_id("result"))
    created_at: str = field(default_factory=utc_now)

    @classmethod
    def from_model(cls, agent: str, data: Any) -> "AgentResult":
        if not isinstance(data, dict):
            data = {"answer": safe_text(data)}
        claims_raw = data.get("claims", [])
        challenges_raw = data.get("challenges", [])
        relations_raw = data.get("relations", [])
        requests_raw = data.get("information_requests", [])
        notes_raw = data.get("peer_notes", data.get("messages", []))
        uncertainties = data.get("uncertainties", [])
        checks = data.get("next_checks", [])
        if not isinstance(claims_raw, list): claims_raw = [claims_raw]
        if not isinstance(challenges_raw, list): challenges_raw = [challenges_raw]
        if not isinstance(relations_raw, list): relations_raw = [relations_raw]
        if not isinstance(requests_raw, list): requests_raw = [requests_raw]
        if not isinstance(notes_raw, list): notes_raw = [notes_raw]
        if not isinstance(uncertainties, list): uncertainties = [uncertainties]
        if not isinstance(checks, list): checks = [checks]
        challenges = [Challenge.from_any(x) for x in challenges_raw[:24]]
        relations = [Relation.from_any(x) for x in relations_raw[:32]]
        requests = [InformationRequest.from_any(x) for x in requests_raw[:16]]
        notes = [PeerNote.from_any(x) for x in notes_raw[:16]]
        return cls(
            agent=agent,
            answer=safe_text(data.get("answer", ""), 12000),
            claims=tuple(Claim.from_any(x, i) for i, x in enumerate(claims_raw[:32], 1)),
            challenges=tuple(x for x in challenges if x is not None),
            uncertainties=tuple(safe_text(x, 1600) for x in uncertainties[:16]),
            next_checks=tuple(safe_text(x, 1600) for x in checks[:16]),
            peer_notes=tuple(x for x in notes if x is not None),
            confidence=clamp(data.get("confidence", 0.5)),
            relations=tuple(x for x in relations if x is not None),
            information_requests=tuple(x for x in requests if x is not None),
            status=safe_text(data.get("status", "ok"), 32),
            error=safe_text(data.get("error", ""), 2000) or None,
        )

    @classmethod
    def failure(cls, agent: str, error: str, status: str = "error") -> "AgentResult":
        return cls(
            agent=agent,
            answer="",
            claims=(),
            challenges=(),
            uncertainties=("agent execution failed",),
            next_checks=(),
            peer_notes=(),
            confidence=0.0,
            relations=(),
            information_requests=(),
            status=safe_text(status, 32),
            error=safe_text(error, 2000),
        )

    def public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MessageEnvelope:
    message_id: str
    trace_id: str
    round_no: int
    sender: str
    recipient: str
    topic: str
    content_hash: str
    priority: int
    created_at: str
    provenance: str

    @classmethod
    def from_note(cls, trace_id: str, round_no: int, sender: str, note: PeerNote) -> "MessageEnvelope":
        return cls(new_id("msg"), trace_id, round_no, sender, note.recipient, note.topic, hashlib.sha256(note.content.encode("utf-8")).hexdigest(), note.priority, utc_now(), "AGENT_NOTE")


def parse_json_object(text: str, max_chars: int = 100000) -> dict[str, Any]:
    raw = safe_text(text, max_chars).strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {"answer": safe_text(value)}
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            try:
                value = json.loads(raw[start:end + 1])
                return value if isinstance(value, dict) else {"answer": safe_text(value)}
            except Exception:
                pass
    return {"answer": raw, "status": "parse_warning", "confidence": 0.2}
