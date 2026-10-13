from __future__ import annotations

import time
from datetime import UTC, datetime

import pytest

from xauusd_agent.broker.mt5_readonly import MT5ReadOnlyAdapter, MT5ReadOnlyError
from xauusd_agent.market import Timeframe


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
        self.connected = True
        self.tradeapi_disabled = True
        self.initialized = False
        self.shutdown_called = False
        self.positions: list[dict[str, object]] = []
        self.orders: list[dict[str, object]] = []
        self.fail_rates = False

    def initialize(self) -> bool:
        self.initialized = True
        return True

    def shutdown(self) -> None:
        self.shutdown_called = True

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
            "bid": 4000.00,
            "ask": 4000.10,
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


def test_adapter_preflight_and_market_reads_are_observation_only() -> None:
    fake = FakeMT5()
    adapter = MT5ReadOnlyAdapter(fake)
    adapter.initialize()

    preflight = adapter.preflight()
    assert preflight["connected"] is True
    assert preflight["trading_api_disabled"] is True
    assert preflight["open_positions"] == 0
    assert preflight["pending_orders"] == 0
    assert preflight["execution_enabled"] is False
    assert preflight["broker_action_count"] == 0

    account = adapter.observe_account()
    assert account.fingerprint.server == "Exness-MT5Trial15"
    assert len(account.fingerprint.account_id_sha256) == 64

    symbol = adapter.observe_symbol_fingerprint("XAUUSD")
    assert str(symbol.point) == "0.01"
    build = adapter.observe_build_fingerprint()
    assert build.python_bridge_version == "5.0.6090"

    now = datetime.now(UTC)
    quote = adapter.read_latest_quote(symbol="XAUUSD", as_of=now)
    assert quote is not None
    assert quote.symbol == "XAUUSD"
    assert quote.ask > quote.bid

    bars = adapter.read_completed_bars(
        symbol="XAUUSD",
        timeframe=Timeframe.M15,
        as_of=now,
        limit=3,
    )
    assert len(bars) == 3
    assert bars == tuple(sorted(bars, key=lambda item: item.open_time))
    assert all(bar.is_completed_at(now) for bar in bars)

    adapter.close()
    assert fake.shutdown_called is True


def test_adapter_maps_observed_positions_and_orders_without_mutation() -> None:
    fake = FakeMT5()
    fake.positions = [
        {"ticket": 1, "symbol": "XAUUSD", "type": fake.POSITION_TYPE_BUY, "volume": 0.01},
        {"ticket": 2, "symbol": "XAUUSD", "type": fake.POSITION_TYPE_SELL, "volume": 0.02},
    ]
    fake.orders = [
        {
            "ticket": 3,
            "symbol": "XAUUSD",
            "type": fake.ORDER_TYPE_BUY_LIMIT,
            "volume_current": 0.01,
            "volume_initial": 0.01,
            "state": 1,
        },
        {
            "ticket": 4,
            "symbol": "XAUUSD",
            "type": fake.ORDER_TYPE_SELL_STOP,
            "volume_current": 0.0,
            "volume_initial": 0.02,
            "state": 1,
        },
    ]
    adapter = MT5ReadOnlyAdapter(fake)
    adapter.initialize()

    positions = adapter.observe_positions()
    orders = adapter.observe_orders()

    assert [item.side for item in positions] == ["BUY", "SELL"]
    assert [item.side for item in orders] == ["BUY", "SELL"]
    assert str(orders[1].volume_lots) == "0.02"
    assert adapter.preflight()["open_positions"] == 2
    assert adapter.preflight()["pending_orders"] == 2


def test_adapter_fails_closed_when_external_python_guard_is_off() -> None:
    fake = FakeMT5()
    fake.tradeapi_disabled = False
    adapter = MT5ReadOnlyAdapter(fake)

    with pytest.raises(MT5ReadOnlyError, match="external-Python trading protection"):
        adapter.initialize()
    assert fake.shutdown_called is True


def test_adapter_rechecks_guard_after_initialization() -> None:
    fake = FakeMT5()
    adapter = MT5ReadOnlyAdapter(fake)
    adapter.initialize()
    fake.tradeapi_disabled = False

    with pytest.raises(MT5ReadOnlyError, match="external-Python trading protection"):
        adapter.observe_account()


def test_adapter_refuses_wrong_symbol_and_failed_rates() -> None:
    fake = FakeMT5()
    adapter = MT5ReadOnlyAdapter(fake)
    adapter.initialize()

    with pytest.raises(MT5ReadOnlyError, match="bound to XAUUSD"):
        adapter.observe_symbol_fingerprint("EURUSD")
    fake.fail_rates = True
    with pytest.raises(MT5ReadOnlyError, match="copy_rates_from_pos failed"):
        adapter.read_completed_bars(
            symbol="XAUUSD",
            timeframe=Timeframe.H1,
            as_of=datetime.now(UTC),
            limit=2,
        )
