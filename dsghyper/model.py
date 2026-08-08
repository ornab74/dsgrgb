from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Any

import httpx

from .config import RuntimeConfig
from .protocol import AgentResult, parse_json_object, stable_json


@dataclass(slots=True)
class ModelMetrics:
    calls: int = 0
    failures: int = 0
    retries: int = 0


class ModelClient:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.metrics = ModelMetrics()
        self._sem = asyncio.Semaphore(config.model_concurrency)
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(config.model_timeout))

    async def close(self) -> None:
        await self._client.aclose()

    async def invoke(
        self,
        agent: str,
        system: str,
        packet: dict[str, Any],
        *,
        model_override: str | None = None,
        max_tokens_override: int | None = None,
    ) -> AgentResult:
        if not self.config.api_key:
            return AgentResult.from_model(agent, {
                "answer": "LOCAL_FALLBACK: OPENAI_API_KEY is not configured.",
                "claims": [],
                "challenges": [],
                "relations": [],
                "information_requests": [],
                "uncertainties": ["No remote model inference was performed."],
                "next_checks": [],
                "peer_notes": [],
                "confidence": 0.2,
                "status": "fallback",
            })

        model = (model_override or self.config.model).strip()
        max_tokens = self.config.max_output_tokens
        if max_tokens_override is not None:
            max_tokens = max(128, min(self.config.max_output_tokens, int(max_tokens_override)))
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": stable_json(packet)},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        last_error = "unknown model error"
        async with self._sem:
            for attempt in range(3):
                self.metrics.calls += 1
                try:
                    response = await self._client.post(
                        f"{self.config.base_url}/chat/completions",
                        headers=headers,
                        json=body,
                    )
                    response.raise_for_status()
                    data = response.json()
                    text = str(data["choices"][0]["message"]["content"])
                    return AgentResult.from_model(agent, parse_json_object(text))
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self.metrics.failures += 1
                    last_error = f"{type(exc).__name__}: {exc}"
                    if attempt < 2:
                        self.metrics.retries += 1
                        await asyncio.sleep(0.4 * (2 ** attempt) + random.random() * 0.15)
        return AgentResult.failure(agent, last_error)
