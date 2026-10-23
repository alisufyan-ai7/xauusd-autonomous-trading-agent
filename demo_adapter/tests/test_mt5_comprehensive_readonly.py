"""Single comprehensive MT5 DEMO source collection: no trade API ever called."""
from __future__ import annotations

import hashlib
import importlib.util
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

import pytest

from xauusd_demo.envelope import DemoSafetyError

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mt5_comprehensive_readonly.py"
spec = importlib.util.spec_from_file_location("comprehensive_mt5", SCRIPT)
assert spec is not None and spec.loader is not None
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

NOW = datetime(2026, 10, 23, 11, 0, tzinfo=UTC)
FP = hashlib.sha256(
    b"Exness Technologies Ltd|Exness-MT5Trial15|321|USD"
).hexdigest()


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    SYMBOL_TRADE_MODE_FULL = 4
    COPY_TICKS_INFO = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_H1 = 60
    TIMEFRAME_H4 = 240
    TIMEFRAME_D1 = 1440
    TIMEFRAME_W1 = 10080

    def __init__(self) -> None:
        self.now = NOW
        self.account = {
            "trade_mode": 0, "company": "Exness Technologies Ltd",
            "server": "Exness-MT5Trial15", "currency": "USD",
            "login": 321, "balance": 10000, "equity": 10000,
            "margin": 0, "margin_free": 10000, "leverage": 2000,
        }
        self.terminal = {"connected": True, "tradeapi_disabled": True}
        self.info = {
            "trade_mode": 4, "trade_tick_size": 0.01,
            "trade_tick_value_loss": 1, "trade_tick_value_profit": 1,
            "trade_contract_size": 100, "point": 0.01,
            "volume_min": 0.01, "volume_max": 10, "volume_step": 0.01,
            "trade_stops_level": 10, "trade_freeze_level": 0,
            "swap_long": -2, "swap_short": -3, "swap_mode": 1,
            "digits": 2, "trade_exemode": 2, "trade_calc_mode": 0,
            "filling_mode": 2, "expiration_mode": 2, "order_mode": 15,
        }
        self.historical_deals = [{
            "type": 2, "profit": 10000, "commission": 0, "swap": 0, "fee": 0,
            "symbol": "",
        }]
        self.orders = []
        self.positions = []
        self.calls: list[str] = []

    def initialize(self):
        self.calls.append("initialize")
        return True

    def shutdown(self):
        self.calls.append("shutdown")

    def terminal_info(self):
        self.calls.append("terminal_info")
        return self.terminal

    def account_info(self):
        self.calls.append("account_info")
        return self.account

    def symbol_info(self, symbol):
        self.calls.append("symbol_info")
        assert symbol == "XAUUSD"
        return self.info

    def symbol_info_tick(self, symbol):
        self.calls.append("symbol_info_tick")
        assert symbol == "XAUUSD"
        return {
            "bid": 2699.8, "ask": 2700,
            "time_msc": int(self.now.timestamp() * 1000),
        }

    def positions_get(self):
        self.calls.append("positions_get")
        return self.positions

    def orders_get(self):
        self.calls.append("orders_get")
        return self.orders

    def history_deals_get(self, start, end):
        self.calls.append("history_deals_get")
        return self.historical_deals

    def history_orders_get(self, start, end):
        self.calls.append("history_orders_get")
        return []

    def copy_ticks_range(self, symbol, start, end, flags):
        self.calls.append("copy_ticks_range")
        assert symbol == "XAUUSD" and flags == 1
        return [
            {"time_msc": int((start + timedelta(seconds=1)).timestamp() * 1000),
             "bid": 2699.8, "ask": 2700},
            {"time_msc": int((end - timedelta(milliseconds=100)).timestamp() * 1000),
             "bid": 2699.7, "ask": 2700.05},
        ]

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        self.calls.append("copy_rates_from_pos")
        assert symbol == "XAUUSD" and start == 0
        return [
            {"time": int((NOW - timedelta(days=3)).timestamp()),
             "open": 2600.0, "close": 2700.0},
            {"time": int((NOW - timedelta(days=1)).timestamp()),
             "open": 2650.0, "close": 2700.0},
        ]

    def order_calc_profit(self, direction, symbol, lots, entry, stop):
        self.calls.append("order_calc_profit")
        assert symbol == "XAUUSD" and lots == 0.01
        return (-abs(entry - stop)) if direction in (0, 1) else None

    def order_calc_margin(self, direction, symbol, lots, entry):
        self.calls.append("order_calc_margin")
        assert lots == 0.01 and symbol == "XAUUSD"
        return 8.0

    def order_send(self, *args, **kwargs):
        raise AssertionError("comprehensive MT5 source must not send orders")

    def order_check(self, *args, **kwargs):
        raise AssertionError("comprehensive MT5 source must not check orders")

    def login(self, *args, **kwargs):
        raise AssertionError("comprehensive MT5 source must not switch login")


@pytest.fixture(autouse=True)
def test_identity(monkeypatch):
    monkeypatch.setattr(probe, "EXPECTED_ACCOUNT_SHA256", FP)
    monkeypatch.setattr(
        "xauusd_demo.broker_money_readonly.EXPECTED_ACCOUNT_SHA256", FP
    )


def surface(raw=None):
    return probe.MT5ReadOnlySurface(FakeMT5() if raw is None else raw)


def test_one_collect_reads_account_cash_seven_frames_history_and_broker_money():
    mt5 = FakeMT5()
    ticks: list[dict] = []
    report = probe.collect_static(surface(mt5), NOW, on_historical_tick=ticks.append)
    assert report["account_before"]["positions_count"] == 0
    assert report["account_before"]["tradeapi_disabled"] is True
    assert len(report["seven_frame_coverage"]) == 7
    assert len(report["broker_money_0_01"]) == 6
    assert report["historical_cash_and_fee_evidence"]["all_broker_deal_count"] == 1
    assert report["past_four_hour_tick_context"]["tick_count"] == 2
    assert report["past_four_hour_tick_context"]["max_intertick_gap_ms"] > 1000
    assert len(ticks) == 2
    assert not report["v11_cost_calibration_admitted"]
    assert not report["policy_a_execution_admitted"]
    assert "order_send" not in mt5.calls
    assert "order_check" not in mt5.calls


def test_surface_is_closed_to_trading_and_login_methods():
    broker = FakeMT5()
    reader = surface(broker)
    for forbidden in probe.FORBIDDEN_METHODS:
        with pytest.raises(DemoSafetyError):
            getattr(reader, forbidden)
    assert not broker.calls


@pytest.mark.parametrize("changed", ["live", "login", "wrong_server", "disabled_toggle", "position", "pending"])
def test_identity_failures_never_read_as_broker_release(changed):
    broker = FakeMT5()
    if changed == "live":
        broker.account["trade_mode"] = 2
    elif changed == "login":
        broker.account["login"] = 555
    elif changed == "wrong_server":
        broker.account["server"] = "LIVE"
    elif changed == "disabled_toggle":
        broker.terminal["tradeapi_disabled"] = False
    elif changed == "position":
        broker.positions = [{"ticket": 1}]
    else:
        broker.orders = [{"ticket": 2}]
    with pytest.raises(DemoSafetyError):
        probe.collect_static(surface(broker), NOW)
    assert "order_send" not in broker.calls


@pytest.mark.parametrize("changed", ["stale", "crossed_quote", "bad_volume", "missing_history", "missing_bars", "bad_margin"])
def test_real_broker_source_gaps_fail_closed(changed):
    broker = FakeMT5()
    if changed == "stale":
        broker.now -= timedelta(seconds=25)
    elif changed == "crossed_quote":
        broker.symbol_info_tick = lambda _symbol: {
            "bid": 2701, "ask": 2700,
            "time_msc": int(NOW.timestamp() * 1000),
        }
    elif changed == "bad_volume":
        broker.info["volume_min"] = 0.1
    elif changed == "missing_history":
        broker.history_deals_get = lambda *_args: None
    elif changed == "missing_bars":
        broker.copy_rates_from_pos = lambda *_args: []
    else:
        broker.order_calc_margin = lambda *_args: 0
    with pytest.raises(DemoSafetyError):
        probe.collect_static(surface(broker), NOW)
    assert "order_send" not in broker.calls


def test_quote_prospective_window_single_invocation_with_source_verification():
    broker = FakeMT5()
    start = NOW
    current = [start]

    def now_fn():
        broker.now = current[0]
        return current[0]

    def sleep_fn(seconds):
        current[0] += timedelta(seconds=seconds)

    observed: list[dict] = []
    ticks: list[dict] = []
    result = probe.collect_prospective_quotes(
        surface(broker), start=start, now_fn=now_fn, sleep_fn=sleep_fn,
        duration_seconds=10, sample_seconds=5,
        on_sample=observed.append, on_tick=ticks.append,
    )
    assert result["prospective_observation_complete"] is True
    assert result["observed_slots"] == 2
    assert len(observed) == 2 and len(ticks) == 2
    assert result["calibration_admitted"] is False
    assert "order_send" not in broker.calls


def test_prospective_window_rejects_missing_slot_and_never_infers_data():
    broker = FakeMT5()
    calls = [0]

    def now_fn():
        calls[0] += 1
        # Exact start first, then 1s late for the first sample's slot
        return NOW if calls[0] == 1 else NOW + timedelta(seconds=7)

    with pytest.raises(DemoSafetyError, match="slot missed"):
        probe.collect_prospective_quotes(
            surface(broker), start=NOW, now_fn=now_fn,
            sleep_fn=lambda _: None, duration_seconds=10, sample_seconds=5,
        )


def test_no_owner_consent_never_initializes_real_terminal(tmp_path, monkeypatch, capsys):
    def no_import(_name):
        raise AssertionError("not permitted to import real MetaTrader5")
    monkeypatch.setattr(probe.importlib, "import_module", no_import)
    assert probe.run(["--output", str(tmp_path / "capture")]) == 2
    assert "CONFIRMATION_REQUIRED" in capsys.readouterr().out


def test_privacy_shareable_summary_has_no_broker_login_or_trade_identifiers():
    mt5 = FakeMT5()
    report = probe.collect_static(surface(mt5), NOW)
    report["status"] = "STATIC_COMPLETE_PROSPECTIVE_NOT_COLLECTED"
    summary = probe._public_summary(report)
    encoded = str(summary)
    assert "login" not in encoded.lower()
    assert "ticket" not in encoded.lower()
    assert summary["full_policy_a_admitted"] is False
    assert summary["order_send_calls"] == 0
    assert summary["four_hour_quote_slots"] is None
