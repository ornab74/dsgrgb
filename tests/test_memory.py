from __future__ import annotations

import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path

from dsghyper.memory import LocalVectorBackend, SecureSemanticFabric, SQLiteVectorBackend


class SecureMemoryTests(unittest.TestCase):
    def make_fabric(self):
        return SecureSemanticFabric(b"K" * 32, backend=LocalVectorBackend(), blind_dimensions=128)

    def test_roundtrip_and_record_recomputation(self):
        fabric = self.make_fabric()
        cap = fabric.issue_capability("test", "ns", ("read", "write"), ttl_seconds=60, max_results=4)
        record_id = fabric.remember(
            namespace="ns", owner="green", text="database outage recovery plan",
            metadata={"role": "green"}, capability=cap,
        )
        hits = fabric.search(namespace="ns", query="database recovery", capability=cap, limit=4)
        self.assertEqual(hits[0].record_id, record_id)
        self.assertTrue(hits[0].proof_valid)
        self.assertIn("recovery", hits[0].text)

    def test_tampered_ciphertext_is_rejected_even_with_old_attestation(self):
        fabric = self.make_fabric()
        cap = fabric.issue_capability("test", "ns", ("read", "write"), ttl_seconds=60, max_results=4)
        record_id = fabric.remember(namespace="ns", owner="blue", text="verify claim", metadata={}, capability=cap)
        original = fabric.backend.records[record_id]
        tampered = replace(original, sealed_payload=original.sealed_payload[:-2] + "AA")
        fabric.backend.records[record_id] = tampered
        hits = fabric.search(namespace="ns", query="verify claim", capability=cap)
        self.assertEqual(hits, [])

    def test_capability_scope_and_revocation(self):
        fabric = self.make_fabric()
        cap = fabric.issue_capability("agent", "ns", ("read",), ttl_seconds=60, max_results=2)
        with self.assertRaises(PermissionError):
            fabric.remember(namespace="ns", owner="x", text="x", metadata={}, capability=cap)
        with self.assertRaises(PermissionError):
            fabric.search(namespace="other", query="x", capability=cap)
        fabric.capabilities.revoke(cap)
        with self.assertRaises(PermissionError):
            fabric.search(namespace="ns", query="x", capability=cap)

    def test_expired_capability_rejected(self):
        fabric = self.make_fabric()
        cap = fabric.issue_capability("agent", "ns", ("read",), ttl_seconds=1, max_results=2)
        time.sleep(1.05)
        with self.assertRaises(PermissionError):
            fabric.search(namespace="ns", query="x", capability=cap)

    def test_sqlite_persistence_with_same_master_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "memory.sqlite3"
            first = SecureSemanticFabric(b"Z" * 32, backend=SQLiteVectorBackend(path), blind_dimensions=128)
            write = first.issue_capability("writer", "ns", ("write",), ttl_seconds=60, max_results=1)
            first.remember(namespace="ns", owner="sync", text="persistent encrypted memory", metadata={}, capability=write)
            first.close()

            second = SecureSemanticFabric(b"Z" * 32, backend=SQLiteVectorBackend(path), blind_dimensions=128)
            read = second.issue_capability("reader", "ns", ("read",), ttl_seconds=60, max_results=4)
            hits = second.search(namespace="ns", query="persistent memory", capability=read)
            self.assertEqual(len(hits), 1)
            self.assertIn("persistent", hits[0].text)
            second.close()


if __name__ == "__main__":
    unittest.main()
