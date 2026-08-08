from __future__ import annotations

import unittest

from dsghyper.protocol import AgentResult, Spectrum


class ProtocolTests(unittest.TestCase):
    def test_structured_challenges_and_notes_are_bounded(self):
        result = AgentResult.from_model("blue", {
            "answer": "audit",
            "claims": [{"claim_id": "c1", "text": "claim", "confidence": 9, "evidence": ["x"]}],
            "challenges": [{"target_agent": "red", "claim_id": "r1", "reason": "unsupported", "severity": .8, "confidence": .9}],
            "peer_notes": [{"recipient": "green", "topic": "fix", "content": "repair", "priority": 200}],
            "confidence": -2,
        })
        self.assertEqual(result.claims[0].confidence, 1.0)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.challenges[0].target_agent, "red")
        self.assertEqual(result.peer_notes[0].priority, 100)

    def test_spectrum_normalizes(self):
        spectrum = Spectrum.infer("urgent verify design final")
        total = sum((spectrum.red, spectrum.green, spectrum.blue, spectrum.gamma, spectrum.sync))
        self.assertAlmostEqual(total, 1.0)
        self.assertGreaterEqual(spectrum.entropy(), 0.0)
        self.assertLessEqual(spectrum.entropy(), 1.0)


if __name__ == "__main__":
    unittest.main()
