from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from dsghyper.cells import QuorumCell, SpecialistExecutor
from dsghyper.config import RuntimeConfig
from dsghyper.model import ModelClient
from dsghyper.research import SpecialistPlan


class CellTests(unittest.TestCase):
    def config(self, root: Path) -> RuntimeConfig:
        return RuntimeConfig(
            base_url="https://api.openai.com/v1",
            api_key="",
            model="primary",
            rounds=1,
            model_timeout=5,
            round_timeout=5,
            model_concurrency=4,
            max_output_tokens=512,
            max_prompt_chars=8000,
            max_context_chars=16000,
            trace_root=root,
            require_ledger=False,
        )

    def test_quorum_cell_is_bounded_and_not_truth_probability(self):
        with tempfile.TemporaryDirectory() as tmp:
            async def scenario():
                client = ModelClient(self.config(Path(tmp)))
                try:
                    cell = QuorumCell(client, ["m1", "m2", "m1"], max_models=2, timeout=2, max_tokens_per_model=256)
                    return await cell.evaluate({"task": "test"})
                finally:
                    await client.close()

            result = asyncio.run(scenario())
            public = result.public_dict()
            self.assertTrue(result.active)
            self.assertEqual(result.configured_models, ("m1", "m2"))
            self.assertEqual(len(result.model_results), 2)
            self.assertIsNone(public["truth_probability"])

    def test_specialist_executor_requires_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = SpecialistPlan("s1", "r1:red:c1", "verifier", "check conflict", 400, 0.8)

            async def scenario(enabled: bool):
                client = ModelClient(self.config(Path(tmp)))
                try:
                    executor = SpecialistExecutor(
                        client,
                        enabled=enabled,
                        max_specialists=1,
                        total_token_quota=300,
                        timeout=2,
                    )
                    return await executor.execute([plan], task="test", epistemic_context={})
                finally:
                    await client.close()

            disabled = asyncio.run(scenario(False))
            enabled = asyncio.run(scenario(True))
            self.assertFalse(disabled.enabled)
            self.assertEqual(len(disabled.executions), 0)
            self.assertTrue(enabled.enabled)
            self.assertEqual(len(enabled.executions), 1)
            self.assertLessEqual(enabled.tokens_reserved, 300)
            self.assertEqual(enabled.executions[0].result.status, "fallback")


if __name__ == "__main__":
    unittest.main()
