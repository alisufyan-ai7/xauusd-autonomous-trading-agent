# ruff: noqa: I001
"""No-order source tests; seven genuine-shape MT5 closed bars on fake terminal."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from xauusd_agent.features.v2_market_context import ContextTimeframe
from xauusd_demo.envelope import DemoSafetyError
from xauusd_demo.mt5_sevenframe_source import ReadOnlyMT5SevenFrameSource

NOW = datetime(2026, 10, 22, 12, 16, tzinfo=UTC)
DUR = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600,
       "H4": 14400, "D1": 86400, "W1": 604800}


class FakeTerminal:
    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_H1 = 60
    TIMEFRAME_H4 = 240
    TIMEFRAME_D1 = 1440
    TIMEFRAME_W1 = 10080

    def __init__(self):
        self.calls = []
        self.connected = True
        self.trade_mode = 0
        self.duplicate = False
        self.incomplete = False
        self.wrong_quote = False

    def account_info(self):
        return {
            "trade_mode": self.trade_mode, "company": "Exness Technologies Ltd",
            "server": "Exness-MT5Trial15", "currency": "USD",
        }

    def terminal_info(self):
        return {"connected": self.connected}

    def symbol_info(self, symbol):
        assert symbol == "XAUUSD"
        return {"trade_tick_size": 0.01}

    def symbol_info_tick(self, symbol):
        assert symbol == "XAUUSD"
        return {
            "bid": 4000.10,
            "ask": 4000.20 if not self.wrong_quote else 3999.90,
            "time_msc": int((NOW-timedelta(milliseconds=200)).timestamp()*1000),
        }

    def copy_rates_from_pos(self, symbol, code, start, count):
        assert symbol == "XAUUSD" and start == 1
        self.calls.append((code, start, count))
        name = {1:"M1", 5:"M5", 15:"M15", 60:"H1",
                240:"H4", 1440:"D1", 10080:"W1"}[code]
        sec = DUR[name]
        # Last completed open, never the forming zero-index bar.
        newest = (int(NOW.timestamp()) // sec)*sec-sec
        result = [{
            "time": newest-i*sec,
            "open": 4000, "high": 4001, "low": 3999,
            "close": 4000, "tick_volume": 100,
        } for i in range(count)]
        if name == "M15" and self.duplicate:
            result[0]["time"] = result[1]["time"]
        if name == "M15" and self.incomplete:
            result[0]["time"] = int(NOW.timestamp()) // sec * sec
        return result

    def order_check(self, *_):
        raise AssertionError("source must not check orders")

    def order_send(self, *_):
        raise AssertionError("source must not send orders")


def test_all_seven_frames_exclude_forming_and_source_calls_are_read_only():
    mt5 = FakeTerminal()
    obs = ReadOnlyMT5SevenFrameSource(mt5).capture(now=NOW)
    assert len(obs.bars) == 7
    assert len(mt5.calls) == 7
    assert obs.broker_spread == obs.quote.spread
    assert obs.bars[ContextTimeframe.M15][-1].close_time <= NOW
    for name, rows in obs.bars.items():
        assert rows and all(x.timeframe is name for x in rows)
        assert all(a.open_time < b.open_time for a, b in zip(rows, rows[1:], strict=False))
        assert rows[-1].close_time <= NOW


@pytest.mark.parametrize(("field", "value"), [
    ("connected", False), ("trade_mode", 2),
    ("duplicate", True), ("incomplete", True), ("wrong_quote", True),
])
def test_bad_account_ticks_and_bar_times_do_not_validate(field, value):
    mt5 = FakeTerminal()
    setattr(mt5, field, value)
    with pytest.raises(DemoSafetyError):
        ReadOnlyMT5SevenFrameSource(mt5).capture(now=NOW)


def test_missing_completed_rate_is_a_rejection_not_a_shortened_warmup():
    class Short(FakeTerminal):
        def copy_rates_from_pos(self, symbol, code, start, count):
            return super().copy_rates_from_pos(symbol, code, start, count-1)

    with pytest.raises(DemoSafetyError, match="historic closed bars short"):
        ReadOnlyMT5SevenFrameSource(Short()).capture(now=NOW)
