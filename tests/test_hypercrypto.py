from __future__ import annotations

import unittest

from hypercrypto import LocalVectorBackend, SecureSemanticFabric


class HyperCryptoTests(unittest.TestCase):
    def setUp(self):
        self.fabric = SecureSemanticFabric(b"K" * 32, backend=LocalVectorBackend())
        self.cap = self.fabric.issue_capability(
            "orchestrator", "hypercomm", ("read", "write"), max_results=8
        )

    def test_sealed_memory_roundtrip_and_search(self):
        self.fabric.remember(
            namespace="hypercomm",
            owner="red",
            text="risk analysis for database outage",
            metadata={"role": "red"},
            capability=self.cap,
        )
        self.fabric.remember(
            namespace="hypercomm",
            owner="green",
            text="recovery plan for database outage",
            metadata={"role": "green"},
            capability=self.cap,
        )
        hits = self.fabric.search(
            namespace="hypercomm",
            query="database outage recovery",
            capability=self.cap,
            limit=2,
        )
        self.assertEqual(len(hits), 2)
        self.assertTrue(all(hit.proof_valid for hit in hits))
        self.assertTrue(any("recovery" in hit.text for hit in hits))

    def test_capability_scope_is_enforced(self):
        wrong = self.fabric.issue_capability("agent", "other", ("read",))
        with self.assertRaises(PermissionError):
            self.fabric.search(namespace="hypercomm", query="x", capability=wrong)

    def test_read_only_capability_cannot_write(self):
        read_only = self.fabric.issue_capability("agent", "hypercomm", ("read",))
        with self.assertRaises(PermissionError):
            self.fabric.remember(
                namespace="hypercomm",
                owner="x",
                text="secret",
                metadata={},
                capability=read_only,
            )

    def test_tampered_attestation_is_rejected(self):
        record_id = self.fabric.remember(
            namespace="hypercomm",
            owner="blue",
            text="verify claim",
            metadata={},
            capability=self.cap,
        )
        record = self.fabric.backend.records[record_id]
        record.attestation = record.attestation[:-1] + (
            "A" if record.attestation[-1] != "A" else "B"
        )
        hits = self.fabric.search(
            namespace="hypercomm", query="verify claim", capability=self.cap
        )
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
