"""Fail-closed session, holiday, and abnormal-shock gates."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from xauusd_agent.market.models import _require_utc


class GateState(StrEnum):
    CLEAR = "CLEAR"
    LOCK = "LOCK"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class GateDecision:
    state: GateState
    reasons: tuple[str, ...]

    @property
    def clear(self) -> bool:
        return self.state is GateState.CLEAR


@dataclass(frozen=True, slots=True)
class SessionObservation:
    observed_utc: datetime
    schedule_current: bool | None
    weekly_boundary_known: bool | None
    holiday_override_known: bool | None
    scheduled_open: bool | None
    broker_reports_open: bool | None
    seconds_to_break: int | None
    required_buffer_seconds: int

    def __post_init__(self) -> None:
        _require_utc(self.observed_utc, "observed_utc")
        if self.required_buffer_seconds < 0:
            raise ValueError("required buffer cannot be negative")


@dataclass(frozen=True, slots=True)
class ShockObservation:
    observed_utc: datetime
    calibration_available: bool | None
    quote_fresh: bool | None
    metric_complete: bool | None
    shock_detected: bool | None
    normalized: bool | None
    normalization_samples: int | None
    required_normalization_samples: int = 3

    def __post_init__(self) -> None:
        _require_utc(self.observed_utc, "observed_utc")
        if self.required_normalization_samples <= 0:
            raise ValueError("required normalization samples must be positive")


def evaluate_session_gate(observation: SessionObservation) -> GateDecision:
    unknown: list[str] = []
    for reason, value in (
        ("SCHEDULE_CURRENCY_UNKNOWN", observation.schedule_current),
        ("WEEKLY_BOUNDARY_UNKNOWN", observation.weekly_boundary_known),
        ("HOLIDAY_OVERRIDE_UNKNOWN", observation.holiday_override_known),
        ("SCHEDULED_STATE_UNKNOWN", observation.scheduled_open),
        ("BROKER_STATE_UNKNOWN", observation.broker_reports_open),
    ):
        if value is None:
            unknown.append(reason)
    if observation.seconds_to_break is None:
        unknown.append("TIME_TO_BREAK_UNKNOWN")
    if unknown:
        return GateDecision(GateState.UNKNOWN, tuple(unknown))
    if observation.schedule_current is not True:
        return GateDecision(GateState.UNKNOWN, ("SCHEDULE_STALE",))
    if (
        observation.weekly_boundary_known is not True
        or observation.holiday_override_known is not True
    ):
        return GateDecision(GateState.UNKNOWN, ("SESSION_OR_HOLIDAY_EVIDENCE_INCOMPLETE",))
    if observation.scheduled_open != observation.broker_reports_open:
        return GateDecision(GateState.LOCK, ("BROKER_SCHEDULE_DISAGREEMENT",))
    if observation.scheduled_open is not True:
        return GateDecision(GateState.LOCK, ("SESSION_CLOSED",))
    assert observation.seconds_to_break is not None
    if observation.seconds_to_break < observation.required_buffer_seconds:
        return GateDecision(GateState.LOCK, ("INSUFFICIENT_TIME_TO_SESSION_BREAK",))
    return GateDecision(GateState.CLEAR, ())


def evaluate_shock_gate(observation: ShockObservation) -> GateDecision:
    unknown: list[str] = []
    for reason, value in (
        ("CALIBRATION_STATE_UNKNOWN", observation.calibration_available),
        ("QUOTE_FRESHNESS_UNKNOWN", observation.quote_fresh),
        ("SHOCK_METRICS_UNKNOWN", observation.metric_complete),
        ("SHOCK_STATE_UNKNOWN", observation.shock_detected),
        ("NORMALIZATION_STATE_UNKNOWN", observation.normalized),
    ):
        if value is None:
            unknown.append(reason)
    if observation.normalization_samples is None:
        unknown.append("NORMALIZATION_SAMPLE_COUNT_UNKNOWN")
    if unknown:
        return GateDecision(GateState.UNKNOWN, tuple(unknown))
    if observation.calibration_available is not True:
        return GateDecision(GateState.UNKNOWN, ("CALIBRATION_UNAVAILABLE",))
    if observation.quote_fresh is not True or observation.metric_complete is not True:
        return GateDecision(GateState.UNKNOWN, ("SHOCK_INPUT_INCOMPLETE",))
    if observation.shock_detected is True:
        return GateDecision(GateState.LOCK, ("ABNORMAL_SHOCK",))
    assert observation.normalization_samples is not None
    if (
        observation.normalized is not True
        or observation.normalization_samples < observation.required_normalization_samples
    ):
        return GateDecision(GateState.LOCK, ("NORMALIZATION_PENDING",))
    return GateDecision(GateState.CLEAR, ())


def combine_gates(decisions: Sequence[GateDecision]) -> GateDecision:
    if not decisions:
        return GateDecision(GateState.UNKNOWN, ("NO_GATE_DECISIONS",))
    reasons = tuple(reason for decision in decisions for reason in decision.reasons)
    if any(decision.state is GateState.LOCK for decision in decisions):
        return GateDecision(GateState.LOCK, tuple(dict.fromkeys(reasons)))
    if any(decision.state is GateState.UNKNOWN for decision in decisions):
        return GateDecision(GateState.UNKNOWN, tuple(dict.fromkeys(reasons)))
    return GateDecision(GateState.CLEAR, ())
