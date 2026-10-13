"""Deterministic composition for one execution-disabled shadow cycle.

This module composes already-observed inputs. It contains no network, process,
broker, model-provider, or alert-delivery capability. Even a fully admissible
SETUP produces only a NullExecutionRecord.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from xauusd_agent.analyst import AnalystDecision, AnalystVerdict
from xauusd_agent.core.canonical import sha256_hex
from xauusd_agent.core.clock import format_utc
from xauusd_agent.core.model import DecisionKind, ExecutionCapability, RuntimeState
from xauusd_agent.guards import (
    EventGuardDecision,
    EventGuardState,
    GateDecision,
    GateState,
    combine_gates,
)
from xauusd_agent.market import AdmissionPolicy, AdmissionState, MarketSnapshot
from xauusd_agent.market.admission import admit_market_snapshot
from xauusd_agent.reconciliation import (
    ExposureReconciliation,
    NullExecutionRecord,
    ReconciliationDisposition,
    ReconciliationStatus,
)
from xauusd_agent.risk import RiskDisposition, RiskEvaluation


@dataclass(frozen=True, slots=True)
class ShadowCycleInput:
    decision_id: str
    observed_at: datetime
    market: MarketSnapshot
    event_guard: EventGuardDecision
    market_gates: tuple[GateDecision, ...]
    reconciliation: ExposureReconciliation
    risk: RiskEvaluation
    analyst: AnalystVerdict
    setup_id: str | None
    admission_policy: AdmissionPolicy

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise ValueError("decision_id is required")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.market.decision_time != self.observed_at:
            raise ValueError("market decision time must equal observed_at")
        object.__setattr__(self, "market_gates", tuple(self.market_gates))


@dataclass(frozen=True, slots=True)
class ShadowCycleResult:
    decision_id: str
    observed_at_utc: str
    state: RuntimeState
    decision: DecisionKind
    setup_id: str | None
    reason_codes: tuple[str, ...]
    state_hash: str
    null_execution: NullExecutionRecord
    execution_capability: ExecutionCapability = ExecutionCapability.ABSENT
    broker_action_count: int = 0

    def __post_init__(self) -> None:
        if self.execution_capability is not ExecutionCapability.ABSENT:
            raise ValueError("execution capability must remain absent")
        if self.broker_action_count != 0:
            raise ValueError("broker action count must remain zero")
        if self.null_execution.broker_action_count != 0:
            raise ValueError("null execution record must contain zero broker actions")


def _finish(
    inputs: ShadowCycleInput,
    *,
    state: RuntimeState,
    decision: DecisionKind,
    reasons: tuple[str, ...],
    setup_id: str | None = None,
) -> ShadowCycleResult:
    observed_at_utc = format_utc(inputs.observed_at)
    stable_reasons = tuple(dict.fromkeys(reasons))
    if not stable_reasons:
        stable_reasons = ("ALL_EXECUTION_DISABLED_GATES_PASS",)
    state_hash = sha256_hex(
        "shadow-cycle-v1",
        inputs.decision_id,
        observed_at_utc,
        state.value,
        decision.value,
        setup_id,
        stable_reasons,
        inputs.risk.policy,
        inputs.risk.disposition.value,
        inputs.reconciliation.status.value,
        inputs.event_guard.state.value,
    )
    null_execution = NullExecutionRecord(
        decision_id=inputs.decision_id,
        decided_at_utc=observed_at_utc,
        setup_id=setup_id,
        risk_disposition=inputs.risk.disposition,
        risk_reason_codes=inputs.risk.reason_codes,
    )
    return ShadowCycleResult(
        decision_id=inputs.decision_id,
        observed_at_utc=observed_at_utc,
        state=state,
        decision=decision,
        setup_id=setup_id,
        reason_codes=stable_reasons,
        state_hash=state_hash,
        null_execution=null_execution,
    )


def evaluate_shadow_cycle(inputs: ShadowCycleInput) -> ShadowCycleResult:
    """Evaluate one cycle and always terminate at the null execution boundary."""

    admission = admit_market_snapshot(inputs.market, inputs.admission_policy)
    if admission.state is AdmissionState.UNKNOWN:
        return _finish(
            inputs,
            state=RuntimeState.QUARANTINED,
            decision=DecisionKind.NO_ACTION,
            reasons=admission.reasons,
        )
    if admission.state is AdmissionState.LOCK:
        return _finish(
            inputs,
            state=RuntimeState.SHADOW,
            decision=DecisionKind.NO_ACTION,
            reasons=admission.reasons,
        )

    if inputs.event_guard.state in {
        EventGuardState.UNKNOWN,
        EventGuardState.SOURCE_UNHEALTHY,
    }:
        return _finish(
            inputs,
            state=RuntimeState.QUARANTINED,
            decision=DecisionKind.NO_ACTION,
            reasons=inputs.event_guard.reasons,
        )
    if not inputs.event_guard.entry_allowed:
        return _finish(
            inputs,
            state=RuntimeState.SHADOW,
            decision=DecisionKind.NO_ACTION,
            reasons=inputs.event_guard.reasons,
        )

    gates = combine_gates(inputs.market_gates)
    if gates.state is GateState.UNKNOWN:
        return _finish(
            inputs,
            state=RuntimeState.QUARANTINED,
            decision=DecisionKind.NO_ACTION,
            reasons=gates.reasons,
        )
    if gates.state is GateState.LOCK:
        return _finish(
            inputs,
            state=RuntimeState.SHADOW,
            decision=DecisionKind.NO_ACTION,
            reasons=gates.reasons,
        )

    if (
        inputs.reconciliation.disposition is not ReconciliationDisposition.CONTINUE
        or inputs.reconciliation.status is not ReconciliationStatus.MATCH_ZERO
    ):
        return _finish(
            inputs,
            state=RuntimeState.QUARANTINED,
            decision=DecisionKind.NO_ACTION,
            reasons=inputs.reconciliation.reason_codes,
        )

    if inputs.risk.disposition is RiskDisposition.QUARANTINE:
        return _finish(
            inputs,
            state=RuntimeState.QUARANTINED,
            decision=DecisionKind.NO_ACTION,
            reasons=inputs.risk.reason_codes,
        )
    if inputs.risk.disposition is RiskDisposition.REJECT:
        return _finish(
            inputs,
            state=RuntimeState.SHADOW,
            decision=DecisionKind.NO_ACTION,
            reasons=inputs.risk.reason_codes,
        )

    if not inputs.analyst.admissible:
        return _finish(
            inputs,
            state=RuntimeState.DEGRADED,
            decision=DecisionKind.NO_ACTION,
            reasons=inputs.analyst.reason_codes,
        )
    if inputs.analyst.decision is AnalystDecision.NO_TRADE:
        return _finish(
            inputs,
            state=RuntimeState.SHADOW,
            decision=DecisionKind.NO_ACTION,
            reasons=inputs.analyst.reason_codes,
        )
    if not inputs.setup_id:
        return _finish(
            inputs,
            state=RuntimeState.QUARANTINED,
            decision=DecisionKind.NO_ACTION,
            reasons=("SETUP_IDENTITY_MISSING",),
        )
    return _finish(
        inputs,
        state=RuntimeState.SHADOW,
        decision=DecisionKind.SETUP,
        reasons=("ALL_EXECUTION_DISABLED_GATES_PASS",),
        setup_id=inputs.setup_id,
    )
