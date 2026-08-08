from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .protocol import digest_json, stable_json, utc_now


@dataclass(frozen=True, slots=True)
class LedgerRecord:
    seq: int
    timestamp: str
    trace_id: str
    event: str
    subject: str
    payload_hash: str
    previous_hash: str
    record_hash: str


class TamperEvidentLedger:
    """Per-run append-only hash chain.

    The ledger stores hashes and routing metadata, not model prompts/results. A fresh file is
    used per trace so chain continuity is unambiguous. It is tamper-evident, not immutable.
    """

    def __init__(self, path: Path, trace_id: str, require_persistence: bool = False):
        self.path = path
        self.trace_id = trace_id
        self.require_persistence = require_persistence
        self.previous_hash = "0" * 64
        self.records: list[LedgerRecord] = []
        self.persistence_error: str | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists() and self.path.stat().st_size:
                raise RuntimeError(f"refusing to append to existing per-trace ledger: {self.path}")
        except Exception as exc:
            self.persistence_error = f"{type(exc).__name__}: {exc}"
            if require_persistence:
                raise

    def append(self, event: str, subject: str, payload: Any) -> LedgerRecord:
        bare = {
            "seq": len(self.records),
            "timestamp": utc_now(),
            "trace_id": self.trace_id,
            "event": event,
            "subject": subject,
            "payload_hash": digest_json(payload),
            "previous_hash": self.previous_hash,
        }
        record_hash = digest_json(bare)
        record = LedgerRecord(**bare, record_hash=record_hash)
        self.records.append(record)
        self.previous_hash = record_hash
        if self.persistence_error is None:
            try:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(stable_json(asdict(record)) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
            except Exception as exc:
                self.persistence_error = f"{type(exc).__name__}: {exc}"
                if self.require_persistence:
                    raise
        return record

    @staticmethod
    def verify_file(path: Path) -> tuple[bool, str]:
        previous = "0" * 64
        try:
            with path.open("r", encoding="utf-8") as handle:
                for expected_seq, line in enumerate(handle):
                    data = json.loads(line)
                    if data.get("seq") != expected_seq:
                        return False, f"sequence mismatch at {expected_seq}"
                    if data.get("previous_hash") != previous:
                        return False, f"previous_hash mismatch at {expected_seq}"
                    claimed = data.pop("record_hash", "")
                    computed = digest_json(data)
                    if claimed != computed:
                        return False, f"record_hash mismatch at {expected_seq}"
                    previous = claimed
            return True, previous
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"
