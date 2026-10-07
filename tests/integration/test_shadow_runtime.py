from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta, tzinfo
from decimal import Decimal

import pytest

from xauusd_agent.analyst import AnalystDecision, AnalystVerdict
from xauusd_agent.core.model import DecisionKind, ExecutionCapability, RuntimeState
from xauusd_agent.guards import (
    EventGuardDecision,
    EventGuardState,
    GateDecision,
    GateState,
)
from xauusd_agent.market import AdmissionPolicy, Bar, MarketSnapshot, Quote, Timeframe
from xauusd_agent.reconciliation import (
    ReconciliationDisposition,
    ReconciliationStatus,
    reconcile_exposure,
)
from xauusd_agent.risk import RiskDisposition, RiskEvaluation
from xauusd_agent.runtime import ShadowCycleInput, evaluate_shadow_cycle

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
POLICY = AdmissionPolicy(minima={Timeframe.H4: 1, Timeframe.H1: 1, Timeframe.M15: 1})


class _IndeterminateTimezone(tzinfo):
    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)


def _bar(timeframe: Timeframe) -> Bar:
    return Bar(
        symbol="XAUUSD",
        timeframe=timeframe,
        open_time=NOW - timeframe.duration,
        open=Decimal("4000.00"),
        high=Decimal("4002.00"),
        low=Decimal("3998.00"),
        close=Decimal("4001.00"),
        tick_volume=10,
    )


def _inputs() -> ShadowCycleInput:
    market = MarketSnapshot(
        decision_time=NOW,
        quote=Quote(
            symbol="XAUUSD",
            broker_time=NOW,
            received_time=NOW,
            bid=Decimal("4000.00"),
            ask=Decimal("4000.10"),
            tick_size=Decimal("0.01"),
            sequence=1,
        ),
        bars={timeframe: (_bar(timeframe),) for timeframe in Timeframe},
        known_breaks={},
        account_symbol_known=True,
        precision_known=True,
        session_state_known=True,
    )
    risk = RiskEvaluation(
        policy="POLICY_A_V1_M1",
        disposition=RiskDisposition.ALLOW,
        reason_codes=("ALL_FROZEN_CONTROLS_PASS",),
        requested_volume_lots=Decimal("0.01"),
    )
    return ShadowCycleInput(
        decision_id="decision-1",
        observed_at=NOW,
        market=market,
        event_guard=EventGuardDecision(EventGuardState.HEALTHY, ()),
        market_gates=(
            GateDecision(GateState.CLEAR, ()),
            GateDecision(GateState.CLEAR, ()),
        ),
        reconciliation=reconcile_exposure((), (), ()),
        risk=risk,
        analyst=AnalystVerdict(AnalystDecision.SETUP, True, ("STRUCTURE_OK",)),
        setup_id="setup-1",
        admission_policy=POLICY,
    )


def test_fully_admissible_cycle_records_setup_but_cannot_execute() -> None:
    result = evaluate_shadow_cycle(_inputs())
    assert result.decision_id == "decision-1"
    assert result.observed_at_utc == "2026-10-07T12:00:00.000000Z"
    assert result.decision is DecisionKind.SETUP
    assert result.state is RuntimeState.SHADOW
    assert result.setup_id == "setup-1"
    assert result.reason_codes == ("ALL_EXECUTION_DISABLED_GATES_PASS",)
    assert result.state_hash == "cb8268b24fb8403c04c3b0590755768e98ef2750220ed6f04f22ac95b4d4c494"
    assert result.execution_capability is ExecutionCapability.ABSENT
    assert result.broker_action_count == 0
    assert result.null_execution.decision_id == "decision-1"
    assert result.null_execution.decided_at_utc == "2026-10-07T12:00:00.000000Z"
    assert result.null_execution.setup_id == "setup-1"
    assert result.null_execution.risk_disposition is RiskDisposition.ALLOW
    assert result.null_execution.risk_reason_codes == ("ALL_FROZEN_CONTROLS_PASS",)
    assert result.null_execution.broker_action_count == 0
    assert result.null_execution.execution_capability == "ABSENT"


def test_unknown_gate_quarantines_without_broker_action() -> None:
    inputs = replace(
        _inputs(),
        market_gates=(GateDecision(GateState.UNKNOWN, ("SESSION_UNKNOWN",)),),
    )
    result = evaluate_shadow_cycle(inputs)
    assert result.decision is DecisionKind.NO_ACTION
    assert result.state is RuntimeState.QUARANTINED
    assert result.broker_action_count == 0


def test_broker_exposure_mismatch_quarantines_without_automatic_close() -> None:
    reconciliation = replace(
        _inputs().reconciliation,
        status=ReconciliationStatus.MISMATCH,
        disposition=ReconciliationDisposition.QUARANTINE_HUMAN_REVIEW,
        reason_codes=("UNEXPECTED_BROKER_EXPOSURE",),
    )
    result = evaluate_shadow_cycle(replace(_inputs(), reconciliation=reconciliation))
    assert result.state is RuntimeState.QUARANTINED
    assert result.null_execution.result.value == "NOT_EXECUTED"
    assert reconciliation.automatic_close_permitted is False


@pytest.mark.parametrize(
    ("status", "disposition"),
    [
        (ReconciliationStatus.MATCH_ZERO, ReconciliationDisposition.QUARANTINE_HUMAN_REVIEW),
        (ReconciliationStatus.MISMATCH, ReconciliationDisposition.CONTINUE),
    ],
)
def test_any_inconsistent_reconciliation_dimension_quarantines(
    status: ReconciliationStatus, disposition: ReconciliationDisposition
) -> None:
    reconciliation = replace(
        _inputs().reconciliation,
        status=status,
        disposition=disposition,
        reason_codes=("INCONSISTENT_RECONCILIATION",),
    )
    result = evaluate_shadow_cycle(replace(_inputs(), reconciliation=reconciliation))
    assert result.state is RuntimeState.QUARANTINED
    assert result.decision is DecisionKind.NO_ACTION
    assert result.reason_codes == ("INCONSISTENT_RECONCILIATION",)
    assert result.broker_action_count == 0


def test_analyst_failure_degrades_and_never_promotes_setup() -> None:
    analyst = AnalystVerdict(
        AnalystDecision.NO_TRADE,
        False,
        ("ANALYST_UNAVAILABLE:AnalystTransportDisabled",),
    )
    result = evaluate_shadow_cycle(replace(_inputs(), analyst=analyst))
    assert result.decision is DecisionKind.NO_ACTION
    assert result.state is RuntimeState.DEGRADED
    assert result.setup_id is None
    assert result.broker_action_count == 0


def test_missing_setup_identity_quarantines_even_after_setup_verdict() -> None:
    result = evaluate_shadow_cycle(replace(_inputs(), setup_id=None))
    assert result.decision is DecisionKind.NO_ACTION
    assert result.state is RuntimeState.QUARANTINED
    assert result.reason_codes == ("SETUP_IDENTITY_MISSING",)


def test_cycle_input_requires_identity_and_exact_decision_clock() -> None:
    with pytest.raises(ValueError, match="decision_id is required"):
        replace(_inputs(), decision_id="")
    with pytest.raises(ValueError, match="decision time must equal observed_at"):
        replace(_inputs(), observed_at=NOW.replace(minute=1))
    indeterminate = NOW.replace(tzinfo=_IndeterminateTimezone())
    with pytest.raises(ValueError, match="observed_at must be timezone-aware"):
        replace(_inputs(), observed_at=indeterminate)
