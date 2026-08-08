from __future__ import annotations

"""Privacy-preserving vector memory for DSG HyperCommunication.

This module implements the Proof-Carrying Oblivious Semantic Mesh (PCOSM), an
architectural layer that combines established cryptographic primitives with an
invented communication pattern:

* AES-256-GCM sealed payloads and metadata.
* HKDF-SHA256 domain-separated keys.
* HMAC-keyed blind routing sketches for vector-database candidate search.
* Capability tokens with namespace/operation/expiry caveats.
* Hash commitments + HMAC integrity attestations attached to every record.
* Optional CKKS encrypted vector arithmetic through TenSEAL.

PCOSM is an architecture, not a new cryptographic primitive. Its "proof-carrying"
records are commitment/integrity attestations, not zero-knowledge proofs or SNARKs.
When TenSEAL is unavailable the system reports HE as disabled; it never pretends
that AES or blind sketches are homomorphic encryption.
"""

import base64
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Protocol

import numpy as np
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

try:
    import tenseal as ts
except Exception:  # optional HE backend
    ts = None

try:
    import weaviate
    from weaviate.classes.config import Configure, DataType, Property
    from weaviate.classes.query import MetadataQuery
except Exception:  # optional vector DB backend
    weaviate = Configure = DataType = Property = MetadataQuery = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _stable(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * ((4 - len(text) % 4) % 4))


def _digest(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na <= 1e-12 or nb <= 1e-12:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


@dataclass(slots=True)
class CryptoStatus:
    persistent_master_key: bool
    vector_backend: str
    ckks_enabled: bool
    ckks_library_available: bool
    blind_dimensions: int
    encrypted_payloads: bool = True
    capability_enforcement: bool = True
    proof_mode: str = "commitment+hmac-attestation"
    warnings: list[str] = field(default_factory=list)


class KeySchedule:
    def __init__(self, master: bytes):
        if len(master) < 32:
            raise ValueError("master key must be at least 32 bytes")
        self.master = master[:64]

    def derive(self, label: str, length: int = 32) -> bytes:
        return HKDF(
            algorithm=SHA256(),
            length=length,
            salt=b"DSG-PCOSM-v1",
            info=("dsg/" + label).encode(),
        ).derive(self.master)


class Sealer:
    def __init__(self, key: bytes):
        self.aes = AESGCM(key)

    def seal(self, value: Any, aad: str) -> str:
        nonce = secrets.token_bytes(12)
        plaintext = _stable(value).encode()
        ciphertext = self.aes.encrypt(nonce, plaintext, aad.encode())
        return _b64e(nonce + ciphertext)

    def open(self, token: str, aad: str) -> Any:
        raw = _b64d(token)
        if len(raw) < 13:
            raise ValueError("sealed token too short")
        plaintext = self.aes.decrypt(raw[:12], raw[12:], aad.encode())
        return json.loads(plaintext.decode())


class BlindRouter:
    TOKEN_RE = re.compile(r"[\w@.+:/-]{2,}", re.UNICODE)

    def __init__(self, key: bytes, dimensions: int = 256):
        self.key = key
        self.dimensions = max(64, min(4096, int(dimensions)))

    def _features(self, text: str) -> list[str]:
        tokens = [x.lower() for x in self.TOKEN_RE.findall(text)][:4096]
        features = list(tokens)
        features.extend(f"{a}::{b}" for a, b in zip(tokens, tokens[1:]))
        return features

    def vector(self, text: str) -> list[float]:
        vec = np.zeros(self.dimensions, dtype=np.float64)
        for feature in self._features(text):
            mac = hmac.new(self.key, feature.encode(), hashlib.sha256).digest()
            bucket = int.from_bytes(mac[:8], "big") % self.dimensions
            sign = 1.0 if (mac[8] & 1) else -1.0
            weight = 1.0 + (mac[9] / 255.0) * 0.125
            vec[bucket] += sign * weight
        norm = float(np.linalg.norm(vec)) or 1.0
        return (vec / norm).astype(np.float32).tolist()

    def digest(self, vector: Iterable[float]) -> str:
        arr = np.asarray(list(vector), dtype=np.float32)
        return _digest(arr.tobytes())


class CapabilityAuthority:
    def __init__(self, key: bytes):
        self.key = key

    def issue(
        self,
        subject: str,
        namespace: str,
        operations: Iterable[str],
        *,
        ttl_seconds: int = 3600,
        max_results: int = 16,
    ) -> str:
        body = {
            "v": 1,
            "sub": subject,
            "ns": namespace,
            "ops": sorted(set(str(x) for x in operations)),
            "exp": int(time.time()) + max(1, int(ttl_seconds)),
            "max_results": max(1, min(1000, int(max_results))),
            "jti": secrets.token_hex(12),
        }
        encoded = _b64e(_stable(body).encode())
        sig = _b64e(hmac.new(self.key, encoded.encode(), hashlib.sha256).digest())
        return encoded + "." + sig

    def verify(self, token: str, *, namespace: str, operation: str) -> dict[str, Any]:
        try:
            encoded, sig = token.split(".", 1)
        except ValueError as exc:
            raise PermissionError("malformed capability") from exc
        expected = hmac.new(self.key, encoded.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64d(sig)):
            raise PermissionError("invalid capability signature")
        body = json.loads(_b64d(encoded))
        if int(body.get("exp", 0)) < int(time.time()):
            raise PermissionError("capability expired")
        allowed_ns = str(body.get("ns", ""))
        if allowed_ns != "*" and allowed_ns != namespace:
            raise PermissionError("namespace not allowed")
        if operation not in set(body.get("ops", [])):
            raise PermissionError("operation not allowed")
        return body


class ProofCarrier:
    def __init__(self, key: bytes):
        self.key = key

    def make(self, *, record_id: str, namespace: str, sealed_payload: str, routing_digest: str, policy_digest: str, previous_commitment: str) -> tuple[str, str]:
        commitment = _digest(_stable({
            "record_id": record_id,
            "namespace": namespace,
            "sealed_payload_sha256": _digest(sealed_payload),
            "routing_digest": routing_digest,
            "policy_digest": policy_digest,
            "previous_commitment": previous_commitment,
        }))
        attestation = _b64e(hmac.new(self.key, commitment.encode(), hashlib.sha256).digest())
        return commitment, attestation

    def verify(self, commitment: str, attestation: str) -> bool:
        expected = hmac.new(self.key, commitment.encode(), hashlib.sha256).digest()
        return hmac.compare_digest(expected, _b64d(attestation))


class CKKSVectorEngine:
    """Optional CKKS engine. Requires TenSEAL; never silently falls back."""

    def __init__(self, enabled: bool = False):
        self.enabled = bool(enabled and ts is not None)
        self.context = None
        self.public_context = None
        if self.enabled:
            self.context = ts.context(
                ts.SCHEME_TYPE.CKKS,
                poly_modulus_degree=8192,
                coeff_mod_bit_sizes=[60, 40, 40, 60],
            )
            self.context.global_scale = 2**40
            self.context.generate_galois_keys()
            self.context.generate_relin_keys()
            public = self.context.copy()
            public.make_context_public()
            self.public_context = public

    @property
    def available(self) -> bool:
        return ts is not None

    def encrypt_vector(self, vector: Iterable[float]) -> str | None:
        if not self.enabled or self.public_context is None:
            return None
        enc = ts.ckks_vector(self.public_context, [float(x) for x in vector])
        return _b64e(enc.serialize())

    def encrypted_dot(self, left_ciphertext: str, right_ciphertext: str) -> str:
        if not self.enabled or self.public_context is None:
            raise RuntimeError("CKKS is disabled")
        left = ts.ckks_vector_from(self.public_context, _b64d(left_ciphertext))
        right = ts.ckks_vector_from(self.public_context, _b64d(right_ciphertext))
        score = left.dot(right)
        return _b64e(score.serialize())

    def decrypt_scalar(self, ciphertext: str) -> float:
        if not self.enabled or self.context is None:
            raise RuntimeError("CKKS secret context unavailable")
        value = ts.ckks_vector_from(self.context, _b64d(ciphertext)).decrypt()
        return float(value[0])


@dataclass(slots=True)
class OpaqueVectorRecord:
    record_id: str
    namespace: str
    sealed_payload: str
    routing_digest: str
    policy_digest: str
    commitment: str
    attestation: str
    previous_commitment: str
    created_at: str
    provenance: str
    owner_pseudonym: str
    he_ciphertext: str | None = None


@dataclass(slots=True)
class Candidate:
    record: OpaqueVectorRecord
    routing_score: float


class VectorBackend(Protocol):
    name: str
    def add(self, record: OpaqueVectorRecord, routing_vector: list[float]) -> None: ...
    def search(self, namespace: str, routing_vector: list[float], limit: int) -> list[Candidate]: ...


class LocalVectorBackend:
    name = "local-memory"

    def __init__(self):
        self.records: dict[str, OpaqueVectorRecord] = {}
        self.vectors: dict[str, np.ndarray] = {}

    def add(self, record: OpaqueVectorRecord, routing_vector: list[float]) -> None:
        self.records[record.record_id] = record
        self.vectors[record.record_id] = np.asarray(routing_vector, dtype=np.float32)

    def search(self, namespace: str, routing_vector: list[float], limit: int) -> list[Candidate]:
        query = np.asarray(routing_vector, dtype=np.float32)
        ranked: list[Candidate] = []
        for record_id, record in self.records.items():
            if record.namespace != namespace:
                continue
            ranked.append(Candidate(record, _cosine(query, self.vectors[record_id])))
        ranked.sort(key=lambda c: c.routing_score, reverse=True)
        return ranked[:limit]


class WeaviateVectorBackend:
    name = "weaviate-opaque"

    def __init__(self, url: str, collection_name: str = "DSGPCOSMOpaqueMemory"):
        if weaviate is None:
            raise RuntimeError("weaviate-client is not installed")
        host = url.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
        secure = url.startswith("https://")
        self.client = weaviate.connect_to_custom(
            http_host=host,
            http_port=443 if secure else 80,
            http_secure=secure,
            grpc_host=host,
            grpc_port=50051,
            grpc_secure=secure,
        )
        self.collection_name = collection_name
        if not self.client.collections.exists(collection_name):
            self.client.collections.create(
                name=collection_name,
                vectorizer_config=Configure.Vectorizer.none(),
                properties=[
                    Property(name="record_id", data_type=DataType.TEXT),
                    Property(name="namespace", data_type=DataType.TEXT),
                    Property(name="sealed_payload", data_type=DataType.TEXT),
                    Property(name="routing_digest", data_type=DataType.TEXT),
                    Property(name="policy_digest", data_type=DataType.TEXT),
                    Property(name="commitment", data_type=DataType.TEXT),
                    Property(name="attestation", data_type=DataType.TEXT),
                    Property(name="previous_commitment", data_type=DataType.TEXT),
                    Property(name="created_at", data_type=DataType.TEXT),
                    Property(name="provenance", data_type=DataType.TEXT),
                    Property(name="owner_pseudonym", data_type=DataType.TEXT),
                    Property(name="he_ciphertext", data_type=DataType.TEXT),
                ],
            )
        self.collection = self.client.collections.get(collection_name)

    def add(self, record: OpaqueVectorRecord, routing_vector: list[float]) -> None:
        props = asdict(record)
        props["he_ciphertext"] = record.he_ciphertext or ""
        self.collection.data.insert(properties=props, vector=routing_vector)

    def search(self, namespace: str, routing_vector: list[float], limit: int) -> list[Candidate]:
        response = self.collection.query.near_vector(
            near_vector=routing_vector,
            limit=max(limit * 4, limit),
            return_metadata=MetadataQuery(distance=True) if MetadataQuery else None,
        )
        results: list[Candidate] = []
        for obj in response.objects:
            props = dict(obj.properties)
            if props.get("namespace") != namespace:
                continue
            he = props.get("he_ciphertext") or None
            record = OpaqueVectorRecord(**{**props, "he_ciphertext": he})
            distance = getattr(obj.metadata, "distance", None)
            score = 1.0 - float(distance) if distance is not None else 0.0
            results.append(Candidate(record, score))
            if len(results) >= limit:
                break
        return results


@dataclass(slots=True)
class SearchHit:
    record_id: str
    text: str
    metadata: dict[str, Any]
    provenance: str
    routing_score: float
    homomorphic_score: float | None
    commitment: str
    proof_valid: bool


class SecureSemanticFabric:
    """PCOSM facade used by the agent runtime."""

    def __init__(
        self,
        master_key: bytes,
        *,
        backend: VectorBackend | None = None,
        blind_dimensions: int = 256,
        enable_ckks: bool = False,
        persistent_master_key: bool = True,
    ):
        self.keys = KeySchedule(master_key)
        self.sealer = Sealer(self.keys.derive("payload/aesgcm"))
        self.router = BlindRouter(self.keys.derive("routing/hmac"), dimensions=blind_dimensions)
        self.capabilities = CapabilityAuthority(self.keys.derive("capability/hmac"))
        self.proofs = ProofCarrier(self.keys.derive("proof/hmac"))
        self.owner_key = self.keys.derive("owner/pseudonym")
        self.he = CKKSVectorEngine(enabled=enable_ckks)
        self.backend = backend or LocalVectorBackend()
        self.persistent_master_key = persistent_master_key
        self.last_commitment: dict[str, str] = {}
        self.warnings: list[str] = []
        if not persistent_master_key:
            self.warnings.append("ephemeral master key: stored records cannot be decrypted after restart")
        if enable_ckks and not self.he.available:
            self.warnings.append("DSG_ENABLE_CKKS requested but TenSEAL is unavailable; HE is disabled")

    @classmethod
    def from_env(cls) -> "SecureSemanticFabric":
        raw = os.getenv("DSG_MEMORY_MASTER_KEY", "").strip()
        persistent = bool(raw)
        if raw:
            key: bytes
            try:
                key = _b64d(raw)
            except Exception:
                try:
                    key = bytes.fromhex(raw)
                except Exception:
                    key = hashlib.sha256(raw.encode()).digest()
            if len(key) < 32:
                key = hashlib.sha256(key).digest()
        else:
            key = secrets.token_bytes(32)

        backend: VectorBackend
        url = os.getenv("WEAVIATE_URL", "").strip()
        if url:
            try:
                backend = WeaviateVectorBackend(url, os.getenv("DSG_WEAVIATE_COLLECTION", "DSGPCOSMOpaqueMemory"))
            except Exception:
                backend = LocalVectorBackend()
        else:
            backend = LocalVectorBackend()

        return cls(
            key,
            backend=backend,
            blind_dimensions=int(os.getenv("DSG_BLIND_VECTOR_DIMS", "256")),
            enable_ckks=os.getenv("DSG_ENABLE_CKKS", "0").lower() in {"1", "true", "yes", "on"},
            persistent_master_key=persistent,
        )

    def status(self) -> CryptoStatus:
        return CryptoStatus(
            persistent_master_key=self.persistent_master_key,
            vector_backend=self.backend.name,
            ckks_enabled=self.he.enabled,
            ckks_library_available=self.he.available,
            blind_dimensions=self.router.dimensions,
            warnings=list(self.warnings),
        )

    def issue_capability(self, subject: str, namespace: str, operations: Iterable[str] = ("read", "write"), ttl_seconds: int = 3600, max_results: int = 16) -> str:
        return self.capabilities.issue(subject, namespace, operations, ttl_seconds=ttl_seconds, max_results=max_results)

    def _authorize(self, token: str, namespace: str, operation: str) -> dict[str, Any]:
        if not token:
            raise PermissionError("capability token required")
        return self.capabilities.verify(token, namespace=namespace, operation=operation)

    def _owner_pseudonym(self, owner: str) -> str:
        return hmac.new(self.owner_key, owner.encode(), hashlib.sha256).hexdigest()[:24]

    def remember(
        self,
        *,
        namespace: str,
        owner: str,
        text: str,
        metadata: dict[str, Any] | None,
        capability: str,
        provenance: str = "AGENT",
        embedding: Iterable[float] | None = None,
        policy: dict[str, Any] | None = None,
    ) -> str:
        self._authorize(capability, namespace, "write")
        record_id = "mem_" + secrets.token_hex(12)
        policy = policy or {"purpose": "agent-memory", "export": False}
        routing = self.router.vector(text)
        routing_digest = self.router.digest(routing)
        policy_digest = _digest(_stable(policy))
        previous = self.last_commitment.get(namespace, "0" * 64)
        aad = f"{record_id}|{namespace}|{provenance}|{policy_digest}"
        sealed = self.sealer.seal({"text": text, "metadata": metadata or {}, "policy": policy}, aad)
        he_ciphertext = self.he.encrypt_vector(embedding) if embedding is not None else None
        commitment, attestation = self.proofs.make(
            record_id=record_id,
            namespace=namespace,
            sealed_payload=sealed,
            routing_digest=routing_digest,
            policy_digest=policy_digest,
            previous_commitment=previous,
        )
        record = OpaqueVectorRecord(
            record_id=record_id,
            namespace=namespace,
            sealed_payload=sealed,
            routing_digest=routing_digest,
            policy_digest=policy_digest,
            commitment=commitment,
            attestation=attestation,
            previous_commitment=previous,
            created_at=_now(),
            provenance=provenance,
            owner_pseudonym=self._owner_pseudonym(owner),
            he_ciphertext=he_ciphertext,
        )
        self.backend.add(record, routing)
        self.last_commitment[namespace] = commitment
        return record_id

    def search(
        self,
        *,
        namespace: str,
        query: str,
        capability: str,
        limit: int = 6,
        query_embedding: Iterable[float] | None = None,
    ) -> list[SearchHit]:
        cap = self._authorize(capability, namespace, "read")
        limit = max(1, min(int(limit), int(cap.get("max_results", 16))))
        routing = self.router.vector(query)
        candidates = self.backend.search(namespace, routing, max(limit * 3, limit))
        query_he = self.he.encrypt_vector(query_embedding) if query_embedding is not None else None
        hits: list[SearchHit] = []
        for candidate in candidates:
            record = candidate.record
            proof_valid = self.proofs.verify(record.commitment, record.attestation)
            if not proof_valid:
                continue
            aad = f"{record.record_id}|{record.namespace}|{record.provenance}|{record.policy_digest}"
            payload = self.sealer.open(record.sealed_payload, aad)
            he_score: float | None = None
            if query_he and record.he_ciphertext and self.he.enabled:
                encrypted_score = self.he.encrypted_dot(query_he, record.he_ciphertext)
                he_score = self.he.decrypt_scalar(encrypted_score)
            hits.append(SearchHit(
                record_id=record.record_id,
                text=str(payload.get("text", "")),
                metadata=dict(payload.get("metadata", {})),
                provenance=record.provenance,
                routing_score=round(candidate.routing_score, 8),
                homomorphic_score=round(he_score, 8) if he_score is not None else None,
                commitment=record.commitment,
                proof_valid=True,
            ))
        hits.sort(key=lambda h: h.homomorphic_score if h.homomorphic_score is not None else h.routing_score, reverse=True)
        return hits[:limit]
