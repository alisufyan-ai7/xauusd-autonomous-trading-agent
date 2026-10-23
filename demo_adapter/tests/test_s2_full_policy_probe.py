# ruff: noqa: I001
from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

import pytest

from xauusd_agent.guards.event_guard import ProtectedEvent
from xauusd_agent.guards.v2_official_source_gate import VerifiedOfficialSnapshot
from xauusd_agent.risk.full_policy_a import FullRiskDisposition

from xauusd_demo.envelope import DemoIdentity, DemoOrderRequest, DemoPolicy, DemoSafetyError, DemoSide
from xauusd_demo.full_policy_broker_receipt import BoundAdverseCost
from xauusd_demo.ledger import DemoSubmissionLedger
from xauusd_demo.mt5_demo import DemoMT5Adapter
from xauusd_demo.prospective_cash_journal import ProspectiveDemoCashJournal
from xauusd_demo.s2_full_policy_probe import preview_s2_full_policy_tpb

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)
COMPANY, SERVER = "Exness Technologies Ltd", "Exness-MT5Trial15"
FP = hashlib.sha256(f"{COMPANY}|{SERVER}|321|USD".encode()).hexdigest()


class FakeS2Broker:
    ACCOUNT_TRADE_MODE_DEMO = 0
    TRADE_ACTION_PENDING = 5
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_SPECIFIED = 2
    SYMBOL_TRADE_MODE_FULL = 4
    DEAL_TYPE_BALANCE = 2
    DEAL_TYPE_CREDIT = 3
    DEAL_TYPE_BUY = 0
    DEAL_TYPE_SELL = 1

    def __init__(self):
        self.calls = []
        self.account = {
            "trade_mode": 0, "company": COMPANY, "server": SERVER, "currency": "USD",
            "login": 321, "balance": 10000, "equity": 10000,
            "margin": 0, "margin_free": 10000,
        }
        self.term = {"connected": True, "tradeapi_disabled": True}
        self.info = {
            "trade_mode": 4, "volume_min": 0.01, "volume_max": 100,
            "volume_step": 0.01, "trade_tick_size": 0.01,
            "trade_tick_value_loss": 1, "point": 0.01, "trade_stops_level": 10,
        }
        self.tick = {
            "time_msc": int(NOW.timestamp() * 1000),
            "bid": 2699.8, "ask": 2700,
        }
        self.orders = ()
        self.positions = ()
        self.history = [{
            "ticket": 11, "time_msc": int((NOW-timedelta(days=1)).timestamp()*1000),
            "type": 2, "profit": 10000, "commission": 0, "swap": 0,
            "fee": 0, "magic": 0,
        }]
        self.loss_value = -5
        self.margin_value = 8

    def initialize(self):
        self.calls.append("initialize")
        return True

    def shutdown(self):
        self.calls.append("shutdown")

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

    def symbol_info(self, symbol):
        self.calls.append("symbol_info")
        assert symbol == "XAUUSD"
        return self.info

    def symbol_info_tick(self, symbol):
        self.calls.append("symbol_info_tick")
        assert symbol == "XAUUSD"
        return self.tick

    def history_deals_get(self, since, now):
        self.calls.append("history_deals_get")
        assert since.year == 2000 and now == NOW
        return self.history

    def order_calc_profit(self, direction, symbol, lots, entry, sl):
        self.calls.append("order_calc_profit")
        assert direction in (self.ORDER_TYPE_BUY, self.ORDER_TYPE_SELL)
        assert symbol == "XAUUSD" and lots == 0.01
        return self.loss_value

    def order_calc_margin(self, direction, symbol, lots, entry):
        self.calls.append("order_calc_margin")
        assert direction in (self.ORDER_TYPE_BUY, self.ORDER_TYPE_SELL)
        assert symbol == "XAUUSD" and lots == 0.01
        return self.margin_value

    def order_send(self, *args, **kwargs):
        raise AssertionError("broker order_send forbidden in source-bound Policy A review")

    def order_check(self, *args, **kwargs):
        raise AssertionError("broker order_check forbidden in source-bound Policy A review")


def request(*, side=DemoSide.BUY):
    if side is DemoSide.BUY:
        prices = ("2701", "2696", "2713")
    else:
        prices = ("2699", "2704", "2687")
    return DemoOrderRequest(
        request_id="11111111-1111-4111-8111-111111111111",
        symbol="XAUUSD", side=side, volume_lots=D("0.01"),
        entry_stop=D(prices[0]), stop_loss=D(prices[1]),
        take_profit=D(prices[2]), expires_utc=NOW+timedelta(minutes=30),
    )


def costs():
    return BoundAdverseCost(
        calibration_id="SYNTHETIC_NOT_ADMITTED",
        evidence_sha256="1"*64,
        commission_roundtrip_usd=D("0.50"), swap_reserve_usd=D("0.50"),
        slippage_reserve_usd=D("1"), gap_reserve_usd=D("1"),
    )


AGENCIES = {
    "BLS": "bls.gov", "BEA": "bea.gov", "FED": "federalreserve.gov",
    "CENSUS": "census.gov", "DOL": "dol.gov",
}


def agency_sources():
    return tuple(
        VerifiedOfficialSnapshot(
            agency=a, source_host=host, raw_sha256=hex(i+10)[2]*64,
            parser_version="SYNTHETIC_NOT_APPROVED",
            captured_utc=NOW-timedelta(minutes=5),
            valid_through_utc=NOW+timedelta(hours=6),
            event_horizon_utc=NOW+timedelta(days=7),
            rights_for_local_processing_verified=True,
            parser_schema_verified=True,
            authoritative_release_coverage_verified=True,
            revision_conflicts_absent=True,
            events=(ProtectedEvent(f"{a}-event", NOW+timedelta(days=2), "TIER_1"),),
        )
        for i,(a,host) in enumerate(AGENCIES.items())
    )


def execute_preview(tmp_path, monkeypatch, *, modify=None, req=None, official=None, digest=None, session=None):
    monkeypatch.setattr("xauusd_demo.mt5_cash_source._EXPECTED_SHA", FP)
    monkeypatch.setattr("xauusd_demo.full_policy_broker_receipt.EXPECTED_ACCOUNT_SHA256", FP)
    mt5 = FakeS2Broker()
    if modify is not None:
        modify(mt5)
    expected = costs().digest() if digest is None else digest
    ledger = DemoSubmissionLedger(tmp_path / "s2.sqlite", max_daily_submissions=3)
    journal = ProspectiveDemoCashJournal(tmp_path / "cash.sqlite")
    try:
        with DemoMT5Adapter(
            DemoIdentity(COMPANY, SERVER, FP, "USD"),
            DemoPolicy(3), ledger, module=mt5
        ) as adapter:
            risk = preview_s2_full_policy_tpb(
                adapter, request() if req is None else req,
                now=NOW, cash_journal=journal, calibrated_costs=costs(),
                pinned_cost_sha256=expected,
                official_snapshots=agency_sources() if official is None else official,
                session_verified_through_utc=(
                    NOW+timedelta(hours=2) if session is None else session
                ),
                shock_locked=False, normalized=True,
            )
    finally:
        ledger.close()
        journal.close()
    return risk, mt5


@pytest.mark.parametrize("side", [DemoSide.BUY, DemoSide.SELL])
def test_single_s2_real_source_pipeline_still_nonordering(tmp_path, monkeypatch, side):
    receipt, mt5 = execute_preview(
        tmp_path, monkeypatch, req=request(side=side),
    )
    assert receipt.mathematics_pass
    assert receipt.risk.decision.disposition is FullRiskDisposition.ALLOW_MATH_ONLY
    assert receipt.risk.decision.l_plan == D("8")
    assert receipt.broker_entry == request(side=side).entry_stop
    assert receipt.broker_order_type == (
        mt5.ORDER_TYPE_BUY_STOP if side is DemoSide.BUY
        else mt5.ORDER_TYPE_SELL_STOP
    )
    assert not receipt.execution_permitted
    assert mt5.calls.count("history_deals_get") == 1
    assert mt5.calls.count("order_calc_profit") == 1
    assert mt5.calls.count("order_calc_margin") == 1
    assert "order_send" not in mt5.calls and "order_check" not in mt5.calls


@pytest.mark.parametrize("failure", [
    "foreign_position", "pending_order", "old_trade", "history_error",
    "nonreconciled_deposit", "wrong_server", "live", "stale_tick",
    "nonmatching_broker_cash", "bad_margin", "bad_loss",
])
def test_source_failures_cannot_convert_to_order_authority(tmp_path, monkeypatch, failure):
    def mutate(mt5):
        if failure == "foreign_position":
            mt5.positions = ({"ticket": 100},)
        elif failure == "pending_order":
            mt5.orders = ({"ticket": 100},)
        elif failure == "old_trade":
            mt5.history.append({
                "ticket": 12, "time_msc": int(NOW.timestamp()*1000),
                "type": 1, "profit": 0, "commission": 0, "swap": 0,
                "fee": 0, "magic": 260101,
            })
        elif failure == "history_error":
            mt5.history = None
        elif failure == "nonreconciled_deposit":
            mt5.history[0]["profit"] = 9000
        elif failure == "wrong_server":
            mt5.account["server"] = "LIVE-server"
        elif failure == "live":
            mt5.account["trade_mode"] = 2
        elif failure == "stale_tick":
            mt5.tick["time_msc"] -= 10000
        elif failure == "nonmatching_broker_cash":
            mt5.account["equity"] = 9000
        elif failure == "bad_margin":
            mt5.margin_value = 0
        else:
            mt5.loss_value = -100

    with pytest.raises(DemoSafetyError):
        execute_preview(tmp_path, monkeypatch, modify=mutate)


def test_unsourced_calibration_and_missing_agency_fail_before_history(tmp_path, monkeypatch):
    with pytest.raises(DemoSafetyError, match="digest"):
        execute_preview(tmp_path/"cost", monkeypatch, digest="f"*64)
    with pytest.raises(DemoSafetyError, match="lifetime"):
        execute_preview(tmp_path/"event", monkeypatch, official=agency_sources()[:-1])


def test_broker_risk_cap_is_reject_not_allow_even_when_source_valid(tmp_path, monkeypatch):
    def adjust(mt5):
        mt5.loss_value = -30
        mt5.info["trade_tick_value_loss"] = 6
    receipt, mt5 = execute_preview(tmp_path, monkeypatch, modify=adjust)
    assert receipt.risk.decision.disposition is FullRiskDisposition.REJECT
    assert not receipt.mathematics_pass
    assert "POLICY_A_PER_TRADE_STOP_LOSS_USD" in receipt.risk.decision.reasons


def test_wrong_stop_or_nonstop_request_never_previews(tmp_path, monkeypatch):
    bad_stop = replace(request(), stop_loss=D("2702"))
    with pytest.raises(DemoSafetyError):
        execute_preview(tmp_path/"bad", monkeypatch, req=bad_stop)
    no_pending = replace(request(), entry_stop=None, take_profit=None, expires_utc=None)
    with pytest.raises(DemoSafetyError):
        execute_preview(tmp_path/"nonstop", monkeypatch, req=no_pending)
