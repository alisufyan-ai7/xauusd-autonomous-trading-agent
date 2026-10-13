from __future__ import annotations

import json
import time

import pytest

from xauusd_agent.broker.mt5_readonly import MT5ReadOnlyAdapter, MT5ReadOnlyError
from xauusd_agent.host import HostSafetyError, broker_preflight, run_shadow_host
from xauusd_agent.storage import open_database, verify_startup


class FakeMT5:
    __version__ = "5.0.6090"

    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_TYPE_BUY_STOP_LIMIT = 6
    ORDER_TYPE_SELL_STOP_LIMIT = 7

    TIMEFRAME_M15 = 15
    TIMEFRAME_H1 = 60
    TIMEFRAME_H4 = 240

    def __init__(self) -> None:
        self.tradeapi_disabled = True
        self.connected = True
        self.positions: list[dict[str, object]] = []
        self.orders: list[dict[str, object]] = []
        self.fail_rates = False

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> None:
        return None

    def last_error(self) -> tuple[int, str]:
        return (0, "OK")

    def terminal_info(self) -> dict[str, object]:
        return {
            "connected": self.connected,
            "tradeapi_disabled": self.tradeapi_disabled,
            "name": "MetaTrader 5",
            "company": "MetaQuotes",
            "build": 5000,
        }

    def account_info(self) -> dict[str, object]:
        return {
            "login": 12345678,
            "server": "Exness-MT5Trial15",
            "company": "Exness",
            "currency": "USD",
            "leverage": 100,
            "trade_mode": 0,
            "equity": 10000.0,
            "margin_free": 10000.0,
            "margin": 0.0,
        }

    def symbol_info(self, symbol: str) -> dict[str, object]:
        assert symbol == "XAUUSD"
        return {
            "path": "Forex\\Metals",
            "digits": 2,
            "point": 0.01,
            "trade_tick_size": 0.01,
            "trade_contract_size": 100.0,
            "volume_min": 0.01,
            "volume_max": 200.0,
            "volume_step": 0.01,
        }

    def symbol_info_tick(self, symbol: str) -> dict[str, object]:
        assert symbol == "XAUUSD"
        now_msc = int(time.time() * 1000)
        return {
            "time": now_msc // 1000,
            "time_msc": now_msc,
            "bid": 4000.0,
            "ask": 4000.1,
        }

    def positions_get(self):
        return tuple(self.positions)

    def orders_get(self):
        return tuple(self.orders)

    def copy_rates_from_pos(self, symbol: str, timeframe: int, start_pos: int, count: int):
        assert symbol == "XAUUSD"
        assert start_pos == 1
        if self.fail_rates:
            return None
        seconds = {
            self.TIMEFRAME_M15: 15 * 60,
            self.TIMEFRAME_H1: 60 * 60,
            self.TIMEFRAME_H4: 4 * 60 * 60,
        }[timeframe]
        now = int(time.time())
        aligned = now - (now % seconds)
        latest_open = aligned - seconds
        oldest = latest_open - seconds * (count - 1)
        return [
            {
                "time": oldest + index * seconds,
                "open": 4000.0,
                "high": 4002.0,
                "low": 3998.0,
                "close": 4001.0,
                "tick_volume": 100,
            }
            for index in range(count)
        ]


def _adapter(fake: FakeMT5) -> MT5ReadOnlyAdapter:
    adapter = MT5ReadOnlyAdapter(fake)
    adapter.initialize()
    return adapter


def test_one_live_shadow_cycle_writes_durable_zero_action_evidence(tmp_path) -> None:
    fake = FakeMT5()
    adapter = _adapter(fake)

    assert run_shadow_host(tmp_path, once=True, adapter=adapter) == 0

    heartbeat = json.loads((tmp_path / "heartbeat.json").read_text(encoding="utf-8"))
    assert heartbeat["execution_enabled"] is False
    assert heartbeat["execution_capability"] == "ABSENT"
    assert heartbeat["broker_action_count"] == 0
    assert heartbeat["open_positions"] == 0
    assert heartbeat["pending_orders"] == 0
    assert heartbeat["runtime_state"] in {"QUARANTINED", "SHADOW", "DEGRADED"}

    connection = open_database(tmp_path / "state.sqlite3")
    try:
        report = verify_startup(connection)
        assert report.journal_entries >= 5
        rows = connection.execute(
            "SELECT event_type, payload_json FROM audit_journal ORDER BY sequence"
        ).fetchall()
        assert rows[0]["event_type"] == "STARTUP"
        assert any(row["event_type"] == "DECISION_RECORDED" for row in rows)
        assert all('"broker_action_count":0' in row["payload_json"] for row in rows)
    finally:
        connection.close()


def test_broker_preflight_refuses_preexisting_exposure() -> None:
    fake = FakeMT5()
    fake.positions = [
        {
            "ticket": 99,
            "symbol": "XAUUSD",
            "type": fake.POSITION_TYPE_BUY,
            "volume": 0.01,
        }
    ]
    adapter = _adapter(fake)

    with pytest.raises(HostSafetyError, match="requires zero broker positions"):
        broker_preflight(adapter)


def test_host_records_fault_and_exits_when_market_observation_fails(tmp_path) -> None:
    fake = FakeMT5()
    fake.fail_rates = True
    adapter = _adapter(fake)

    with pytest.raises(MT5ReadOnlyError, match="copy_rates_from_pos failed"):
        run_shadow_host(tmp_path, once=True, adapter=adapter)

    heartbeat = json.loads((tmp_path / "heartbeat.json").read_text(encoding="utf-8"))
    assert heartbeat["runtime_state"] == "QUARANTINED"
    assert heartbeat["execution_enabled"] is False
    assert heartbeat["broker_action_count"] == 0

    connection = open_database(tmp_path / "state.sqlite3")
    try:
        rows = connection.execute(
            "SELECT event_type FROM audit_journal ORDER BY sequence"
        ).fetchall()
        assert any(row["event_type"] == "FAULT_RECORDED" for row in rows)
    finally:
        connection.close()


def test_preflight_detects_guard_loss_after_initialization() -> None:
    fake = FakeMT5()
    adapter = _adapter(fake)
    fake.tradeapi_disabled = False

    with pytest.raises(MT5ReadOnlyError, match="external-Python trading protection"):
        broker_preflight(adapter)


def test_host_rejects_too_fast_polling(tmp_path) -> None:
    fake = FakeMT5()
    adapter = _adapter(fake)

    with pytest.raises(HostSafetyError, match="at least 5"):
        run_shadow_host(tmp_path, interval_seconds=1, once=True, adapter=adapter)
