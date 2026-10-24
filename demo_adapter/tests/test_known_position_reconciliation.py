# ruff: noqa: I001
from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from xauusd_demo.continuous_coordinator import QualifiedBrokerAck
from xauusd_demo.envelope import DemoSafetyError
from xauusd_demo.known_position_reconciliation import (
    KnownMT5PositionPort,
    KnownPositionBinding,
    observe_known_mt5_position,
)

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)
COMPANY = "Exness Technologies Ltd"
SERVER = "Exness-MT5Trial15"
FP = hashlib.sha256(f"{COMPANY}|{SERVER}|321|USD".encode()).hexdigest()


def binding() -> KnownPositionBinding:
    return KnownPositionBinding(
        position_id=700, entry_order=101, entry_deal=201,
        account_fingerprint=FP, side="BUY", volume=D("0.01"),
        protective_sl=D("2700.0"), protective_tp=D("2720.0"),
        tick_size=D("0.01"),
    )


class FakeMT5:
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1
    DEAL_TYPE_BUY = 0
    DEAL_TYPE_SELL = 1

    def __init__(self):
        self.account = {
            "company": COMPANY, "server": SERVER, "login": 321,
            "currency": "USD", "trade_mode": 0,
        }
        self.terminal = {"connected": True, "tradeapi_disabled": False}
        self.open_position = {
            "identifier": 700, "ticket": 777, "magic": 260101,
            "symbol": "XAUUSD", "volume": 0.01, "type": 0,
            "sl": 2700.0, "tp": 2720.0,
        }
        self.orders = []
        self.deals = [{
            "ticket": 201, "order": 101, "position_id": 700,
            "symbol": "XAUUSD", "magic": 260101, "type": 0,
            "entry": 0, "volume": 0.01,
            "time_msc": int((NOW - timedelta(seconds=4)).timestamp() * 1000),
        }]
        self.calls = []

    def terminal_info(self):
        self.calls.append("terminal_info")
        return self.terminal

    def account_info(self):
        self.calls.append("account_info")
        return self.account

    def positions_get(self):
        self.calls.append("positions_get")
        return [] if self.open_position is None else [self.open_position]

    def orders_get(self):
        self.calls.append("orders_get")
        return self.orders

    def history_deals_get(self, *, position):
        self.calls.append("history_deals_get")
        assert position == 700
        return self.deals


def exit_deal(*, volume=0.01, magic=0):
    return {
        "ticket": 202, "order": 102, "position_id": 700,
        "symbol": "XAUUSD", "magic": magic, "type": 1,
        "entry": 1, "volume": volume,
        "time_msc": int((NOW - timedelta(seconds=1)).timestamp() * 1000),
    }


def observe(port, bound=None):
    return observe_known_mt5_position(
        port, binding=binding() if bound is None else bound, now=NOW
    )


def test_known_open_position_requires_exact_position_identifier_not_order_ticket():
    port = FakeMT5()
    assert port.open_position["ticket"] != binding().position_id
    assert observe(port) == "OPEN"
    assert "order_send" not in port.calls
    assert "order_check" not in port.calls


def test_closed_requires_exact_entry_plus_exit_position_history():
    port = FakeMT5()
    port.open_position = None
    assert observe(port) == "UNKNOWN"
    port.deals.append(exit_deal())
    assert observe(port) == "CLOSED"


@pytest.mark.parametrize("change", [
    ("identifier", 101), ("magic", 0), ("symbol", "EURUSD"),
    ("sl", 0), ("tp", 0), ("sl", 2690), ("volume", 0.02),
    ("type", 1),
])
def test_unknown_position_identity_and_protection_quarantines(change):
    port = FakeMT5()
    field, value = change
    port.open_position[field] = value
    assert observe(port) == "UNKNOWN"


@pytest.mark.parametrize("change", [
    ("ticket", 999), ("order", 999), ("magic", 0), ("position_id", 999),
    ("volume", 0.02), ("symbol", "EURUSD"),
])
def test_unmatched_entry_deal_never_counts_as_known(change):
    port = FakeMT5()
    field, value = change
    port.deals[0][field] = value
    assert observe(port) == "UNKNOWN"


def test_partial_close_verified_as_open_only_with_correct_remaining_volume():
    port = FakeMT5()
    port.deals.append(exit_deal(volume=0.004))
    port.open_position["volume"] = 0.006
    assert observe(port) == "OPEN"
    port.open_position = None
    assert observe(port) == "UNKNOWN"


@pytest.mark.parametrize("failure", [
    "pending", "foreign", "missing_history", "duplicate", "future",
    "reversing", "wrong_exit_magic", "overclose",
])
def test_ambiguous_exposure_and_history_never_closed(failure):
    port = FakeMT5()
    port.open_position = None
    port.deals.append(exit_deal())
    if failure == "pending":
        port.orders = [{"ticket": 123}]
    elif failure == "foreign":
        port.open_position = {
            "identifier": 88, "symbol": "XAUUSD", "magic": 99
        }
    elif failure == "missing_history":
        port.deals = None
    elif failure == "duplicate":
        port.deals.append(dict(port.deals[-1]))
    elif failure == "future":
        port.deals[-1]["time_msc"] = int(
            (NOW + timedelta(minutes=1)).timestamp() * 1000
        )
    elif failure == "reversing":
        port.deals[-1]["entry"] = 2
    elif failure == "wrong_exit_magic":
        port.deals[-1]["magic"] = 777
    else:
        port.deals[-1]["volume"] = 0.02
    assert observe(port) == "UNKNOWN"


@pytest.mark.parametrize("change", [
    ("trade_mode", 2), ("server", "Wrong"), ("login", 222),
    ("currency", "EUR"),
])
def test_live_wrong_account_and_identity_never_reconcile(change):
    port = FakeMT5()
    field, value = change
    port.account[field] = value
    with pytest.raises(DemoSafetyError):
        observe(port)


def test_disconnected_broker_and_naive_clock_not_admitted():
    port = FakeMT5()
    port.terminal["connected"] = False
    assert observe(port) == "UNKNOWN"
    with pytest.raises(DemoSafetyError, match="UTC"):
        observe_known_mt5_position(
            port, binding=binding(), now=NOW.replace(tzinfo=None)
        )


@pytest.mark.parametrize("change", [
    {"volume": D("0.02")}, {"entry_deal": 0},
    {"protective_tp": D("0")}, {"side": "LIVE"},
    {"account_fingerprint": "guess"},
])
def test_binding_rejects_unqualified_ack_metadata(change):
    with pytest.raises(DemoSafetyError):
        replace(binding(), **change)


def test_read_port_accepts_exact_persisted_position_identifier_only():
    port = FakeMT5()
    observer = KnownMT5PositionPort(port, binding=binding())
    receipt = QualifiedBrokerAck(
        setup_key="a" * 64, account_fingerprint=FP,
        position_id=700, order_ticket=101, entry_deal_ticket=201,
        side="BUY", volume_lots=D("0.01"), entry_price=D("2710"),
        stop_loss=D("2700"), take_profit=D("2720"), tick_size=D("0.01"),
    )
    assert observer.known_position_state(
        replace(receipt, order_ticket=999), NOW
    ) == "UNKNOWN"
    assert observer.known_position_state(receipt, NOW) == "OPEN"
    port.open_position = None
    port.deals.append(exit_deal())
    assert observer.known_position_state(receipt, NOW) == "CLOSED"
    assert not hasattr(observer, "submit_qualified")
    assert not hasattr(observer, "order_send")
