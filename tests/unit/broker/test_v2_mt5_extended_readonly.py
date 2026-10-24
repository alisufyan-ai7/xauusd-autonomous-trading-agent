"""Entirely synthetic MT5 fake. No real account numbers or broker orders."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from xauusd_agent.broker.mt5_readonly import MT5ReadOnlyError
from xauusd_agent.broker.v2_mt5_context_readonly import MT5ExtendedReadOnlyAdapter
from xauusd_agent.features.v2_market_context import ContextTimeframe

NOW = datetime(2026, 10, 22, 12, tzinfo=UTC)
BROKER = "Exness Technologies Ltd"
SERVER = "Exness-MT5Trial15"
LOGIN = "SYNTHETIC_NOT_A_REAL_LOGIN"
EXPECTED = hashlib.sha256(f"{BROKER}|{SERVER}|{LOGIN}|USD".encode()).hexdigest()


class SyntheticMT5:
    TIMEFRAME_W1 = 10080
    TIMEFRAME_D1 = 1440
    TIMEFRAME_H4 = 240
    TIMEFRAME_H1 = 60
    TIMEFRAME_M15 = 15
    TIMEFRAME_M5 = 5
    TIMEFRAME_M1 = 1

    def __init__(self) -> None:
        self.connected = True
        self.disabled = True
        self.login = LOGIN
        self.mode = 0
        self.future = False
        self.calls: list[tuple[str, int, int, int]] = []

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass

    def terminal_info(self):
        return {"connected": self.connected, "tradeapi_disabled": self.disabled}

    def account_info(self):
        return {
            "login": self.login, "company": BROKER, "server": SERVER,
            "currency": "USD", "trade_mode": self.mode,
            "equity": 10000, "margin": 0, "margin_free": 10000,
            "leverage": 100,
        }

    def last_error(self):
        return (0, "synthetic")

    def copy_rates_from_pos(self, symbol: str, tf: int, pos: int, n: int):
        self.calls.append((symbol, tf, pos, n))
        assert symbol == "XAUUSD" and pos == 1
        seconds = tf * 60
        if tf == self.TIMEFRAME_W1:
            # Weekly broker bars open on Mondays at 00:00 UTC.
            offset = (NOW.weekday() * 86400 + NOW.hour * 3600)
            current_open = NOW - timedelta(seconds=offset)
        else:
            current_open = NOW - timedelta(seconds=int(NOW.timestamp()) % seconds)
        last_start = current_open - timedelta(seconds=seconds)
        if self.future:
            last_start = current_open
        return [
            {
                "time": int((last_start - timedelta(seconds=seconds * idx)).timestamp()),
                "open": 3000.0, "high": 3002.0,
                "low": 2998.0, "close": 3001.0, "tick_volume": 100,
            }
            for idx in reversed(range(n))
        ]


def adapter(fake: SyntheticMT5) -> MT5ExtendedReadOnlyAdapter:
    return MT5ExtendedReadOnlyAdapter(
        module=fake, admitted_fingerprint_sha256=EXPECTED,
        admitted_server=SERVER, admitted_company=BROKER,
    )


def test_seven_real_timeframe_lookups_are_read_only_and_complete() -> None:
    fake = SyntheticMT5()
    a = adapter(fake)
    a.initialize()
    result = a.read_seven_frames(
        as_of=NOW, limits={frame: 3 for frame in ContextTimeframe}
    )
    assert set(result) == set(ContextTimeframe)
    assert all(len(bars) == 3 for bars in result.values())
    assert all(bar.close_time <= NOW for bars in result.values() for bar in bars)
    assert len(fake.calls) == 7
    assert all(position == 1 for _, _, position, _ in fake.calls)


def test_demo_fingerprint_and_trade_mode_never_default() -> None:
    fake = SyntheticMT5()
    a = adapter(fake)
    a.initialize()
    fake.login = "DIFFERENT_FAKE_ACCOUNT"
    with pytest.raises(MT5ReadOnlyError, match="identity mismatch"):
        a.read_context_bars(timeframe=ContextTimeframe.M1, as_of=NOW, limit=2)
    fake.login = LOGIN
    fake.mode = 2
    with pytest.raises(MT5ReadOnlyError, match="identity mismatch"):
        a.read_context_bars(timeframe=ContextTimeframe.W1, as_of=NOW, limit=2)


def test_read_only_api_guard_blocks_trade_setting_change() -> None:
    fake = SyntheticMT5()
    a = adapter(fake)
    a.initialize()
    fake.disabled = False
    with pytest.raises(MT5ReadOnlyError, match="external-Python"):
        a.read_context_bars(timeframe=ContextTimeframe.D1, as_of=NOW, limit=2)


def test_incomplete_or_future_bar_fails_closed() -> None:
    fake = SyntheticMT5()
    fake.future = True
    a = adapter(fake)
    a.initialize()
    with pytest.raises(MT5ReadOnlyError, match="incomplete or future"):
        a.read_context_bars(timeframe=ContextTimeframe.M5, as_of=NOW, limit=2)


def test_missing_timeframe_and_invalid_limits_reject() -> None:
    fake = SyntheticMT5()
    fake.TIMEFRAME_W1 = None
    a = adapter(fake)
    a.initialize()
    with pytest.raises(MT5ReadOnlyError, match="unsupported"):
        a.read_context_bars(timeframe=ContextTimeframe.W1, as_of=NOW, limit=2)
    with pytest.raises(MT5ReadOnlyError, match="limit"):
        a.read_context_bars(timeframe=ContextTimeframe.H1, as_of=NOW, limit=20001)
    with pytest.raises(MT5ReadOnlyError, match="seven"):
        a.read_seven_frames(as_of=NOW, limits={ContextTimeframe.M1: 2})
