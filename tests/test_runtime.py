from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from dsghyper.config import MemoryConfig, RuntimeConfig
from dsghyper.runtime import HyperOrchestrator, SecureHyperOrchestrator


class RuntimeTests(unittest.TestCase):
    def runtime_config(self, root: Path) -> RuntimeConfig:
        return RuntimeConfig(
            base_url="https://api.openai.com/v1",
            api_key="",
            model="test-model",
            rounds=2,
            model_timeout=5,
            round_timeout=5,
            model_concurrency=4,
            max_output_tokens=512,
            max_prompt_chars=8000,
            max_context_chars=16000,
            trace_root=root,
            require_ledger=True,
        )

    def test_fallback_runtime_has_fixed_call_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self.runtime_config(Path(tmp))

            async def scenario():
                async with HyperOrchestrator(rounds=2, config=config) as runtime:
                    return await runtime.ask("design and verify a resilient system")

            result = asyncio.run(scenario())
            self.assertEqual(result["communication"]["worker_results"], 8)
            self.assertEqual(result["communication"]["recursive_peer_calls"], 0)
            self.assertTrue(result["ledger"]["verified"])
            self.assertEqual(result["final"]["status"], "fallback")

    def test_secure_ephemeral_mode_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_cfg = self.runtime_config(Path(tmp) / "traces")
            memory_cfg = MemoryConfig(
                namespace="test",
                master_key_raw="",
                allow_ephemeral=True,
                sqlite_path=Path(tmp) / "unused.sqlite3",
                weaviate_url="",
                weaviate_collection="Test",
                blind_dimensions=128,
                result_limit=4,
                capability_ttl=60,
                store_request=True,
                enable_ckks=False,
                ckks_public_context="",
                ckks_secret_context="",
            )

            async def scenario():
                async with SecureHyperOrchestrator(rounds=1, runtime_config=runtime_cfg, memory_config=memory_cfg) as runtime:
                    return await runtime.ask("remember this architecture")

            result = asyncio.run(scenario())
            status = result["secure_memory"]["status"]
            self.assertFalse(status["master_key_persistent"])
            self.assertFalse(status["backend_persistent"])
            self.assertTrue(result["secure_memory"]["capabilities_revoked_after_run"])


if __name__ == "__main__":
    unittest.main()
