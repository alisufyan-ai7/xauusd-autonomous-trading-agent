"""Adversarial offline durable attempt and partial-data replay tests.

No MT5 connection. A real source hash does not establish provider authenticity.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts.v12_attempt_journal import (
    AttemptJournal, AttemptJournalError, attempt_path, verify_attempt,
)
from scripts.v12_journaled_readonly_port import JournaledReadOnlyPort

REG = "a" * 64
RAW = "b" * 64


def build(tmp_path: Path) -> AttemptJournal:
    return AttemptJournal(
        attempt_path(tmp_path, REG), REG, "SYNTHETIC_REHEARSAL",
        clock=lambda: "2026-10-20T10:00:00+00:00",
    )


def test_start_fsynced_and_terminal_failure_survives(tmp_path: Path) -> None:
    j = build(tmp_path)
    assert j.path.is_file()
    assert verify_attempt(j.path, REG) == "INCOMPLETE_FAIL_CLOSED"
    j.append("POLL_QUOTE", {"ordinal": 0, "bid": "1.00", "ask": "1.01"})
    j.failed("CaptureSafetyError")
    j.close()
    assert verify_attempt(j.path, REG) == "FAIL_CLOSED"
    with pytest.raises(AttemptJournalError, match="already exists"):
        build(tmp_path)


def test_crash_with_no_final_event_is_incomplete_not_erasable(tmp_path: Path) -> None:
    j = build(tmp_path)
    j.append("TERMINAL_READ", {"external_python_trading_disabled": False})
    j.close()  # models process loss before terminal status was written
    assert verify_attempt(j.path, REG) == "INCOMPLETE_FAIL_CLOSED"
    with pytest.raises(AttemptJournalError, match="already exists"):
        build(tmp_path)


def test_success_requires_matching_raw_digest_no_execution_authority(
    tmp_path: Path,
) -> None:
    j = build(tmp_path)
    j.success(RAW)
    j.close()
    assert verify_attempt(j.path, REG, RAW) == "COMPLETED_RAW_NOT_ADMITTED"
    with pytest.raises(AttemptJournalError, match="SHA"):
        verify_attempt(j.path, REG, "f" * 64)
    with pytest.raises(AttemptJournalError, match="closed"):
        j.append("POLL_QUOTE", {"ordinal": 1})


def test_mutated_or_truncated_wal_rejected(tmp_path: Path) -> None:
    j = build(tmp_path)
    j.append("POLL_QUOTE", {"ordinal": 0, "bid": "1.00", "ask": "1.01"})
    j.close()
    data = j.path.read_bytes()
    assert verify_attempt(j.path, REG) == "INCOMPLETE_FAIL_CLOSED"
    j.path.chmod(0o600)
    j.path.write_bytes(data.replace(b"1.01", b"1.11"))
    with pytest.raises(AttemptJournalError, match="tampered"):
        verify_attempt(j.path, REG)
    j.path.write_bytes(data[:-1])
    with pytest.raises(AttemptJournalError, match="truncated"):
        verify_attempt(j.path, REG)


def test_appended_events_after_success_cannot_rebrand_attempt(tmp_path: Path) -> None:
    j = build(tmp_path)
    j.success(RAW)
    j.close()
    j.path.chmod(0o600)
    with j.path.open("ab") as f:
        f.write(b'{"kind":"FAIL_CLOSED"}\n')
    with pytest.raises(AttemptJournalError, match="after terminal"):
        verify_attempt(j.path, REG)


def test_duplicate_registration_never_creates_second_attempt(tmp_path: Path) -> None:
    j = build(tmp_path)
    with pytest.raises(AttemptJournalError, match="already exists"):
        build(tmp_path)
    j.failed("AnySourceTimeout")
    j.close()


class FakeReadOnlyPort:
    def terminal_info(self) -> dict[str, Any]:
        return {"tradeapi_disabled": True, "connected": True}

    def account_info(self) -> dict[str, Any]:
        return {"login": 12345678}

    def positions_get(self) -> tuple[()]:
        return ()

    def orders_get(self) -> tuple[()]:
        return ()

    def symbol_info(self, symbol: str) -> dict[str, str]:
        assert symbol == "XAUUSD"
        return {"name": symbol}

    def symbol_info_tick(self, symbol: str) -> dict[str, Any]:
        assert symbol == "XAUUSD"
        return {"time_msc": 1792504800000, "bid": 4000.0, "ask": 4000.3}

    def copy_ticks_range(
        self, symbol: str, start: datetime, end: datetime, flags: int
    ) -> list[dict[str, Any]]:
        assert symbol == "XAUUSD"
        assert end - start == timedelta(minutes=10)
        assert flags == 3
        return [{
            "time_msc": 1792504800000, "time": 1792504800,
            "bid": 4000.0, "ask": 4000.3, "flags": 3,
        }]


def test_wrapped_readonly_port_preserves_quotes_and_original_order(
    tmp_path: Path,
) -> None:
    j = build(tmp_path)
    port = JournaledReadOnlyPort(FakeReadOnlyPort(), j)
    assert port.terminal_info()["tradeapi_disabled"] is True
    assert port.account_info()["login"] == 12345678
    assert port.positions_get() == ()
    assert port.orders_get() == ()
    assert port.symbol_info("XAUUSD")["name"] == "XAUUSD"
    assert port.symbol_info_tick("XAUUSD")["bid"] == 4000.0
    a = datetime(2026, 10, 20, 12, tzinfo=UTC)
    assert len(port.copy_ticks_range("XAUUSD", a, a + timedelta(minutes=10), 3)) == 1
    j.failed("synthetic_interruption")
    j.close()
    rows = [json.loads(row) for row in j.path.read_text("ascii").splitlines()]
    assert [r["kind"] for r in rows].count("POLL_QUOTE") == 1
    assert [r["kind"] for r in rows].count("TRUE_TICK_RANGE") == 1
    raw = next(r for r in rows if r["kind"] == "TRUE_TICK_RANGE")
    assert raw["details"]["raw_records"][0]["flags"] == 3
    assert verify_attempt(j.path, REG) == "FAIL_CLOSED"


def test_unknown_symbol_rejected_before_mt5_call(tmp_path: Path) -> None:
    j = build(tmp_path)
    port = JournaledReadOnlyPort(FakeReadOnlyPort(), j)
    with pytest.raises(ValueError, match="XAUUSD"):
        port.symbol_info_tick("EURUSD")
    with pytest.raises(ValueError, match="XAUUSD"):
        port.symbol_info("EURUSD")
    j.failed("rejected_other_symbol")
    j.close()


def test_journal_source_contains_no_order_api_or_mt5_module() -> None:
    from inspect import getsource

    from scripts import v12_attempt_journal, v12_journaled_readonly_port

    for module in (v12_attempt_journal, v12_journaled_readonly_port):
        source = getsource(module)
        for forbidden in (
            "import MetaTrader5", "order_" + "send(", "order_" + "check(",
            "order_" + "calc_margin(", "order_" + "close(",
            "symbol_select(", "terminal_login(", "subprocess.",
        ):
            assert forbidden not in source
