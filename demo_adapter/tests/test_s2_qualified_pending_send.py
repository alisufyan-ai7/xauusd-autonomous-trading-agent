# ruff: noqa: I001
"""Offline actual-S2-sender STOP admission tests; fake MT5 only, never real orders."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from test_s2_full_policy_probe import (
    FakeS2Broker, FP, COMPANY, SERVER, agency_sources, costs, request,
)
from xauusd_demo.control import ARM_CONFIRMATION, DemoControlStore
from xauusd_demo.envelope import (
    DemoActivationPermit, DemoIdentity, DemoPolicy, DemoSafetyError,
)
from xauusd_demo.ledger import DemoSubmissionLedger
from xauusd_demo.mt5_demo import DemoMT5Adapter, SUBMISSION_CONFIRMATION
from xauusd_demo.prospective_cash_journal import ProspectiveDemoCashJournal
from xauusd_demo.risk_binding import DemoRiskCalibration, DEMO_LIFECYCLE_SCOPE
from xauusd_demo.s2_order_sources import S2OrderSources

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)


class BrokerPending(FakeS2Broker):
    TRADE_RETCODE_PLACED = 10008
    TRADE_RETCODE_DONE = 10009
    ORDER_STATE_PLACED = 1

    def __init__(self):
        super().__init__()
        self.check_calls = 0
        self.send_calls = 0
        self.return_none = False
        self.bad_receipt = False
        self.bad_retcode = False
        self.term["tradeapi_disabled"] = False

    def last_error(self):
        return (0, "ok")

    def order_check(self, payload):
        self.check_calls += 1
        assert payload["type"] == self.ORDER_TYPE_BUY_STOP
        assert payload["volume"] == 0.01
        assert payload["magic"] == 260101
        return {"retcode": 0}

    def order_send(self, payload):
        self.send_calls += 1
        if self.return_none:
            return None
        if self.bad_retcode:
            return {"retcode": self.TRADE_RETCODE_DONE, "order": 501}
        self.orders = ({
            "ticket": 999 if self.bad_receipt else 501,
            "symbol": "XAUUSD", "magic": 260101,
            "type": payload["type"], "volume_initial": payload["volume"],
            "price_open": payload["price"], "sl": payload["sl"],
            "tp": payload["tp"], "time_expiration": payload["expiration"],
            "state": self.ORDER_STATE_PLACED,
        },)
        return {"retcode": self.TRADE_RETCODE_PLACED, "order": 501}


def activation():
    return DemoActivationPermit(
        activation_id="REAL_DEMO_UNIT_TEST",
        account_id_sha256=FP, server=SERVER,
        max_daily_submissions=3,
        not_before_utc=NOW-timedelta(minutes=5),
        expires_utc=NOW+timedelta(minutes=30),
    )


def cal():
    return DemoRiskCalibration(
        "UNIT_BOUNDED", "a"*64, DEMO_LIFECYCLE_SCOPE, D("1"), D("2")
    )


def make_source(journal, **kwargs):
    original = costs()
    testcost = replace(original, calibration_id="OFFLINE_TEST_SOURCE")
    snapshot = tuple(
        replace(s, parser_version="OFFLINE_UNIT_TEST_PARSER") for s in agency_sources()
    )
    return S2OrderSources(
        cash_journal=journal, costs=testcost,
        expected_cost_sha256=testcost.digest(),
        official_snapshots=snapshot,
        session_verified_through_utc=NOW + timedelta(hours=2),
        shock_locked=False, normalized=True,
        **kwargs,
    )


def run(tmp_path, monkeypatch, *, change=None, source_change=None):
    monkeypatch.setattr("xauusd_demo.mt5_cash_source._EXPECTED_SHA", FP)
    monkeypatch.setattr("xauusd_demo.full_policy_broker_receipt.EXPECTED_ACCOUNT_SHA256", FP)
    broker = BrokerPending()
    if change is not None:
        change(broker)
    item = request()
    with (
        DemoSubmissionLedger(tmp_path / "orders.sqlite", max_daily_submissions=3) as book,
        DemoControlStore(tmp_path / "control.sqlite") as control,
        ProspectiveDemoCashJournal(tmp_path / "cash.sqlite") as cash,
    ):
        identity = DemoIdentity(COMPANY, SERVER, FP, "USD")
        control.arm(
            permit=activation(), identity=identity, now=NOW,
            confirmation_phrase=ARM_CONFIRMATION,
        )
        source = make_source(cash)
        if source_change is not None:
            source = source_change(source)
        policy = DemoPolicy(3, cal().sha256())
        with DemoMT5Adapter(
            identity, policy, book, module=broker, control=control,
        ) as adapter:
            try:
                result = adapter.submit_market_order(
                    item, confirmation_phrase=SUBMISSION_CONFIRMATION,
                    activation_permit=activation(), risk_calibration=cal(),
                    full_policy_sources=source, now=NOW,
                )
                err = None
            except DemoSafetyError as exc:
                result, err = None, str(exc)
        return result, err, broker.check_calls, broker.send_calls, book.status(
            item.request_id
        ), control.snapshot().state.value


def test_real_source_bound_pending_stop_reaches_single_s2_send(tmp_path, monkeypatch):
    report, error, check, send, ledger, control = run(tmp_path, monkeypatch)
    assert error is None
    assert report is not None
    assert report["status"] == "PENDING_ACKNOWLEDGED"
    assert report["pending_order_ticket"] == 501
    assert report["live_account_permitted"] is False
    assert (check, send, ledger, control) == (1, 1, "ACKNOWLEDGED", "ACTIVE")


@pytest.mark.parametrize("change", [
    lambda b: setattr(b, "return_none", True),
    lambda b: setattr(b, "bad_receipt", True),
    lambda b: setattr(b, "bad_retcode", True),
])
def test_ambiguous_mt5_send_never_retries_or_reports_fill(tmp_path, monkeypatch, change):
    result, error, check, send, ledger, control = run(
        tmp_path, monkeypatch, change=change
    )
    assert result is None
    assert error
    assert (check, send, ledger, control) == (1, 1, "UNCERTAIN", "QUARANTINED")


@pytest.mark.parametrize("source_change", [
    lambda s: replace(s, costs=replace(s.costs, gap_reserve_usd=D("0"))),
    lambda s: replace(s, official_snapshots=()),
    lambda s: replace(s, session_verified_through_utc=NOW-timedelta(seconds=1)),
    lambda s: replace(
        s, expected_cost_sha256="f"*64
    ),
])
def test_missing_or_stale_risk_event_cost_cannot_send(
    tmp_path, monkeypatch, source_change,
):
    result, error, check, send, ledger, control = run(
        tmp_path, monkeypatch, source_change=source_change
    )
    assert result is None and error
    assert check == 0 and send == 0 and ledger is None
    assert control == "QUARANTINED"


@pytest.mark.parametrize("change", [
    lambda b: b.account.__setitem__("trade_mode", 2),
    lambda b: b.account.__setitem__("server", "LIVE"),
    lambda b: setattr(b, "positions", ({"ticket": 77},)),
])
def test_wrong_account_or_exposure_never_submits(tmp_path, monkeypatch, change):
    try:
        result, error, check, send, ledger, state = run(
            tmp_path, monkeypatch, change=change
        )
    except DemoSafetyError:
        # Invalid DEMO identity is rejected at initialization itself.
        return
    # Unknown exposure is rejected during the attended source-bound preflight.
    assert result is None and error
    assert check == 0 and send == 0 and ledger is None
    assert state == "QUARANTINED"


def test_caller_cannot_turn_math_receipt_into_broker_submission(tmp_path, monkeypatch):
    def bad_source(s):
        return replace(s, costs=replace(s.costs, calibration_id="SYNTHETIC_FORGED"))
    report, error, check, send, ledger, control = run(
        tmp_path, monkeypatch, source_change=bad_source
    )
    assert report is None and error
    assert check == 0 and send == 0 and ledger is None
    assert control == "QUARANTINED"
