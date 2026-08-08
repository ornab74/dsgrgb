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


def _csv(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    return tuple(x.strip() for x in raw.split(",") if x.strip())


def _csv_ints(name: str, default: tuple[int, ...]) -> tuple[int, ...]:
    values: list[int] = []
    for item in _csv(name):
        try:
            values.append(int(item))
        except ValueError:
            continue
    return tuple(values) or default


def parse_secret(raw: str, *, name: str, minimum: int = 32) -> bytes:
    """Parse explicit hex:/b64: secrets; otherwise derive a fixed-length key."""
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
class ResearchConfig:
    market_token_budget: int
    freshness_ttl_rounds: int
    freshness_half_life_rounds: float
    specialist_limit: int
    specialist_token_quota: int
    execute_specialists: bool
    quorum_models: tuple[str, ...]
    counterfactual_budgets: tuple[int, ...]
    policy_auth_key_raw: str

    @classmethod
    def from_env(cls) -> "ResearchConfig":
        return cls(
            market_token_budget=_bounded_int("DSG_MARKET_TOKEN_BUDGET", 4500, 256, 50000),
            freshness_ttl_rounds=_bounded_int("DSG_FRESHNESS_TTL_ROUNDS", 4, 1, 64),
            freshness_half_life_rounds=_bounded_float("DSG_FRESHNESS_HALF_LIFE_ROUNDS", 2.0, 0.25, 64.0),
            specialist_limit=_bounded_int("DSG_SPECIALIST_LIMIT", 2, 0, 8),
            specialist_token_quota=_bounded_int("DSG_SPECIALIST_TOKEN_QUOTA", 3000, 0, 50000),
            execute_specialists=_flag("DSG_EXECUTE_SPECIALISTS", False),
            quorum_models=_csv("DSG_QUORUM_MODELS")[:8],
            counterfactual_budgets=tuple(
                max(128, min(50000, x)) for x in _csv_ints("DSG_COUNTERFACTUAL_BUDGETS", (1024, 2048, 4096))
            )[:12],
            policy_auth_key_raw=os.getenv("DSG_POLICY_AUTH_KEY", "").strip(),
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
