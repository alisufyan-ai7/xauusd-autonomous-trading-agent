"""Durable OFFLINE DEMO paper intent journal; NO broker or order interfaces.

SQLite WAL + FULL synchronous durability, revision fencing, unique
idempotency keys and a hash-chain protect local synthetic execution studies.
No trading can be activated from this module. Unknown exposure is quarantined,
never automatically closed. Keep real account IDs/credentials out of storage.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

_ZERO = "0" * 64


@dataclass(frozen=True, slots=True)
class PaperLedgerStatus:
    revision: int
    state: str
    last_hash: str
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("paper ledger never grants execution")


def _digest(last_hash: str, revision: int, state: str, event: str, key: str) -> str:
    canonical = json.dumps(
        [last_hash, revision, state, event, key],
        separators=(",", ":"), ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


class DurablePaperLedger:
    """Local synthetic-only ledger for fault/restart tests; no broker handles."""

    def __init__(self, path: Path, *, demo_fingerprint_sha256: str) -> None:
        if (
            len(demo_fingerprint_sha256) != 64
            or any(c not in "0123456789abcdef" for c in demo_fingerprint_sha256)
        ):
            raise ValueError("sanitized 64-digit DEMO hash required")
        self._db = sqlite3.connect(str(path), timeout=1, isolation_level=None)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("PRAGMA busy_timeout=1000")
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS meta(
              singleton INTEGER PRIMARY KEY CHECK(singleton=1),
              fingerprint TEXT NOT NULL
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS paper_events(
              revision INTEGER PRIMARY KEY,
              state TEXT NOT NULL,
              event TEXT NOT NULL,
              idempotency_key TEXT NOT NULL UNIQUE,
              previous_hash TEXT NOT NULL,
              event_hash TEXT NOT NULL
            )
        """)
        self._db.execute("INSERT OR IGNORE INTO meta VALUES(1, ?)", (demo_fingerprint_sha256,))
        stored = self._db.execute(
            "SELECT fingerprint FROM meta WHERE singleton=1"
        ).fetchone()
        if stored is None or stored[0] != demo_fingerprint_sha256:
            self.close()
            raise ValueError("DEMO identity does not match persisted journal")
        if self._db.execute("SELECT COUNT(*) FROM paper_events").fetchone()[0] == 0:
            self._append_raw(0, "KILLED", "INIT_PAPER_ONLY", "SYNTHETIC-INITIAL")

    def __enter__(self) -> DurablePaperLedger:
        return self

    def __exit__(self, *unused: object) -> None:
        self.close()

    def close(self) -> None:
        self._db.close()

    def _append_raw(self, rev: int, state: str, event: str, key: str) -> None:
        previous = self._db.execute(
            "SELECT event_hash FROM paper_events ORDER BY revision DESC LIMIT 1"
        ).fetchone()
        old = previous[0] if previous else _ZERO
        hashed = _digest(old, rev, state, event, key)
        self._db.execute(
            "INSERT INTO paper_events VALUES(?,?,?,?,?,?)",
            (rev, state, event, key, old, hashed),
        )

    def inspect(self) -> PaperLedgerStatus:
        previous = _ZERO
        rows = self._db.execute(
            "SELECT revision,state,event,idempotency_key,previous_hash,event_hash "
            "FROM paper_events ORDER BY revision"
        ).fetchall()
        if not rows:
            raise ValueError("empty journal is corrupt")
        for expected_rev, (rev, state, event, key, prev, h) in enumerate(rows):
            if rev != expected_rev or prev != previous or h != _digest(
                prev, rev, state, event, key
            ):
                raise ValueError("local journal hash/revision integrity failure")
            previous = h
        return PaperLedgerStatus(rows[-1][0], rows[-1][1], previous)

    def advance(
        self, *, expected_revision: int, event: str, synthetic_key: str
    ) -> PaperLedgerStatus:
        """CAS append; broker order submission is intentionally absent."""
        if not synthetic_key.startswith("SYNTHETIC-"):
            raise ValueError("synthetic idempotency identity only")
        edges = {
            ("KILLED", "SIMULATE_ARM"): "PAPER_READY",
            ("PAPER_READY", "SIMULATE_INTENT"): "PAPER_INTENT",
            ("PAPER_INTENT", "SIMULATE_ACK_KNOWN"): "PAPER_KNOWN_OPEN",
            ("PAPER_KNOWN_OPEN", "SIMULATE_EXIT_INTENT"): "PAPER_EXIT_PENDING",
            ("PAPER_EXIT_PENDING", "SIMULATE_FLAT_RECONCILED"): "PAPER_FLAT",
            ("PAPER_FLAT", "SIMULATE_DISARM"): "KILLED",
        }
        self._db.execute("BEGIN IMMEDIATE")
        try:
            old = self.inspect()
            if old.revision != expected_revision:
                raise ValueError("stale writer revision / duplicate intent")
            if event == "SIMULATE_AMBIGUOUS_OR_UNKNOWN_EXPOSURE":
                next_state = "QUARANTINED"
            else:
                next_state = edges.get((old.state, event))
                if next_state is None:
                    raise ValueError("unknown or unsafe paper transition")
            self._append_raw(old.revision + 1, next_state, event, synthetic_key)
            result = self.inspect()
            self._db.execute("COMMIT")
            return result
        except Exception:
            self._db.execute("ROLLBACK")
            raise


def reconcile_paper_exposure(
    *,
    ledger: PaperLedgerStatus,
    expected_synthetic_position_hash: str | None,
    observed_position_hashes: tuple[str, ...] | None,
    observed_at: datetime | None,
    current_time: datetime,
    maximum_age: timedelta = timedelta(seconds=5),
) -> str:
    """OFFLINE decision only. No order, close, modify or automatic resumption."""
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        return "QUARANTINE_CLOCK_INVALID"
    if (
        observed_at is None
        or observed_at.tzinfo is None
        or observed_at.utcoffset() is None
        or observed_at > current_time
        or current_time - observed_at > maximum_age
    ):
        return "QUARANTINE_BROKER_SNAPSHOT_STALE_OR_UNKNOWN"
    if observed_position_hashes is None:
        return "QUARANTINE_BROKER_EXPOSURE_UNKNOWN"
    if ledger.state == "QUARANTINED":
        return "QUARANTINE_HUMAN_ONLY"
    if ledger.state == "PAPER_KNOWN_OPEN":
        if (
            expected_synthetic_position_hash is None
            or observed_position_hashes != (expected_synthetic_position_hash,)
        ):
            return "QUARANTINE_UNKNOWN_OR_MISSING_POSITION"
        return "PAPER_KNOWN_POSITION_MATCH_ONLY"
    if observed_position_hashes:
        return "QUARANTINE_UNOWNED_EXPOSURE"
    return "PAPER_FLAT_OR_PREENTRY_NO_BROKER_AUTHORITY"
