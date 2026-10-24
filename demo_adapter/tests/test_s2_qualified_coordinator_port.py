# ruff: noqa: I001
"""Qualified MT5 DEMO STOP bridge; all broker writes target fake MT5 only."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal as D


from test_s2_qualified_pending_send import (
    BrokerPending, FP, COMPANY, SERVER, activation, cal, make_source,
)
from test_s2_readonly_coordinator_port import tpb
from xauusd_demo.continuous_coordinator import ContinuousDemoCoordinator
from xauusd_demo.control import ARM_CONFIRMATION, DemoControlStore
from xauusd_demo.envelope import DemoIdentity, DemoPolicy
from xauusd_demo.ledger import DemoSubmissionLedger
from xauusd_demo.mt5_demo import DemoMT5Adapter
from xauusd_demo.prospective_cash_journal import ProspectiveDemoCashJournal
from xauusd_demo.s2_qualified_coordinator_port import QualifiedS2CoordinatorPort

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)


class Strategy:
    def __init__(self):
        self.calls = 0

    def observe_closed_bar_plan(self, now):
        self.calls += 1
        return replace(
            tpb(),
            protective_stop=D("2696"),
            take_profit=D("2713"),
        )


class Sources:
    def __init__(self, cash):
        self.cash = cash

    def current_sources(self, now):
        return make_source(self.cash)


def test_qualified_tpb_coordinator_places_one_real_shape_pending_order(tmp_path, monkeypatch):
    monkeypatch.setattr("xauusd_demo.mt5_cash_source._EXPECTED_SHA", FP)
    monkeypatch.setattr("xauusd_demo.full_policy_broker_receipt.EXPECTED_ACCOUNT_SHA256", FP)
    mt5 = BrokerPending()
    idn = DemoIdentity(COMPANY, SERVER, FP, "USD")
    with (
        DemoSubmissionLedger(tmp_path / "submissions.sqlite", max_daily_submissions=3) as ledger,
        DemoControlStore(tmp_path / "control.sqlite") as control,
        ProspectiveDemoCashJournal(tmp_path / "cash.sqlite") as cash,
        ContinuousDemoCoordinator(tmp_path / "agent.sqlite", account_fingerprint=FP) as engine,
    ):
        control.arm(
            permit=activation(), identity=idn, now=NOW,
            confirmation_phrase=ARM_CONFIRMATION,
        )
        engine.arm_attended(
            confirmation="ARM-CONTINUOUS-PRO-DEMO-XAUUSD",
            broker_flat_confirmed=True,
        )
        with DemoMT5Adapter(
            idn, DemoPolicy(3, cal().sha256()),
            ledger, control=control, module=mt5,
        ) as adapter:
            port = QualifiedS2CoordinatorPort(
                adapter=adapter, plan_source=Strategy(), sources=Sources(cash),
                activation=activation(), risk_calibration=cal(),
            )
            outcome = engine.cycle(port, now=NOW)
            assert outcome.action == "BROKER_PENDING_ACKNOWLEDGED"
            assert outcome.reason == "501"
            assert ledger.status("11111111-1111-4111-8111-111111111111") is None
            # The TPB translator uses a derived request_id, not the old unit fixture.
            assert mt5.send_calls == 1 and mt5.check_calls == 1
            assert engine.conn.execute(
                "SELECT COUNT(*) FROM agent_pending_receipts"
            ).fetchone()[0] == 1
            assert engine.cycle(port, now=NOW).action == "MONITOR_PENDING_ORDER"
            assert mt5.send_calls == 1


def test_coordinator_with_disabled_python_never_creates_trade_intent(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr("xauusd_demo.mt5_cash_source._EXPECTED_SHA", FP)
    monkeypatch.setattr("xauusd_demo.full_policy_broker_receipt.EXPECTED_ACCOUNT_SHA256", FP)
    mt5 = BrokerPending()
    mt5.term["tradeapi_disabled"] = True
    idn = DemoIdentity(COMPANY, SERVER, FP, "USD")
    with (
        DemoSubmissionLedger(tmp_path / "orders.sqlite", max_daily_submissions=3) as ledger,
        DemoControlStore(tmp_path / "control.sqlite") as control,
        ProspectiveDemoCashJournal(tmp_path / "cash.sqlite") as cash,
        ContinuousDemoCoordinator(tmp_path / "engine.sqlite", account_fingerprint=FP) as engine,
    ):
        engine.arm_attended(
            confirmation="ARM-CONTINUOUS-PRO-DEMO-XAUUSD",
            broker_flat_confirmed=True,
        )
        with DemoMT5Adapter(
            idn, DemoPolicy(3, cal().sha256()), ledger, control=control, module=mt5,
        ) as adapter:
            port = QualifiedS2CoordinatorPort(
                adapter=adapter, plan_source=Strategy(), sources=Sources(cash),
                activation=activation(), risk_calibration=cal(),
            )
            outcome = engine.cycle(port, now=NOW)
            assert outcome.action == "NO_ORDER"
            assert outcome.state == "QUARANTINED"
            assert mt5.send_calls == 0 and mt5.check_calls == 0
            assert engine.conn.execute(
                "SELECT COUNT(*) FROM agent_cycles"
            ).fetchone()[0] == 0


def test_qualified_port_cannot_propose_source_free_false_risk(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr("xauusd_demo.mt5_cash_source._EXPECTED_SHA", FP)
    monkeypatch.setattr("xauusd_demo.full_policy_broker_receipt.EXPECTED_ACCOUNT_SHA256", FP)
    mt5 = BrokerPending()
    mt5.loss_value = -50
    mt5.info["trade_tick_value_loss"] = 10
    idn = DemoIdentity(COMPANY, SERVER, FP, "USD")
    with (
        DemoSubmissionLedger(tmp_path / "orders.sqlite", max_daily_submissions=3) as ledger,
        ProspectiveDemoCashJournal(tmp_path / "cash.sqlite") as cash,
    ):
        with DemoMT5Adapter(
            idn, DemoPolicy(3, cal().sha256()), ledger, module=mt5,
        ) as adapter:
            port = QualifiedS2CoordinatorPort(
                adapter=adapter, plan_source=Strategy(), sources=Sources(cash),
                activation=activation(), risk_calibration=cal(),
            )
            assert port.one_cycle_proposal(NOW) is None
            assert mt5.send_calls == 0 and mt5.check_calls == 0
