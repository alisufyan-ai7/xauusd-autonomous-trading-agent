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
    NullExecutionRecord,
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


def test_every_fail_closed_runtime_branch_preserves_exact_outcome() -> None:
    base = _inputs()
    stale_quote = replace(
        base.market.quote,
        broker_time=NOW - timedelta(seconds=3),
        received_time=NOW - timedelta(seconds=3),
    )
    cases = (
        (
            "admission unknown",
            replace(base, market=replace(base.market, quote=None)),
            RuntimeState.QUARANTINED,
            ("QUOTE_MISSING",),
        ),
        (
            "admission lock",
            replace(base, market=replace(base.market, quote=stale_quote)),
            RuntimeState.SHADOW,
            ("QUOTE_STALE",),
        ),
        (
            "event unknown",
            replace(
                base,
                event_guard=EventGuardDecision(
                    EventGuardState.UNKNOWN, ("EVENT_INVENTORY_MISSING",)
                ),
            ),
            RuntimeState.QUARANTINED,
            ("EVENT_INVENTORY_MISSING",),
        ),
        (
            "event source unhealthy",
            replace(
                base,
                event_guard=EventGuardDecision(
                    EventGuardState.SOURCE_UNHEALTHY, ("SOURCE_UNHEALTHY",)
                ),
            ),
            RuntimeState.QUARANTINED,
            ("SOURCE_UNHEALTHY",),
        ),
        (
            "event lock",
            replace(
                base,
                event_guard=EventGuardDecision(EventGuardState.PRE_LOCK, ("PRE_LOCK",)),
            ),
            RuntimeState.SHADOW,
            ("PRE_LOCK",),
        ),
        (
            "gate unknown",
            replace(
                base,
                market_gates=(GateDecision(GateState.UNKNOWN, ("SESSION_UNKNOWN",)),),
            ),
            RuntimeState.QUARANTINED,
            ("SESSION_UNKNOWN",),
        ),
        (
            "gate lock",
            replace(
                base,
                market_gates=(GateDecision(GateState.LOCK, ("SESSION_CLOSED",)),),
            ),
            RuntimeState.SHADOW,
            ("SESSION_CLOSED",),
        ),
        (
            "reconciliation quarantine",
            replace(
                base,
                reconciliation=replace(
                    base.reconciliation,
                    status=ReconciliationStatus.MISMATCH,
                    disposition=ReconciliationDisposition.QUARANTINE_HUMAN_REVIEW,
                    reason_codes=("UNEXPECTED_BROKER_EXPOSURE",),
                ),
            ),
            RuntimeState.QUARANTINED,
            ("UNEXPECTED_BROKER_EXPOSURE",),
        ),
        (
            "risk quarantine",
            replace(
                base,
                risk=replace(
                    base.risk,
                    disposition=RiskDisposition.QUARANTINE,
                    reason_codes=("UNKNOWN_EXPOSURE",),
                ),
            ),
            RuntimeState.QUARANTINED,
            ("UNKNOWN_EXPOSURE",),
        ),
        (
            "risk reject",
            replace(
                base,
                risk=replace(
                    base.risk,
                    disposition=RiskDisposition.REJECT,
                    reason_codes=("V1_VOLUME_CAP_EXCEEDED",),
                ),
            ),
            RuntimeState.SHADOW,
            ("V1_VOLUME_CAP_EXCEEDED",),
        ),
        (
            "analyst inadmissible",
            replace(
                base,
                analyst=AnalystVerdict(
                    AnalystDecision.NO_TRADE, False, ("ANALYST_UNAVAILABLE",)
                ),
            ),
            RuntimeState.DEGRADED,
            ("ANALYST_UNAVAILABLE",),
        ),
        (
            "analyst no trade",
            replace(
                base,
                analyst=AnalystVerdict(
                    AnalystDecision.NO_TRADE, True, ("ANALYST_NO_TRADE",)
                ),
            ),
            RuntimeState.SHADOW,
            ("ANALYST_NO_TRADE",),
        ),
        (
            "missing setup identity",
            replace(base, setup_id=None),
            RuntimeState.QUARANTINED,
            ("SETUP_IDENTITY_MISSING",),
        ),
    )

    for label, inputs, expected_state, expected_reasons in cases:
        result = evaluate_shadow_cycle(inputs)
        assert result.state is expected_state, label
        assert result.decision is DecisionKind.NO_ACTION, label
        assert result.reason_codes == expected_reasons, label
        assert result.setup_id is None, label
        assert result.decision_id == "decision-1", label
        assert result.observed_at_utc == "2026-10-07T12:00:00.000000Z", label
        assert len(result.state_hash) == 64, label
        assert result.null_execution.decision_id == "decision-1", label
        assert result.null_execution.decided_at_utc == result.observed_at_utc, label
        assert result.null_execution.setup_id is None, label
        assert result.null_execution.risk_disposition is inputs.risk.disposition, label
        assert result.null_execution.risk_reason_codes == inputs.risk.reason_codes, label
        assert result.execution_capability is ExecutionCapability.ABSENT, label
        assert result.broker_action_count == 0, label


def test_empty_runtime_reason_list_is_replaced_with_stable_fail_closed_reason() -> None:
    result = evaluate_shadow_cycle(
        replace(
            _inputs(),
            event_guard=EventGuardDecision(EventGuardState.PRE_LOCK, ()),
        )
    )
    assert result.reason_codes == ("ALL_EXECUTION_DISABLED_GATES_PASS",)
    assert result.state is RuntimeState.SHADOW
    assert result.decision is DecisionKind.NO_ACTION


def test_shadow_cycle_result_rejects_every_execution_capability_violation() -> None:
    valid = evaluate_shadow_cycle(_inputs())
    with pytest.raises(ValueError, match="^execution capability must remain absent$"):
        replace(valid, execution_capability=object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="^broker action count must remain zero$"):
        replace(valid, broker_action_count=1)
    unsafe_null = NullExecutionRecord(
        decision_id="decision-1",
        decided_at_utc="2026-10-07T12:00:00.000000Z",
        setup_id="setup-1",
        risk_disposition=RiskDisposition.ALLOW,
        risk_reason_codes=("ALL_FROZEN_CONTROLS_PASS",),
    )
    object.__setattr__(unsafe_null, "broker_action_count", 1)
    with pytest.raises(
        ValueError, match="^null execution record must contain zero broker actions$"
    ):
        replace(valid, null_execution=unsafe_null)


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
    with pytest.raises(ValueError) as missing_identity:
        replace(_inputs(), decision_id="")
    assert str(missing_identity.value) == "decision_id is required"
    with pytest.raises(ValueError) as clock_mismatch:
        replace(_inputs(), observed_at=NOW.replace(minute=1))
    assert str(clock_mismatch.value) == "market decision time must equal observed_at"
    indeterminate = NOW.replace(tzinfo=_IndeterminateTimezone())
    with pytest.raises(ValueError) as invalid_clock:
        replace(_inputs(), observed_at=indeterminate)
    assert str(invalid_clock.value) == "observed_at must be timezone-aware"
