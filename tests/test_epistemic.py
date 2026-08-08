from __future__ import annotations

import unittest

from dsghyper.epistemic import CommunicationBudget, EpistemicMesh
from dsghyper.protocol import AgentResult, Spectrum


class EpistemicMeshTests(unittest.TestCase):
    def result(self, agent: str, data: dict) -> AgentResult:
        return AgentResult.from_model(agent, data)

    def test_global_claim_ids_and_targeted_challenges(self):
        mesh = EpistemicMesh()
        round1 = {
            "red": self.result("red", {
                "claims": [{"claim_id": "c1", "text": "single point of failure", "confidence": 0.8, "salience": 0.9}],
                "confidence": 0.8,
            }),
            "green": self.result("green", {"claims": [], "confidence": 0.5}),
            "blue": self.result("blue", {"claims": [], "confidence": 0.5}),
            "gamma": self.result("gamma", {"claims": [], "confidence": 0.5}),
        }
        report1 = mesh.ingest_round(1, round1)
        self.assertEqual(report1.accepted_claims, 1)
        gid = "r1:red:c1"
        self.assertIn(gid, mesh.nodes)

        round2 = {
            "red": self.result("red", {"claims": [], "confidence": 0.5}),
            "green": self.result("green", {
                "challenges": [{"target_agent": "red", "claim_id": "c1", "reason": "redundancy exists", "severity": 0.8, "confidence": 0.9}],
                "confidence": 0.7,
            }),
            "blue": self.result("blue", {"claims": [], "confidence": 0.5}),
            "gamma": self.result("gamma", {"claims": [], "confidence": 0.5}),
        }
        report2 = mesh.ingest_round(2, round2)
        self.assertEqual(report2.accepted_challenges, 1)
        self.assertEqual(report2.resolved_challenges[0].target_claim_id, gid)

    def test_unresolved_challenge_does_not_resolve(self):
        mesh = EpistemicMesh()
        report = mesh.ingest_round(1, {
            "red": self.result("red", {"claims": [], "confidence": 0.5}),
            "green": self.result("green", {
                "challenges": [{"target_agent": "red", "claim_id": "missing", "reason": "no such claim", "severity": 1, "confidence": 1}],
                "confidence": 0.7,
            }),
            "blue": self.result("blue", {"claims": [], "confidence": 0.5}),
            "gamma": self.result("gamma", {"claims": [], "confidence": 0.5}),
        })
        self.assertEqual(report.accepted_challenges, 0)
        self.assertEqual(mesh.metrics.unresolved_challenges, 1)

    def test_selective_route_honors_claim_budget(self):
        mesh = EpistemicMesh(CommunicationBudget(max_claims=2, max_chars=20000))
        claims = [
            {"claim_id": f"c{i}", "text": f"claim {i}", "confidence": 0.6 + i * 0.03, "salience": 0.5 + i * 0.04}
            for i in range(6)
        ]
        mesh.ingest_round(1, {
            "red": self.result("red", {"claims": claims, "confidence": 0.8}),
            "green": self.result("green", {"claims": [], "confidence": 0.5}),
            "blue": self.result("blue", {"claims": [], "confidence": 0.5}),
            "gamma": self.result("gamma", {"claims": [], "confidence": 0.5}),
        })
        route = mesh.route_for("blue", current_round=2, spectrum=Spectrum(), influence={})
        self.assertLessEqual(len(route["claims"]), 2)
        self.assertGreater(mesh.metrics.dropped_claims_budget, 0)

    def test_information_requests_are_targeted(self):
        mesh = EpistemicMesh()
        mesh.ingest_round(1, {
            "red": self.result("red", {
                "information_requests": [{
                    "recipient": "blue",
                    "question": "Can the failover claim be verified?",
                    "reason": "changes severity",
                    "utility": 0.9,
                }],
                "confidence": 0.6,
            }),
            "green": self.result("green", {"claims": [], "confidence": 0.5}),
            "blue": self.result("blue", {"claims": [], "confidence": 0.5}),
            "gamma": self.result("gamma", {"claims": [], "confidence": 0.5}),
        })
        blue_route = mesh.route_for("blue", current_round=2, spectrum=Spectrum(), influence={})
        green_route = mesh.route_for("green", current_round=2, spectrum=Spectrum(), influence={})
        self.assertEqual(len(blue_route["information_requests"]), 1)
        self.assertEqual(green_route["information_requests"], [])

    def test_quorum_is_not_boolean_truth(self):
        mesh = EpistemicMesh()
        mesh.ingest_round(1, {
            "red": self.result("red", {"claims": [{"claim_id": "c1", "text": "risk exists", "confidence": 0.7, "salience": 0.9}], "confidence": 0.7}),
            "green": self.result("green", {"claims": [], "confidence": 0.5}),
            "blue": self.result("blue", {"claims": [], "confidence": 0.5}),
            "gamma": self.result("gamma", {"claims": [], "confidence": 0.5}),
        })
        quorum = mesh.quorum("r1:red:c1", {})
        self.assertIn(quorum["status"], {"weak", "provisional", "cross_supported", "contested"})
        self.assertNotIn("true", quorum)
        self.assertNotIn("false", quorum)


if __name__ == "__main__":
    unittest.main()
