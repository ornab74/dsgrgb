from __future__ import annotations

import unittest

from dsghyper.protocol import AgentResult
from dsghyper.research import (
    AdvancedSecuritySurface,
    CausalCreditEngine,
    FreshnessPolicy,
    InformationMarket,
    MarketBid,
    MultiModelQuorum,
    PolicyEnvelopeAuthority,
    SpecialistScheduler,
)


class Edge:
    def __init__(self, source, target, kind, confidence=1.0):
        self.source_claim_id = source
        self.target_claim_id = target
        self.kind = kind
        self.confidence = confidence


class ResearchLayerTests(unittest.TestCase):
    def test_freshness_expires_old_claims(self):
        policy = FreshnessPolicy(ttl_rounds=3, half_life_rounds=2.0)
        self.assertEqual(policy.score(1, 5), 0.0)
        self.assertGreater(policy.score(2, 3), policy.score(2, 4))

    def test_information_market_is_budget_bounded_and_deterministic(self):
        bids = [
            MarketBid("a", "red", "blue", "c1", 1.0, 0.9, 0.9, 1.0, 120, {"x": 1}),
            MarketBid("b", "green", "blue", "c2", 0.8, 0.8, 0.8, 1.0, 120, {"x": 2}),
            MarketBid("c", "gamma", "blue", "c3", 0.2, 0.5, 0.3, 1.0, 120, {"x": 3}),
        ]
        market = InformationMarket(token_budget=240, max_winners=2)
        first = market.allocate("blue", bids)
        second = market.allocate("blue", list(reversed(bids)))
        self.assertLessEqual(first.tokens_used, 240)
        self.assertEqual([b.bid_id for b in first.winners], [b.bid_id for b in second.winners])
        self.assertEqual(first.allocation_digest, second.allocation_digest)

    def test_causal_credit_propagates_without_claiming_truth(self):
        engine = CausalCreditEngine()
        edges = [
            Edge("a", "b", "supports", 1.0),
            Edge("b", "c", "depends_on", 1.0),
        ]
        credit = engine.assign(["a", "b", "c"], edges, ["c"], max_depth=4)
        self.assertEqual(credit["c"].direct_credit, 1.0)
        self.assertGreater(credit["b"].propagated_credit, 0.0)
        self.assertGreater(credit["a"].propagated_credit, 0.0)

    def test_policy_envelope_detects_payload_change_and_nonce_replay(self):
        authority = PolicyEnvelopeAuthority(b"K" * 32)
        payload = {"claim": "c1", "value": 7}
        envelope = authority.issue(
            sender="red", audience="blue", purpose="verify", operations=("read",), payload=payload
        )
        self.assertTrue(authority.verify(envelope, audience="blue", operation="read", payload=payload, consume_nonce=True))
        self.assertFalse(authority.verify(envelope, audience="blue", operation="read", payload=payload, consume_nonce=True))
        self.assertFalse(authority.verify(envelope, audience="blue", operation="read", payload={"claim": "c1", "value": 8}))

    def test_specialist_scheduler_honors_hard_quota(self):
        contested = [
            {"claim": {"global_id": f"c{i}"}, "quorum": {"claim_id": f"c{i}", "support_mass": 1.0, "challenge_mass": 0.9, "review_diversity": 3}}
            for i in range(10)
        ]
        scheduler = SpecialistScheduler(max_specialists=2, token_quota=2000, min_conflict=0.1)
        plans = scheduler.plan(contested)
        self.assertLessEqual(len(plans), 2)
        self.assertLessEqual(sum(plan.quota_cost for plan in plans), 2000)

    def test_multi_model_quorum_is_bookkeeping_not_truth(self):
        a = AgentResult.from_model("sync", {"answer": "A", "confidence": 0.8, "status": "ok"})
        b = AgentResult.from_model("sync", {"answer": "B", "confidence": 0.6, "status": "ok"})
        report = MultiModelQuorum().summarize([("m1", a), ("m2", b)])
        public = report.__dict__ if hasattr(report, "__dict__") else None
        self.assertEqual(len(report.votes), 2)
        self.assertGreater(report.response_diversity, 0.0)
        self.assertFalse(hasattr(report, "truth"))
        self.assertIsNone(public)

    def test_advanced_security_surface_defaults_to_unavailable(self):
        status = AdvancedSecuritySurface().status()
        for name in (
            "threshold_authenticated_identity",
            "post_quantum_transport_identity",
            "oram_access_pattern_hiding",
            "pir_private_retrieval",
            "zero_knowledge_authorization",
        ):
            self.assertFalse(status[name]["implemented"])
            self.assertFalse(status[name]["active"])


if __name__ == "__main__":
    unittest.main()
