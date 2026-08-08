from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Protocol

import numpy as np
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .config import MemoryConfig, parse_secret
from .protocol import safe_text, stable_json

try:
    import tenseal as ts
except Exception:
    ts = None

try:
    import weaviate
    from weaviate.classes.config import Configure, DataType, Property
    from weaviate.classes.query import Filter, MetadataQuery
except Exception:
    weaviate = Configure = DataType = Property = Filter = MetadataQuery = None

ARCHITECTURE = "PCESM_PROOF_CARRYING_ENCRYPTED_SEMANTIC_MESH_V2"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * ((4 - len(text) % 4) % 4))


def _digest(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na <= 1e-12 or nb <= 1e-12:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class KeySchedule:
    def __init__(self, master: bytes):
        if len(master) < 32:
            raise ValueError("memory master key must contain at least 32 bytes")
        self.master = master

    def derive(self, label: str, length: int = 32) -> bytes:
        return HKDF(algorithm=SHA256(), length=length, salt=b"DSG-PCESM-v2", info=("dsg/pcesm/" + label).encode()).derive(self.master)


class Sealer:
    def __init__(self, key: bytes):
        self._aes = AESGCM(key)

    def seal(self, value: Any, aad: str) -> str:
        nonce = secrets.token_bytes(12)
        ciphertext = self._aes.encrypt(nonce, stable_json(value).encode(), aad.encode())
        return _b64e(nonce + ciphertext)

    def open(self, token: str, aad: str) -> Any:
        raw = _b64d(token)
        if len(raw) < 29:
            raise ValueError("sealed payload is malformed")
        return json.loads(self._aes.decrypt(raw[:12], raw[12:], aad.encode()).decode())


class BlindRouter:
    """Keyed semantic sketch. It hides literal tokens, not access patterns or similarity leakage."""

    def __init__(self, key: bytes, dimensions: int):
        self.key = key
        self.dimensions = max(64, min(4096, int(dimensions)))

    def vector(self, text: str) -> list[float]:
        normalized = "".join(ch.lower() if ch.isalnum() or ch in "@.+:/-_" else " " for ch in text)
        tokens = [x for x in normalized.split() if len(x) >= 2][:4096]
        features = tokens + [f"{a}::{b}" for a, b in zip(tokens, tokens[1:])]
        vec = np.zeros(self.dimensions, dtype=np.float64)
        for feature in features:
            mac = hmac.new(self.key, feature.encode(), hashlib.sha256).digest()
            bucket = int.from_bytes(mac[:8], "big") % self.dimensions
            vec[bucket] += 1.0 if mac[8] & 1 else -1.0
        norm = float(np.linalg.norm(vec)) or 1.0
        return (vec / norm).astype(np.float32).tolist()

    @staticmethod
    def digest(vector: Iterable[float]) -> str:
        return _digest(np.asarray(list(vector), dtype=np.float32).tobytes())


class CapabilityAuthority:
    def __init__(self, key: bytes):
        self.key = key
        self.revoked: set[str] = set()
        self._lock = threading.Lock()

    def issue(self, *, subject: str, namespace: str, operations: Iterable[str], ttl_seconds: int, max_results: int) -> str:
        now = int(time.time())
        body = {
            "v": 2, "iss": "dsg-hyperruntime", "aud": "dsg-pcesm",
            "sub": safe_text(subject, 128), "ns": safe_text(namespace, 128),
            "ops": sorted(set(safe_text(x, 32) for x in operations)),
            "iat": now, "nbf": now - 2, "exp": now + max(1, int(ttl_seconds)),
            "max_results": max(1, min(128, int(max_results))), "jti": secrets.token_hex(16),
        }
        encoded = _b64e(stable_json(body).encode())
        sig = _b64e(hmac.new(self.key, encoded.encode(), hashlib.sha256).digest())
        return encoded + "." + sig

    def _decode(self, token: str) -> dict[str, Any]:
        try:
            encoded, signature = token.split(".", 1)
            expected = hmac.new(self.key, encoded.encode(), hashlib.sha256).digest()
            if not hmac.compare_digest(expected, _b64d(signature)):
                raise PermissionError("invalid capability signature")
            body = json.loads(_b64d(encoded))
            if not isinstance(body, dict):
                raise PermissionError("invalid capability body")
            return body
        except PermissionError:
            raise
        except Exception as exc:
            raise PermissionError("malformed capability") from exc

    def verify(self, token: str, *, namespace: str, operation: str) -> dict[str, Any]:
        body = self._decode(token)
        now = int(time.time())
        if body.get("aud") != "dsg-pcesm":
            raise PermissionError("capability audience mismatch")
        if int(body.get("nbf", 0)) > now or int(body.get("exp", 0)) <= now:
            raise PermissionError("capability is not currently valid")
        with self._lock:
            if str(body.get("jti", "")) in self.revoked:
                raise PermissionError("capability revoked")
        if str(body.get("ns", "")) not in {"*", namespace}:
            raise PermissionError("namespace not allowed")
        if operation not in set(body.get("ops", [])):
            raise PermissionError("operation not allowed")
        return body

    def revoke(self, token: str) -> None:
        body = self._decode(token)
        with self._lock:
            self.revoked.add(str(body.get("jti", "")))


@dataclass(frozen=True, slots=True)
class OpaqueRecord:
    record_id: str
    version: int
    namespace: str
    kind: str
    sealed_payload: str
    routing_digest: str
    policy_digest: str
    commitment: str
    attestation: str
    created_at: str
    expires_at: int
    provenance: str
    owner_pseudonym: str
    he_ciphertext: str = ""

    def commitment_body(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id, "version": self.version, "namespace": self.namespace,
            "kind": self.kind, "sealed_payload_sha256": _digest(self.sealed_payload),
            "routing_digest": self.routing_digest, "policy_digest": self.policy_digest,
            "created_at": self.created_at, "expires_at": self.expires_at,
            "provenance": self.provenance, "owner_pseudonym": self.owner_pseudonym,
            "he_ciphertext_sha256": _digest(self.he_ciphertext) if self.he_ciphertext else "",
        }


class RecordAttestor:
    def __init__(self, key: bytes): self.key = key

    def build(self, record: OpaqueRecord) -> tuple[str, str]:
        commitment = _digest(stable_json(record.commitment_body()))
        return commitment, _b64e(hmac.new(self.key, commitment.encode(), hashlib.sha256).digest())

    def verify(self, record: OpaqueRecord) -> bool:
        recomputed = _digest(stable_json(record.commitment_body()))
        if not hmac.compare_digest(recomputed, record.commitment):
            return False
        try:
            supplied = _b64d(record.attestation)
        except Exception:
            return False
        expected = hmac.new(self.key, recomputed.encode(), hashlib.sha256).digest()
        return hmac.compare_digest(expected, supplied)


@dataclass(frozen=True, slots=True)
class Candidate:
    record: OpaqueRecord
    routing_score: float


class VectorBackend(Protocol):
    name: str
    persistent: bool
    def put(self, record: OpaqueRecord, routing_vector: list[float]) -> None: ...
    def search(self, namespace: str, routing_vector: list[float], limit: int) -> list[Candidate]: ...
    def close(self) -> None: ...


class LocalVectorBackend:
    name = "local-memory"
    persistent = False

    def __init__(self):
        self.records: dict[str, OpaqueRecord] = {}
        self.vectors: dict[str, np.ndarray] = {}

    def put(self, record: OpaqueRecord, routing_vector: list[float]) -> None:
        self.records[record.record_id] = record
        self.vectors[record.record_id] = np.asarray(routing_vector, dtype=np.float32)

    def search(self, namespace: str, routing_vector: list[float], limit: int) -> list[Candidate]:
        query = np.asarray(routing_vector, dtype=np.float32)
        now = int(time.time())
        values = [Candidate(record, _cosine(query, self.vectors[rid])) for rid, record in self.records.items() if record.namespace == namespace and (not record.expires_at or record.expires_at > now)]
        values.sort(key=lambda x: x.routing_score, reverse=True)
        return values[:limit]

    def close(self) -> None: pass


class SQLiteVectorBackend:
    name = "sqlite-opaque-vector"
    persistent = True

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("CREATE TABLE IF NOT EXISTS pcesm_records (record_id TEXT PRIMARY KEY, version INTEGER, namespace TEXT, kind TEXT, sealed_payload TEXT, routing_digest TEXT, policy_digest TEXT, commitment TEXT, attestation TEXT, created_at TEXT, expires_at INTEGER, provenance TEXT, owner_pseudonym TEXT, he_ciphertext TEXT, routing_vector BLOB)")
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_pcesm_ns ON pcesm_records(namespace)")
        self._db.commit()
        self._lock = threading.Lock()

    def put(self, record: OpaqueRecord, routing_vector: list[float]) -> None:
        blob = np.asarray(routing_vector, dtype=np.float32).tobytes()
        with self._lock:
            self._db.execute("INSERT INTO pcesm_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (*asdict(record).values(), blob))
            self._db.commit()

    def search(self, namespace: str, routing_vector: list[float], limit: int) -> list[Candidate]:
        query = np.asarray(routing_vector, dtype=np.float32)
        now = int(time.time())
        with self._lock:
            rows = self._db.execute("SELECT * FROM pcesm_records WHERE namespace=? AND (expires_at=0 OR expires_at>?)", (namespace, now)).fetchall()
        values = []
        for row in rows:
            record = OpaqueRecord(*row[:14])
            vec = np.frombuffer(row[14], dtype=np.float32)
            if vec.size == query.size:
                values.append(Candidate(record, _cosine(query, vec)))
        values.sort(key=lambda x: x.routing_score, reverse=True)
        return values[:limit]

    def close(self) -> None:
        with self._lock: self._db.close()


class WeaviateVectorBackend:
    name = "weaviate-opaque-vector"
    persistent = True

    def __init__(self, url: str, collection_name: str):
        if weaviate is None or Filter is None:
            raise RuntimeError("weaviate-client is unavailable")
        clean = url.rstrip("/")
        secure = clean.startswith("https://")
        host = clean.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0]
        self.client = weaviate.connect_to_custom(http_host=host, http_port=443 if secure else 80, http_secure=secure, grpc_host=host, grpc_port=50051, grpc_secure=secure)
        if not self.client.collections.exists(collection_name):
            self.client.collections.create(name=collection_name, vectorizer_config=Configure.Vectorizer.none(), properties=[Property(name=name, data_type=DataType.INT if name in {"version", "expires_at"} else DataType.TEXT) for name in OpaqueRecord.__dataclass_fields__])
        self.collection = self.client.collections.get(collection_name)

    def put(self, record: OpaqueRecord, routing_vector: list[float]) -> None:
        self.collection.data.insert(properties=asdict(record), vector=routing_vector)

    def search(self, namespace: str, routing_vector: list[float], limit: int) -> list[Candidate]:
        response = self.collection.query.near_vector(near_vector=routing_vector, filters=Filter.by_property("namespace").equal(namespace), limit=max(limit * 3, limit), return_metadata=MetadataQuery(distance=True))
        now, values = int(time.time()), []
        for obj in response.objects:
            props = dict(obj.properties)
            if int(props.get("expires_at", 0) or 0) and int(props["expires_at"]) <= now:
                continue
            record = OpaqueRecord(**{k: props.get(k, "") for k in OpaqueRecord.__dataclass_fields__})
            distance = getattr(obj.metadata, "distance", None)
            values.append(Candidate(record, 1.0 - float(distance) if distance is not None else 0.0))
            if len(values) >= limit: break
        return values

    def close(self) -> None:
        try: self.client.close()
        except Exception: pass


class CKKSVectorEngine:
    def __init__(self, enabled: bool, public_context_b64: str = "", secret_context_b64: str = ""):
        self.requested = bool(enabled)
        self.available = ts is not None
        self.enabled = bool(enabled and self.available)
        self.public_context = self.secret_context = None
        self.persistent_context = False
        if not self.enabled: return
        if public_context_b64 and secret_context_b64:
            self.public_context = ts.context_from(_b64d(public_context_b64)); self.secret_context = ts.context_from(_b64d(secret_context_b64)); self.persistent_context = True
        else:
            secret = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192, coeff_mod_bit_sizes=[60,40,40,60])
            secret.global_scale = 2**40; secret.generate_galois_keys(); secret.generate_relin_keys()
            public = secret.copy(); public.make_context_public()
            self.secret_context, self.public_context = secret, public

    def encrypt(self, vector: Iterable[float]) -> str:
        if not self.enabled: raise RuntimeError("CKKS is not enabled")
        return _b64e(ts.ckks_vector(self.public_context, [float(x) for x in vector]).serialize())

    def encrypted_dot(self, left: str, right: str) -> str:
        lhs = ts.ckks_vector_from(self.public_context, _b64d(left)); rhs = ts.ckks_vector_from(self.public_context, _b64d(right))
        return _b64e(lhs.dot(rhs).serialize())

    def decrypt_scalar(self, ciphertext: str) -> float:
        return float(ts.ckks_vector_from(self.secret_context, _b64d(ciphertext)).decrypt()[0])


@dataclass(frozen=True, slots=True)
class SearchHit:
    record_id: str
    text: str
    metadata: dict[str, Any]
    provenance: str
    routing_score: float
    homomorphic_score: float | None
    commitment: str
    proof_valid: bool


@dataclass(frozen=True, slots=True)
class MemoryStatus:
    architecture: str
    vector_backend: str
    backend_persistent: bool
    master_key_persistent: bool
    encrypted_payloads: bool
    capability_enforcement: bool
    record_attestation: str
    blind_dimensions: int
    ckks_requested: bool
    ckks_available: bool
    ckks_enabled: bool
    ckks_persistent_context: bool
    access_pattern_hiding: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)


class SecureSemanticFabric:
    def __init__(self, master_key: bytes, *, backend: VectorBackend, blind_dimensions: int = 512, master_key_persistent: bool = True, enable_ckks: bool = False, ckks_public_context: str = "", ckks_secret_context: str = "", warnings: Iterable[str] = ()):
        keys = KeySchedule(master_key)
        self.sealer = Sealer(keys.derive("payload/aes-256-gcm"))
        self.router = BlindRouter(keys.derive("routing/hmac-sha256"), blind_dimensions)
        self.capabilities = CapabilityAuthority(keys.derive("capability/hmac-sha256"))
        self.attestor = RecordAttestor(keys.derive("record-attestation/hmac-sha256"))
        self.owner_key = keys.derive("owner-pseudonym/hmac-sha256")
        self.backend = backend; self.master_key_persistent = master_key_persistent
        self.he = CKKSVectorEngine(enable_ckks, ckks_public_context, ckks_secret_context)
        self.warnings = list(warnings)
        if self.he.requested and not self.he.available: self.warnings.append("CKKS requested but TenSEAL is unavailable")
        if self.he.enabled and not self.he.persistent_context and backend.persistent: self.warnings.append("ephemeral CKKS context: HE ciphertext will not be persisted")

    @classmethod
    def from_config(cls, config: MemoryConfig | None = None) -> "SecureSemanticFabric":
        config = config or MemoryConfig.from_env(); warnings = []
        if not config.master_key_raw:
            if not config.allow_ephemeral:
                raise RuntimeError("DSG_MEMORY_MASTER_KEY is required for persistent secure memory; set DSG_ALLOW_EPHEMERAL_MEMORY=1 only for temporary local mode")
            master, backend, persistent = secrets.token_bytes(32), LocalVectorBackend(), False
            warnings.append("ephemeral mode: memory disappears at shutdown")
        else:
            master, persistent = parse_secret(config.master_key_raw, name="DSG_MEMORY_MASTER_KEY"), True
            if config.weaviate_url:
                try: backend = WeaviateVectorBackend(config.weaviate_url, config.weaviate_collection)
                except Exception as exc:
                    warnings.append(f"Weaviate unavailable ({type(exc).__name__}); using SQLite")
                    backend = SQLiteVectorBackend(config.sqlite_path)
            else: backend = SQLiteVectorBackend(config.sqlite_path)
        return cls(master, backend=backend, blind_dimensions=config.blind_dimensions, master_key_persistent=persistent, enable_ckks=config.enable_ckks, ckks_public_context=config.ckks_public_context, ckks_secret_context=config.ckks_secret_context, warnings=warnings)

    def close(self) -> None: self.backend.close()

    def status(self) -> MemoryStatus:
        return MemoryStatus(ARCHITECTURE, self.backend.name, self.backend.persistent, self.master_key_persistent, True, True, "sha256-commitment+hmac-sha256", self.router.dimensions, self.he.requested, self.he.available, self.he.enabled, self.he.persistent_context, False, tuple(self.warnings))

    def issue_capability(self, subject: str, namespace: str, operations: Iterable[str], *, ttl_seconds: int = 900, max_results: int = 8) -> str:
        return self.capabilities.issue(subject=subject, namespace=namespace, operations=operations, ttl_seconds=ttl_seconds, max_results=max_results)

    def _pseudonym(self, owner: str) -> str:
        return hmac.new(self.owner_key, owner.encode(), hashlib.sha256).hexdigest()[:24]

    @staticmethod
    def _aad(record_id: str, namespace: str, kind: str, policy_digest: str) -> str:
        return f"PCESM2|{record_id}|{namespace}|{kind}|{policy_digest}"

    def remember(self, *, namespace: str, owner: str, text: str, metadata: dict[str, Any] | None, capability: str, provenance: str = "AGENT", kind: str = "semantic-memory", policy: dict[str, Any] | None = None, expires_at: int = 0, embedding: Iterable[float] | None = None) -> str:
        self.capabilities.verify(capability, namespace=namespace, operation="write")
        record_id = "mem_" + secrets.token_hex(16); policy = policy or {"purpose":"agent-memory","export":False}
        policy_digest = _digest(stable_json(policy)); routing = self.router.vector(text); routing_digest = self.router.digest(routing)
        sealed = self.sealer.seal({"text":safe_text(text,50000),"metadata":metadata or {},"policy":policy}, self._aad(record_id, namespace, kind, policy_digest))
        he_ciphertext = ""
        if embedding is not None and self.he.enabled and (self.he.persistent_context or not self.backend.persistent): he_ciphertext = self.he.encrypt(embedding)
        draft = OpaqueRecord(record_id,2,safe_text(namespace,128),safe_text(kind,64),sealed,routing_digest,policy_digest,"","",_now(),max(0,int(expires_at)),safe_text(provenance,96),self._pseudonym(owner),he_ciphertext)
        commitment, attestation = self.attestor.build(draft)
        record = OpaqueRecord(**{**asdict(draft),"commitment":commitment,"attestation":attestation})
        self.backend.put(record, routing); return record_id

    def search(self, *, namespace: str, query: str, capability: str, limit: int = 6, query_embedding: Iterable[float] | None = None) -> list[SearchHit]:
        auth = self.capabilities.verify(capability, namespace=namespace, operation="read")
        limit = max(1,min(int(limit),int(auth.get("max_results",8)))); routing = self.router.vector(query)
        candidates = self.backend.search(namespace, routing, max(limit*3,limit)); query_he = self.he.encrypt(query_embedding) if query_embedding is not None and self.he.enabled else ""
        hits = []
        for candidate in candidates:
            record = candidate.record
            if not self.attestor.verify(record): continue
            try: payload = self.sealer.open(record.sealed_payload, self._aad(record.record_id,record.namespace,record.kind,record.policy_digest))
            except Exception: continue
            he_score = None
            if query_he and record.he_ciphertext and self.he.enabled: he_score = self.he.decrypt_scalar(self.he.encrypted_dot(query_he, record.he_ciphertext))
            hits.append(SearchHit(record.record_id,safe_text(payload.get("text",""),50000),dict(payload.get("metadata",{})) if isinstance(payload.get("metadata",{}),dict) else {},record.provenance,round(candidate.routing_score,8),round(he_score,8) if he_score is not None else None,record.commitment,True))
        hits.sort(key=lambda h: h.homomorphic_score if h.homomorphic_score is not None else h.routing_score, reverse=True)
        return hits[:limit]
