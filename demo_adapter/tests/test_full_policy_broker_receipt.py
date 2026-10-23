# ruff: noqa: I001
from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest
from xauusd_agent.risk.full_policy_a import FullRiskDisposition

from xauusd_demo.envelope import DemoSafetyError
from xauusd_demo.full_policy_broker_receipt import (
    BoundAdverseCost, BrokerStopProposal, preview_broker_full_policy_a,
)
from xauusd_demo.prospective_cash_journal import CashObservation, CashRiskBaseline

NOW = datetime(2026, 10, 23, 12, 0, 0, tzinfo=UTC)
COMPANY = "Exness Technologies Ltd"
SERVER = "Exness-MT5Trial15"
FP = hashlib.sha256(f"{COMPANY}|{SERVER}|321|USD".encode()).hexdigest()


class FakeSource:
    SYMBOL_TRADE_MODE_FULL = 4
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1

    def __init__(self):
        self.calls = []
        self.account = {
            "trade_mode": 0, "company": COMPANY, "server": SERVER,
            "currency": "USD", "login": 321, "balance": 10000,
            "equity": 10000, "margin": 0, "margin_free": 10000,
        }
        self.term = {"connected": True}
        self.tick = {
            "time_msc": int(NOW.timestamp() * 1000),
            "bid": 2699.8, "ask": 2700.0,
        }
        self.info = {
            "trade_mode": 4, "trade_tick_size": 0.01,
            "trade_tick_value_loss": 1.0, "volume_min": 0.01,
            "volume_step": 0.01, "point": 0.01, "trade_stops_level": 10,
        }
        self.positions = []
        self.orders = []
        self.loss_value = -5.0
        self.margin_value = 8.0

    def terminal_info(self):
        self.calls.append("terminal_info")
        return self.term

    def account_info(self):
        self.calls.append("account_info")
        return self.account

    def positions_get(self):
        self.calls.append("positions_get")
        return self.positions

    def orders_get(self):
        self.calls.append("orders_get")
        return self.orders

    def symbol_info_tick(self, symbol):
        self.calls.append("symbol_info_tick")
        assert symbol == "XAUUSD"
        return self.tick

    def symbol_info(self, symbol):
        self.calls.append("symbol_info")
        assert symbol == "XAUUSD"
        return self.info

    def order_calc_profit(self, order_type, symbol, volume, entry, stop):
        self.calls.append("order_calc_profit")
        assert order_type in (0, 1)
        assert volume == 0.01
        return self.loss_value

    def order_calc_margin(self, order_type, symbol, volume, entry):
        self.calls.append("order_calc_margin")
        return self.margin_value


def baseline():
    return CashRiskBaseline(
        admitted=True, reason="SYNTHETIC_TEST",
        initial_equity=D("10000"), day_start_equity=D("10000"),
        week_start_equity=D("10000"), normalized_high_water=D("10000"),
        observed_day_loss=D(0), observed_week_loss=D(0),
        observed_drawdown=D(0), loss_equivalent_streak=D(0),
    )


def cash():
    return CashObservation(
        observed_utc=NOW, balance=D("10000"), equity=D("10000"),
        account_currency="USD", account_fingerprint=FP,
        broker_history_complete=True, positions_count=0,
        orders_count=0, broker_deals=(),
    )


def costs():
    return BoundAdverseCost(
        calibration_id="SYNTHETIC-UNADMITTED",
        evidence_sha256="a" * 64,
        commission_roundtrip_usd=D("0.50"),
        swap_reserve_usd=D("0.50"),
        slippage_reserve_usd=D("1.00"),
        gap_reserve_usd=D("1.00"),
    )


def candidate():
    return BrokerStopProposal(
        side="BUY", entry=D("2701.00"),
        stop=D("2696.00"), take_profit=D("2713.00"),
    )


def run(mt5, monkeypatch, *, observed=None, base=None, proposal=None,
        cost=None, expected=None, guard=True, session=True):
    monkeypatch.setattr(
        "xauusd_demo.full_policy_broker_receipt.EXPECTED_ACCOUNT_SHA256",
        FP,
    )
    c = costs() if cost is None else cost
    return preview_broker_full_policy_a(
        mt5, now=NOW,
        cash=cash() if observed is None else observed,
        baseline=baseline() if base is None else base,
        proposal=candidate() if proposal is None else proposal,
        costs=c, expected_cost_sha256=c.digest() if expected is None else expected,
        official_guard_pass=guard, session_source_verified=session,
    )


def test_account_bound_frozen_cash_and_stressed_margin_math_only(monkeypatch):
    mt5 = FakeSource()
    receipt = run(mt5, monkeypatch)
    assert receipt.decision.disposition == FullRiskDisposition.ALLOW_MATH_ONLY
    assert receipt.broker_price_loss_usd == D("5")
    assert receipt.decision.l_plan == D("8.00")
    assert receipt.execution_permitted is False
    assert mt5.calls.count("order_calc_profit") == 1
    assert mt5.calls.count("order_calc_margin") == 1
    assert "order_send" not in mt5.calls and "order_check" not in mt5.calls


@pytest.mark.parametrize("scenario", [
    "live", "wrong_account", "disconnected", "foreign_position",
    "pending_order", "quote_stale", "crossed_quote", "wrong_symbol",
    "tick_value_mismatch", "margin_missing", "future_tick",
    "equity_changed", "cost_hash_invalid", "event_unknown",
    "session_unknown", "cash_stale", "history_incomplete",
    "day_baseline_missing", "negative_cost", "sl_wrong_side",
    "entry_inside_spread", "off_grid", "loss_not_adverse",
])
def test_bad_evidence_denies_without_broker_order(monkeypatch, scenario):
    mt5 = FakeSource()
    obs, base, proposal, cost = cash(), baseline(), candidate(), costs()
    expected = None
    guard, session = True, True
    if scenario == "live":
        mt5.account["trade_mode"] = 2
    elif scenario == "wrong_account":
        mt5.account["login"] = 123
    elif scenario == "disconnected":
        mt5.term["connected"] = False
    elif scenario == "foreign_position":
        mt5.positions = [{"ticket": 900}]
    elif scenario == "pending_order":
        mt5.orders = [{"ticket": 400}]
    elif scenario == "quote_stale":
        mt5.tick["time_msc"] = int((NOW - timedelta(seconds=10)).timestamp() * 1000)
    elif scenario == "future_tick":
        mt5.tick["time_msc"] = int((NOW + timedelta(seconds=10)).timestamp() * 1000)
    elif scenario == "crossed_quote":
        mt5.tick["bid"] = 2701
    elif scenario == "wrong_symbol":
        mt5.info["trade_mode"] = 0
    elif scenario == "tick_value_mismatch":
        mt5.info["trade_tick_value_loss"] = 20
    elif scenario == "margin_missing":
        mt5.margin_value = None
    elif scenario == "equity_changed":
        mt5.account["equity"] = 9000
    elif scenario == "cost_hash_invalid":
        expected = "b" * 64
    elif scenario == "event_unknown":
        guard = False
    elif scenario == "session_unknown":
        session = False
    elif scenario == "cash_stale":
        obs = replace(obs, observed_utc=NOW - timedelta(minutes=1))
    elif scenario == "history_incomplete":
        obs = replace(obs, broker_history_complete=False)
    elif scenario == "day_baseline_missing":
        base = replace(base, day_start_equity=None)
    elif scenario == "negative_cost":
        cost = replace(cost, slippage_reserve_usd=D("-1"))
    elif scenario == "sl_wrong_side":
        proposal = replace(proposal, stop=D("2705"))
    elif scenario == "entry_inside_spread":
        proposal = replace(proposal, entry=D("2700"))
    elif scenario == "off_grid":
        proposal = replace(proposal, entry=D("2701.005"))
    else:
        mt5.loss_value = 5
    with pytest.raises(DemoSafetyError):
        run(mt5, monkeypatch, observed=obs, base=base,
            proposal=proposal, cost=cost, expected=expected,
            guard=guard, session=session)
    assert "order_send" not in mt5.calls and "order_check" not in mt5.calls


def test_risk_cap_violation_rejects_even_on_valid_broker_receipt(monkeypatch):
    mt5 = FakeSource()
    proposal = replace(candidate(), stop=D("2671"))
    mt5.loss_value = -30
    receipt = run(mt5, monkeypatch, proposal=proposal)
    assert receipt.decision.disposition == FullRiskDisposition.REJECT
    assert "POLICY_A_PER_TRADE_STOP_LOSS_USD" in receipt.decision.reasons
    assert not receipt.execution_permitted


def test_period_loss_pauses_preserved_not_reset_by_model(monkeypatch):
    mt5 = FakeSource()
    mt5.account["balance"] = 9910
    mt5.account["equity"] = 9910
    obs = replace(cash(), balance=D("9910"), equity=D("9910"))
    receipt = run(mt5, monkeypatch, observed=obs)
    assert receipt.decision.disposition == FullRiskDisposition.REJECT
    assert any("POLICY_A_DAILY" in r for r in receipt.decision.reasons)
