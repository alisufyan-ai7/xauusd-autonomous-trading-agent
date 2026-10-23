from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from xauusd_agent.ops.v2_durable_paper_ledger import (
    DurablePaperLedger,
    reconcile_paper_exposure,
)

FINGERPRINT = "f" * 64
NOW = datetime(2026, 10, 22, 12, tzinfo=UTC)


def test_journal_persists_restart_then_reconciles_only_known_position(tmp_path: Path):
    path = tmp_path / "synthetic.sqlite"
    with DurablePaperLedger(path, demo_fingerprint_sha256=FINGERPRINT) as db:
        start = db.inspect()
        assert start.state == "KILLED"
        ready = db.advance(
            expected_revision=start.revision, event="SIMULATE_ARM",
            synthetic_key="SYNTHETIC-arm",
        )
        intent = db.advance(
            expected_revision=ready.revision, event="SIMULATE_INTENT",
            synthetic_key="SYNTHETIC-intent",
        )
        assert intent.state == "PAPER_INTENT"
    with DurablePaperLedger(path, demo_fingerprint_sha256=FINGERPRINT) as db2:
        assert db2.inspect().revision == intent.revision
        known = db2.advance(
            expected_revision=intent.revision, event="SIMULATE_ACK_KNOWN",
            synthetic_key="SYNTHETIC-known",
        )
        assert reconcile_paper_exposure(
            ledger=known, expected_synthetic_position_hash="a" * 64,
            observed_position_hashes=("a" * 64,),
            observed_at=NOW, current_time=NOW,
        ) == "PAPER_KNOWN_POSITION_MATCH_ONLY"
        assert reconcile_paper_exposure(
            ledger=known, expected_synthetic_position_hash="a" * 64,
            observed_position_hashes=("b" * 64,),
            observed_at=NOW, current_time=NOW,
        ) == "QUARANTINE_UNKNOWN_OR_MISSING_POSITION"


def test_stale_writer_and_duplicate_intent_are_rejected(tmp_path: Path):
    with DurablePaperLedger(
        tmp_path / "j.sqlite", demo_fingerprint_sha256=FINGERPRINT
    ) as db:
        first = db.advance(
            expected_revision=0, event="SIMULATE_ARM",
            synthetic_key="SYNTHETIC-arm",
        )
        with pytest.raises(ValueError, match="stale"):
            db.advance(
                expected_revision=0, event="SIMULATE_INTENT",
                synthetic_key="SYNTHETIC-old",
            )
        with pytest.raises(sqlite3.IntegrityError):
            db.advance(
                expected_revision=first.revision, event="SIMULATE_INTENT",
                synthetic_key="SYNTHETIC-arm",
            )
        assert db.inspect().state == "PAPER_READY"


def test_corrupted_local_journal_refuses_restart(tmp_path: Path):
    file = tmp_path / "journal.sqlite"
    with DurablePaperLedger(file, demo_fingerprint_sha256=FINGERPRINT) as db:
        db.advance(
            expected_revision=0, event="SIMULATE_ARM",
            synthetic_key="SYNTHETIC-a",
        )
    with sqlite3.connect(file) as conn:
        conn.execute(
            "UPDATE paper_events SET state='PAPER_INTENT' WHERE revision=1"
        )
    with DurablePaperLedger(file, demo_fingerprint_sha256=FINGERPRINT) as db2:
        with pytest.raises(ValueError, match="hash"):
            db2.inspect()


def test_account_fingerprint_switch_rejected(tmp_path: Path):
    file = tmp_path / "ledger.sqlite"
    with DurablePaperLedger(file, demo_fingerprint_sha256=FINGERPRINT):
        pass
    with pytest.raises(ValueError, match="identity"):
        DurablePaperLedger(file, demo_fingerprint_sha256="a" * 64)


def test_uncertain_exposure_quarantines_without_close_or_retry(tmp_path: Path):
    with DurablePaperLedger(
        tmp_path / "s.sqlite", demo_fingerprint_sha256=FINGERPRINT
    ) as db:
        locked = db.advance(
            expected_revision=0,
            event="SIMULATE_AMBIGUOUS_OR_UNKNOWN_EXPOSURE",
            synthetic_key="SYNTHETIC-uncertain",
        )
        assert locked.state == "QUARANTINED"
        with pytest.raises(ValueError, match="unsafe"):
            db.advance(
                expected_revision=locked.revision,
                event="SIMULATE_ARM", synthetic_key="SYNTHETIC-rearm",
            )
        assert reconcile_paper_exposure(
            ledger=locked, expected_synthetic_position_hash=None,
            observed_position_hashes=(),
            observed_at=NOW, current_time=NOW,
        ) == "QUARANTINE_HUMAN_ONLY"


def test_unknown_and_stale_broker_snapshot_cannot_authorize_position():
    with pytest.raises(ValueError, match="hash"):
        DurablePaperLedger(Path(":memory:"), demo_fingerprint_sha256="bad")
    from xauusd_agent.ops.v2_durable_paper_ledger import PaperLedgerStatus

    status = PaperLedgerStatus(3, "PAPER_KNOWN_OPEN", "a" * 64)
    assert "STALE" in reconcile_paper_exposure(
        ledger=status, expected_synthetic_position_hash="b" * 64,
        observed_position_hashes=("b" * 64,),
        observed_at=NOW - timedelta(seconds=10), current_time=NOW,
    )
    assert "UNKNOWN" in reconcile_paper_exposure(
        ledger=status, expected_synthetic_position_hash="b" * 64,
        observed_position_hashes=None, observed_at=NOW, current_time=NOW,
    )
    with pytest.raises(ValueError, match="never grants execution"):
        PaperLedgerStatus(0, "KILLED", "a" * 64, execution_permitted=True)
