# ruff: noqa: I001
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from xauusd_demo.continuous_coordinator import PendingBrokerAck
from xauusd_demo.envelope import DemoSafetyError
from xauusd_demo.pending_mt5_reconciliation import ReadOnlyPendingMT5Port

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)
FP = hashlib.sha256(
    "Exness Technologies Ltd|Exness-MT5Trial15|321|USD".encode()
).hexdigest()


def receipt():
    return PendingBrokerAck(
        setup_key="a" * 64, account_fingerprint=FP, order_ticket=501,
        side="BUY", volume_lots=D("0.01"),
        entry_stop=D("2701"), stop_loss=D("2695"),
        take_profit=D("2720"), expires_utc=NOW + timedelta(minutes=40),
    )


class FakeMT5:
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_STATE_PLACED = 1
    ORDER_STATE_FILLED = 4
    ORDER_STATE_CANCELED = 2
    ORDER_STATE_EXPIRED = 3
    DEAL_TYPE_BUY = 0
    DEAL_TYPE_SELL = 1
    DEAL_ENTRY_IN = 0
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1

    def __init__(self):
        self.account = {
            "company": "Exness Technologies Ltd",
            "server": "Exness-MT5Trial15", "currency": "USD",
            "login": 321, "trade_mode": 0,
        }
        self.terminal = {"connected": True}
        self.pending = {
            "ticket": 501, "symbol": "XAUUSD",
            "magic": 260101, "type": 4, "volume_initial": 0.01,
            "price_open": 2701.0, "sl": 2695.0, "tp": 2720.0,
            "time_expiration": int(receipt().expires_utc.timestamp()),
            "state": 1,
        }
        self.current_orders = [self.pending]
        self.current_positions = []
        self.historic_orders = []
        self.deals = []
        self.calls = []

    def terminal_info(self):
        self.calls.append("terminal_info")
        return self.terminal

    def account_info(self):
        self.calls.append("account_info")
        return self.account

    def orders_get(self):
        self.calls.append("orders_get")
        return self.current_orders

    def positions_get(self):
        self.calls.append("positions_get")
        return self.current_positions

    def history_orders_get(self, *, ticket):
        self.calls.append("history_orders_get")
        assert ticket == 501
        return self.historic_orders

    def history_deals_get(self, *, ticket):
        self.calls.append("history_deals_get")
        assert ticket == 501
        return self.deals

    def symbol_info(self, symbol):
        self.calls.append("symbol_info")
        assert symbol == "XAUUSD"
        return {"trade_tick_size": 0.01}

    def make_history(self, state):
        self.current_orders = []
        self.historic_orders = [self.pending | {"state": state}]

    def make_fill(self):
        self.make_history(self.ORDER_STATE_FILLED)
        self.deals = [{
            "ticket": 1001, "order": 501, "position_id": 700,
            "symbol": "XAUUSD", "entry": 0, "magic": 260101,
            "type": 0, "volume": 0.01, "price": 2701.0,
        }]
        self.current_positions = [{
            "identifier": 700, "ticket": 701,
            "symbol": "XAUUSD", "magic": 260101, "type": 0,
            "volume": 0.01, "sl": 2695.0, "tp": 2720.0,
        }]


def observe(mt5):
    return ReadOnlyPendingMT5Port(mt5).known_pending_state(receipt(), NOW)


def test_real_mt5_pending_order_is_not_equated_with_position_or_fill():
    mt5 = FakeMT5()
    result = observe(mt5)
    assert result.state == "PENDING" and result.fill is None
    assert "history_orders_get" not in mt5.calls
    assert "order_check" not in mt5.calls and "order_send" not in mt5.calls


def test_real_mt5_matched_filled_order_deal_and_position():
    mt5 = FakeMT5()
    mt5.make_fill()
    result = observe(mt5)
    assert result.state == "FILLED"
    assert result.fill is not None
    assert result.fill.position_id == 700
    assert result.fill.order_ticket == 501
    assert result.fill.entry_deal_ticket == 1001


@pytest.mark.parametrize("order_state", [FakeMT5.ORDER_STATE_EXPIRED, FakeMT5.ORDER_STATE_CANCELED])
def test_expired_or_canceled_order_needs_flat_account_and_no_deals(order_state):
    mt5 = FakeMT5()
    mt5.make_history(order_state)
    assert observe(mt5).state == "EXPIRED"
    mt5.deals = [{"ticket": 1001}]
    assert observe(mt5).state == "UNKNOWN"


@pytest.mark.parametrize("scenario", [
    "other_order", "foreign_position", "missing_broker_order_history",
    "partial_fill", "wrong_position", "missing_sl", "moved_tp",
    "wrong_deal_magic", "wrong_deal_order", "missing_deal",
    "closed_before_poll", "wrong_direction", "missing_tick",
    "stale_pending_after_expiry", "changed_pending_volume",
])
def test_unreconciled_pending_order_is_never_automatically_closed(scenario):
    mt5 = FakeMT5()
    if scenario == "other_order":
        mt5.current_orders.append({"ticket": 999})
    elif scenario == "foreign_position":
        mt5.current_positions = [{"ticket": 20}]
    elif scenario == "stale_pending_after_expiry":
        outcome = ReadOnlyPendingMT5Port(mt5).known_pending_state(
            receipt(), NOW + timedelta(hours=1)
        )
        assert outcome.state == "UNKNOWN"
        return
    elif scenario == "changed_pending_volume":
        mt5.pending["volume_initial"] = 0.02
    else:
        mt5.make_fill()
        if scenario == "missing_broker_order_history":
            mt5.historic_orders = None
        elif scenario == "partial_fill":
            mt5.deals[0]["volume"] = 0.005
        elif scenario == "wrong_position":
            mt5.current_positions[0]["identifier"] = 600
        elif scenario == "missing_sl":
            mt5.current_positions[0]["sl"] = 0
        elif scenario == "moved_tp":
            mt5.current_positions[0]["tp"] = 2740
        elif scenario == "wrong_deal_magic":
            mt5.deals[0]["magic"] = 42
        elif scenario == "wrong_deal_order":
            mt5.deals[0]["order"] = 98
        elif scenario == "missing_deal":
            mt5.deals = []
        elif scenario == "closed_before_poll":
            mt5.current_positions = []
        else:
            mt5.deals[0]["type"] = 1
    assert observe(mt5).state == "UNKNOWN"


@pytest.mark.parametrize("change", ["live", "wrong_server", "wrong_login"])
def test_wrong_or_live_mt5_account_cannot_monitor_pending(change):
    mt5 = FakeMT5()
    if change == "live":
        mt5.account["trade_mode"] = 2
    elif change == "wrong_server":
        mt5.account["server"] = "Other"
    else:
        mt5.account["login"] = 123
    with pytest.raises(DemoSafetyError):
        observe(mt5)
