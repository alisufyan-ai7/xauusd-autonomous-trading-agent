"""Offline-only synthetic read-port tests; no MT5 import or network."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from scripts.v11_readonly_collector import (
    CaptureSafetyError,
    WindowContract,
    canonical_sha256,
    read_only_preflight,
)


def digest(login: int = 12345678) -> str:
    return hashlib.sha256(
        f"Exness Technologies Ltd|Exness-MT5Trial15|{login}|USD".encode()
    ).hexdigest()


def plan(**overrides: object) -> dict[str, object]:
    document: dict[str, object] = {
        "exact_window_start_utc": "2026-10-19T13:00:00Z",
        "exact_window_end_utc": "2026-10-19T17:00:00Z",
        "expected_demo_identity_fingerprint_sha256": digest(),
        "registration_sha256": "1" * 64,
        "exact_collector_source_sha256": "2" * 64,
        "broker_xauusd_session_source_sha256": "3" * 64,
        "official_event_guard_health_and_event_schedule_sha256": "4" * 64,
        "exact_owner_approval_id": "SYNTHETIC_FIXTURE_NOT_REAL_APPROVAL",
        "approval_for_vps_capture": "EXPLICIT_OWNER_APPROVED",
    }
    document.update(overrides)
    return document


class FakePort:
    def __init__(self) -> None:
        self.login = 12345678
        self.disabled = True
        self.positions: tuple[object, ...] | None = ()
        self.orders: tuple[object, ...] | None = ()
        self.calls: list[str] = []

    def terminal_info(self) -> dict[str, object]:
        self.calls.append("terminal_info")
        return {"connected": True, "tradeapi_disabled": self.disabled}

    def account_info(self) -> dict[str, object]:
        self.calls.append("account_info")
        return {
            "company": "Exness Technologies Ltd", "server": "Exness-MT5Trial15",
            "login": self.login, "currency": "USD", "trade_mode": 0,
        }

    def positions_get(self) -> tuple[object, ...] | None:
        self.calls.append("positions_get")
        return self.positions

    def orders_get(self) -> tuple[object, ...] | None:
        self.calls.append("orders_get")
        return self.orders

    def symbol_info(self, symbol: str) -> dict[str, object]:
        self.calls.append("symbol_info")
        assert symbol == "XAUUSD"
        return {
            "trade_tick_size": "0.01", "trade_tick_value_loss": "1",
            "trade_contract_size": "100", "point": "0.001",
            "trade_stops_level": 10,
        }

    def symbol_info_tick(self, symbol: str) -> dict[str, object]:
        self.calls.append("symbol_info_tick")
        assert symbol == "XAUUSD"
        return {"bid": "2000.0", "ask": "2000.2", "time_msc": 1792400000000}

    def copy_ticks_range(
        self, symbol: str, start: datetime, end: datetime, flags: int
    ) -> tuple[object, ...]:
        self.calls.append("copy_ticks_range")
        return ()


def test_fixture_preflight_only_allowlisted_reads() -> None:
    port = FakePort()
    evidence = read_only_preflight(port, WindowContract.from_record(plan()))
    assert evidence["calibration_status"] == "NOT_ADMITTED"
    assert evidence["broker_order_actions"] == 0
    assert evidence["identity_before"]["open_positions"] == "0"
    assert evidence["identity_after"]["pending_orders"] == "0"
    assert "login" not in str(evidence)
    assert canonical_sha256(evidence) == canonical_sha256(evidence)
    assert set(port.calls) == {
        "terminal_info", "account_info", "positions_get", "orders_get",
        "symbol_info", "symbol_info_tick",
    }


@pytest.mark.parametrize("bad", [
    {}, {"exact_window_start_utc": None}, {"registration_sha256": None},
    {"approval_for_vps_capture": "REQUIRED_SEPARATELY"},
    {"exact_owner_approval_id": ""},
    {"exact_window_end_utc": "2026-10-19T16:59:59Z"},
    {"exact_window_end_utc": "2026-10-19T17:00:00+05:00"},
    {"registration_sha256": "Z" * 64},
])
def test_missing_approval_window_or_hash_rejected(bad: dict[str, object]) -> None:
    invalid = plan(**bad) if bad else plan(approval_for_vps_capture="NOT_APPROVED")
    with pytest.raises(CaptureSafetyError):
        WindowContract.from_record(invalid)


@pytest.mark.parametrize("field,value", [
    ("disabled", False), ("login", 999), ("positions", (object(),)),
    ("orders", (object(),)), ("positions", None), ("orders", None),
])
def test_bad_identity_exposure_or_trading_permission_rejected(
    field: str, value: object
) -> None:
    port = FakePort()
    setattr(port, field, value)
    with pytest.raises(CaptureSafetyError):
        read_only_preflight(port, WindowContract.from_record(plan()))


def test_window_has_real_utc_timestamps_and_no_wall_clock_assumption() -> None:
    contract = WindowContract.from_record(plan())
    assert contract.end_utc - contract.start_utc == timedelta(hours=4)
    assert contract.start_utc.tzinfo == UTC


def test_source_has_no_mt5_import_or_trade_methods() -> None:
    import inspect
    from scripts import v11_readonly_collector as module

    source = inspect.getsource(module)
    assert "import MetaTrader5" not in source
    assert "order_send(" not in source
    assert "order_check(" not in source
    assert "order_calc_margin(" not in source
    assert "order_calc_profit(" not in source
