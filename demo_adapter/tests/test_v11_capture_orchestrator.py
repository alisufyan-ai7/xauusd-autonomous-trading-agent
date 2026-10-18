"""No real MT5: injected clock/port 4h capture lifecycle and failures."""
from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from scripts.v11_capture_orchestrator import rehearse_orchestrator
from scripts.v11_readonly_collector import CaptureSafetyError, WindowContract

START = datetime(2026, 10, 19, 13, tzinfo=UTC)
END = START + timedelta(hours=4)


class Clock:
    def __init__(self, at: datetime = START):
        self.at = at

    def now(self) -> datetime:
        return self.at

    def sleep(self, duration: float) -> None:
        if duration < 0:
            raise AssertionError("negative sleep")
        self.at += timedelta(seconds=duration)


class FakePort:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.disabled = True
        self.connected = True
        self.positions: tuple[object, ...] | None = ()
        self.orders: tuple[object, ...] | None = ()
        self.polls = 0
        self.chunk_reads = 0

    def terminal_info(self) -> dict[str, object]:
        self.polls += 1
        return {"tradeapi_disabled": self.disabled, "connected": self.connected}

    def account_info(self) -> dict[str, object]:
        return {
            "trade_mode": 0, "company": "Exness Technologies Ltd",
            "server": "Exness-MT5Trial15", "currency": "USD", "login": 12345678,
        }

    def positions_get(self) -> tuple[object, ...] | None:
        return self.positions

    def orders_get(self) -> tuple[object, ...] | None:
        return self.orders

    def symbol_info(self, name: str) -> dict[str, object]:
        assert name == "XAUUSD"
        return {
            "trade_tick_size": "0.01", "trade_tick_value_loss": "1",
            "trade_contract_size": "100", "point": "0.01",
            "trade_stops_level": 10,
        }

    def symbol_info_tick(self, name: str) -> dict[str, object]:
        assert name == "XAUUSD"
        return {
            "time_msc": int(self.clock.now().timestamp() * 1000),
            "bid": "2000.00", "ask": "2000.20",
        }

    def copy_ticks_range(
        self, name: str, start: datetime, end: datetime, flags: int
    ) -> list[dict[str, object]]:
        assert name == "XAUUSD"
        assert flags == 1
        self.chunk_reads += 1
        from_ms = int(start.timestamp() * 1000)
        stop_ms = int(end.timestamp() * 1000)
        return [
            {"time_msc": v, "bid": "2000.00", "ask": "2000.20", "flags": 134}
            for v in range(from_ms, stop_ms, 1000)
        ]


def contract() -> WindowContract:
    fp = hashlib.sha256(
        b"Exness Technologies Ltd|Exness-MT5Trial15|12345678|USD"
    ).hexdigest()
    return WindowContract(
        start_utc=START, end_utc=END, expected_identity_sha256=fp,
        registration_sha256="1" * 64, collector_source_sha256="2" * 64,
        broker_session_source_sha256="3" * 64,
        event_guard_source_sha256="4" * 64,
        exact_owner_approval_id="SYNTHETIC_DOES_NOT_AUTHORIZE_A_REAL_RUN",
    )


def test_all_2880_slots_and_true_ticks_quote_only_not_admitted() -> None:
    clock = Clock()
    port = FakePort(clock)
    result = rehearse_orchestrator(
        port, contract(), now_utc=clock.now, sleep_seconds=clock.sleep,
        copy_ticks_all_flags=1,
    )
    assert result.status == "READ_ONLY_QUOTE_CAPTURE_NOT_COST_CALIBRATION"
    assert result.observed_poll_count == 2880
    assert result.observed_tick_count == 14400
    assert result.coverage.current_adverse_cost_usd is None
    assert result.coverage.stressed_adverse_cost_usd is None
    assert port.chunk_reads == 24
    assert clock.now() == END
    assert len(result.polls_sha256) == 64
    assert result.polls_sha256 != result.ticks_sha256


def test_starting_after_prospective_start_fails_before_polling() -> None:
    clock = Clock(START + timedelta(seconds=1))
    port = FakePort(clock)
    with pytest.raises(CaptureSafetyError, match="after prospectively"):
        rehearse_orchestrator(port, contract(), now_utc=clock.now,
                             sleep_seconds=clock.sleep, copy_ticks_all_flags=1)
    assert port.chunk_reads == 0


def test_session_contract_inconsistent_fails() -> None:
    clock = Clock()
    port = FakePort(clock)
    modified = replace(contract(), end_utc=END + timedelta(seconds=1))
    with pytest.raises(CaptureSafetyError, match="not exact 4h"):
        rehearse_orchestrator(port, modified, now_utc=clock.now,
                             sleep_seconds=clock.sleep, copy_ticks_all_flags=1)


def test_external_python_trading_enabled_blocks_before_tick_capture() -> None:
    clock = Clock()
    port = FakePort(clock)
    port.disabled = False
    with pytest.raises(CaptureSafetyError):
        rehearse_orchestrator(port, contract(), now_utc=clock.now,
                             sleep_seconds=clock.sleep, copy_ticks_all_flags=1)
    assert port.chunk_reads == 0


def test_missing_positions_observation_fails_closed() -> None:
    clock = Clock()
    port = FakePort(clock)
    port.positions = None
    with pytest.raises(CaptureSafetyError, match="exposure unknown"):
        rehearse_orchestrator(port, contract(), now_utc=clock.now,
                             sleep_seconds=clock.sleep, copy_ticks_all_flags=1)


def test_disabled_terminal_during_capture_aborts_before_tick_source() -> None:
    clock = Clock()
    port = FakePort(clock)

    def disconnect_after_first_minute() -> datetime:
        if clock.at >= START + timedelta(seconds=60):
            port.connected = False
        return clock.now()

    with pytest.raises(CaptureSafetyError, match="disconnected"):
        rehearse_orchestrator(
            port, contract(), now_utc=disconnect_after_first_minute,
            sleep_seconds=clock.sleep, copy_ticks_all_flags=1,
        )
    assert port.chunk_reads == 0


def test_no_read_only_port_has_order_methods() -> None:
    import inspect

    from scripts import v11_capture_orchestrator

    source = inspect.getsource(v11_capture_orchestrator)
    for forbidden in ("order_send(", "order_check(", "order_calc_margin(",
                      "import MetaTrader5", "initialize(", "shutdown("):
        assert forbidden not in source
