"""Synthetic-only immutable registration attempt recovery and tamper tests."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.v12_attempt_journal import (
    AttemptJournal,
    AttemptJournalError,
    attempt_path,
    verify_attempt,
)
from scripts.v12_journaled_readonly_port import JournaledReadOnlyPort

REGISTRATION = "a" * 64
RAW_SHA = "b" * 64


def make(tmp_path: Path) -> tuple[AttemptJournal, Path]:
    path = attempt_path(tmp_path, REGISTRATION)
    journal = AttemptJournal(path, REGISTRATION, "SYNTHETIC", clock=lambda: (
        "2026-10-19T12:00:00+00:00"
    ))
    return journal, path


def test_start_is_durable_before_any_broker_and_unfinished_is_failure(
    tmp_path: Path,
) -> None:
    journal, path = make(tmp_path)
    content = path.read_text("utf-8")
    assert "ATTEMPT_STARTED" in content
    assert "EXNESS_XAUUSD_DEMO_READ_ONLY_NOT_ADMITTED" in content
    journal.close()
    assert verify_attempt(path, REGISTRATION) == "INCOMPLETE_FAIL_CLOSED"
    with pytest.raises(FileExistsError):
        AttemptJournal(path, REGISTRATION, "WOULD_RETRY")


def test_explicit_failure_persists_irrespective_of_private_output(
    tmp_path: Path,
) -> None:
    journal, path = make(tmp_path)
    journal.append("POLL_QUOTE", {
        "ordinal": 0, "bid": "2000.0", "ask": "2000.2", "time_msc": 1,
    })
    journal.failed("CaptureSafetyError")
    journal.close()
    assert verify_attempt(path, REGISTRATION) == "FAIL_CLOSED"
    assert "POLL_QUOTE" in path.read_text("utf-8")
    with pytest.raises(FileExistsError):
        AttemptJournal(path, REGISTRATION, "SYNTHETIC_SECOND_ATTEMPT")


def test_success_is_only_raw_complete_not_calibrated(
    tmp_path: Path,
) -> None:
    journal, path = make(tmp_path)
    journal.append("POLL_QUOTE", {"ordinal": 0, "bid": "1", "ask": "2"})
    journal.success(RAW_SHA)
    journal.failed("LATER_FABRICATED")  # closed journals ignore later failures
    with pytest.raises(AttemptJournalError, match="closed"):
        journal.append("POLL_QUOTE", {"ordinal": 1})
    journal.close()
    assert verify_attempt(path, REGISTRATION, RAW_SHA) == (
        "COMPLETED_RAW_NOT_ADMITTED"
    )
    with pytest.raises(AttemptJournalError, match="not independently matched"):
        verify_attempt(path, REGISTRATION, "c" * 64)


def test_tampering_middle_event_detected_even_with_later_success(
    tmp_path: Path,
) -> None:
    journal, path = make(tmp_path)
    journal.append("POLL_QUOTE", {"bid": "2000", "ask": "2001"})
    journal.success(RAW_SHA)
    journal.close()
    path.chmod(0o600)
    payload = path.read_bytes()
    path.write_bytes(payload.replace(b"2000", b"3000", 1))
    with pytest.raises(AttemptJournalError, match="tampered"):
        verify_attempt(path, REGISTRATION, RAW_SHA)


def test_missing_last_line_and_truncated_partial_line_fails_closed(
    tmp_path: Path,
) -> None:
    journal, path = make(tmp_path)
    journal.append("POLL_QUOTE", {"bid": "2000"})
    journal.success(RAW_SHA)
    journal.close()
    path.chmod(0o600)
    lines = path.read_bytes().splitlines(keepends=True)
    path.write_bytes(b"".join(lines[:-1]))
    assert verify_attempt(path, REGISTRATION) == "INCOMPLETE_FAIL_CLOSED"
    path.write_bytes(b"".join(lines[:-1]) + b'{"partial":')
    with pytest.raises(AttemptJournalError, match="truncated"):
        verify_attempt(path, REGISTRATION)


def test_cannot_append_a_fabricated_success_after_recorded_fail(
    tmp_path: Path,
) -> None:
    journal, path = make(tmp_path)
    journal.failed("NetworkDisconnected")
    journal.close()
    path.chmod(0o600)
    record = {
        "seq": 2, "prev_sha256": "0" * 64,
        "timestamp_utc": "2026-10-19T12:00:00Z",
        "kind": "COMPLETED_RAW_NOT_ADMITTED", "details": {},
    }
    with path.open("ab") as output:
        output.write(json.dumps(record).encode() + b"\n")
    with pytest.raises(AttemptJournalError):
        verify_attempt(path, REGISTRATION)


def test_private_attempt_name_is_bound_to_sha_and_registration(
    tmp_path: Path,
) -> None:
    path = attempt_path(tmp_path, REGISTRATION)
    assert path.name == "v12-attempt-" + REGISTRATION + ".jsonl"
    with pytest.raises(AttemptJournalError):
        attempt_path(tmp_path, "bad")
    journal, path = make(tmp_path)
    journal.failed("Fail")
    journal.close()
    with pytest.raises(AttemptJournalError, match="filename"):
        verify_attempt(path, "b" * 64)


class FakePort:
    def __init__(self) -> None:
        self.tick_counter = 0

    def terminal_info(self) -> dict[str, bool]:
        return {"connected": True, "tradeapi_disabled": True}

    def account_info(self) -> SimpleNamespace:
        return SimpleNamespace(currency="USD")

    def positions_get(self) -> tuple[()]:
        return ()

    def orders_get(self) -> tuple[()]:
        return ()

    def symbol_info(self, symbol: str) -> dict[str, str]:
        assert symbol == "XAUUSD"
        return {"trade_tick_size": "0.01"}

    def symbol_info_tick(self, symbol: str) -> dict[str, str | int]:
        self.tick_counter += 1
        return {
            "time_msc": 1792400000000 + self.tick_counter,
            "bid": "2040.01",
            "ask": "2040.16",
        }

    def copy_ticks_range(
        self, symbol: str, start: datetime, end: datetime, flags: int
    ) -> list[dict[str, str | int]]:
        assert symbol == "XAUUSD" and flags == 1
        assert end - start == timedelta(minutes=10)
        return [{
            "time": int(start.timestamp()), "time_msc": int(start.timestamp()*1000),
            "bid": "2040.01", "ask": "2040.16", "flags": 134,
        }]


def test_wrapper_preserves_partial_quotes_and_chunk_source_flags(
    tmp_path: Path,
) -> None:
    journal, path = make(tmp_path)
    port = JournaledReadOnlyPort(FakePort(), journal)
    assert port.terminal_info()["tradeapi_disabled"] is True
    assert port.account_info() is not None
    assert port.positions_get() == ()
    assert port.orders_get() == ()
    assert port.symbol_info("XAUUSD")["trade_tick_size"] == "0.01"
    assert port.symbol_info_tick("XAUUSD")["ask"] == "2040.16"
    start = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
    port.copy_ticks_range("XAUUSD", start, start + timedelta(minutes=10), 1)
    journal.failed("SyntheticLoss")
    journal.close()
    evidence = path.read_text("utf-8")
    assert "POLL_QUOTE" in evidence
    assert "TRUE_TICK_RANGE" in evidence
    assert '"flags":134' in evidence
    assert verify_attempt(path, REGISTRATION) == "FAIL_CLOSED"


def test_journal_has_no_order_methods_or_mt5_import() -> None:
    from scripts import v12_attempt_journal, v12_journaled_readonly_port

    text = Path(v12_attempt_journal.__file__).read_text("utf-8") + (
        Path(v12_journaled_readonly_port.__file__).read_text("utf-8")
    )
    for token in ("import MetaTrader5", "order_send(", "order_check(",
                  "order_calc_margin(", "order_calc_profit(", "os.system("):
        assert token not in text
    assert hashlib.sha256(text.encode()).hexdigest()
