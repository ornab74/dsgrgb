from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _bounded_int(name: str, default: int, lo: int, hi: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(lo, min(hi, value))


def _bounded_float(name: str, default: float, lo: float, hi: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(lo, min(hi, value))


def parse_secret(raw: str, *, name: str, minimum: int = 32) -> bytes:
    """Parse explicit hex:/b64: secrets; otherwise derive a fixed-length key.

    A plain string is accepted for compatibility, but is fed through scrypt rather than
    used directly as cryptographic key material. Deployments should prefer generated
    b64:/hex: values with at least 32 random bytes.
    """
    raw = raw.strip()
    if not raw:
        raise ValueError(f"{name} is empty")
    if raw.startswith("hex:"):
        value = bytes.fromhex(raw[4:])
    elif raw.startswith("b64:"):
        text = raw[4:]
        value = base64.urlsafe_b64decode(text + "=" * ((4 - len(text) % 4) % 4))
    else:
        value = hashlib.scrypt(
            raw.encode("utf-8"),
            salt=("DSG/" + name + "/v2").encode("utf-8"),
            n=2**14,
            r=8,
            p=1,
            dklen=32,
        )
    if len(value) < minimum:
        raise ValueError(f"{name} must decode to at least {minimum} bytes")
    return value


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    base_url: str
    api_key: str
    model: str
    rounds: int
    model_timeout: float
    round_timeout: float
    model_concurrency: int
    max_output_tokens: int
    max_prompt_chars: int
    max_context_chars: int
    trace_root: Path
    require_ledger: bool

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        return cls(
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            model=os.getenv("OPENAI_MODEL", "gpt-5.6").strip(),
            rounds=_bounded_int("DSG_HYPER_ROUNDS", 2, 1, 8),
            model_timeout=_bounded_float("DSG_MODEL_TIMEOUT", 90.0, 5.0, 600.0),
            round_timeout=_bounded_float("DSG_ROUND_TIMEOUT", 120.0, 10.0, 900.0),
            model_concurrency=_bounded_int("DSG_MODEL_CONCURRENCY", 6, 1, 32),
            max_output_tokens=_bounded_int("DSG_MAX_OUTPUT_TOKENS", 2200, 256, 12000),
            max_prompt_chars=_bounded_int("DSG_MAX_PROMPT_CHARS", 32000, 1024, 200000),
            max_context_chars=_bounded_int("DSG_MAX_CONTEXT_CHARS", 48000, 4096, 300000),
            trace_root=Path(os.getenv("DSG_TRACE_ROOT", "outputs/traces")),
            require_ledger=_flag("DSG_REQUIRE_LEDGER", False),
        )


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    namespace: str
    master_key_raw: str
    allow_ephemeral: bool
    sqlite_path: Path
    weaviate_url: str
    weaviate_collection: str
    blind_dimensions: int
    result_limit: int
    capability_ttl: int
    store_request: bool
    enable_ckks: bool
    ckks_public_context: str
    ckks_secret_context: str

    @classmethod
    def from_env(cls) -> "MemoryConfig":
        return cls(
            namespace=os.getenv("DSG_MEMORY_NAMESPACE", "hypercomm").strip() or "hypercomm",
            master_key_raw=os.getenv("DSG_MEMORY_MASTER_KEY", "").strip(),
            allow_ephemeral=_flag("DSG_ALLOW_EPHEMERAL_MEMORY", False),
            sqlite_path=Path(os.getenv("DSG_MEMORY_SQLITE", "outputs/secure_memory.sqlite3")),
            weaviate_url=os.getenv("WEAVIATE_URL", "").strip(),
            weaviate_collection=os.getenv("DSG_WEAVIATE_COLLECTION", "DSGPCESMMemory").strip(),
            blind_dimensions=_bounded_int("DSG_BLIND_VECTOR_DIMS", 512, 64, 4096),
            result_limit=_bounded_int("DSG_MEMORY_RESULT_LIMIT", 6, 1, 64),
            capability_ttl=_bounded_int("DSG_CAPABILITY_TTL", 900, 30, 86400),
            store_request=_flag("DSG_MEMORY_STORE_REQUEST", True),
            enable_ckks=_flag("DSG_ENABLE_CKKS", False),
            ckks_public_context=os.getenv("DSG_CKKS_PUBLIC_CONTEXT_B64", "").strip(),
            ckks_secret_context=os.getenv("DSG_CKKS_SECRET_CONTEXT_B64", "").strip(),
        )
