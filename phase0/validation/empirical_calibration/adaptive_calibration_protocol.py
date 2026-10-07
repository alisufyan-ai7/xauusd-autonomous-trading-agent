"""Pure prospective evaluator for the registered R4 adaptive cost trial.

The evaluator has no file, network, broker, model, messaging, process or write
capability. Predictions for each UTC day use only observations strictly before
that day and inside the frozen rolling window.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
from typing import Any


METRICS = ("spread_points", "gap_points", "round_trip_cost_usd")
SESSIONS = ("ASIA", "LONDON", "LONDON_NY", "ROLLOVER")
HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class AdaptiveRow:
    observed_utc: datetime
    session: str
    spread_points: float
    gap_points: float
    round_trip_cost_usd: float

    def __post_init__(self) -> None:
        if (self.observed_utc.tzinfo is None
                or self.observed_utc.utcoffset() != timedelta(0)):
            raise ValueError("UTC timestamp required")
        if self.session not in SESSIONS:
            raise ValueError("invalid session")
        values = (self.spread_points, self.gap_points, self.round_trip_cost_usd)
        if any(not math.isfinite(value) or value < 0 for value in values):
            raise ValueError("finite non-negative metrics required")


@dataclass(frozen=True)
class AdaptivePlan:
    schema_version: str
    bundle_root_sha256: str
    registered_utc: datetime
    development_cutoff_utc: datetime
    evaluation_start_utc: datetime
    evaluation_end_utc: datetime
    lookback_days: int
    quantile_probability: float
    minimum_history_rows_per_session: int
    minimum_evaluation_rows: int
    minimum_evaluation_rows_per_session: int
    minimum_overall_coverage: float
    minimum_session_coverage: float
    daily_freeze_utc_hour: int
    external_python_trading_disabled: bool
    trading_authorized: bool
    registration_sha256: str


@dataclass(frozen=True)
class AdaptiveResult:
    status: str
    reason_codes: tuple[str, ...]
    evaluated_rows: int
    overall_coverage: tuple[tuple[str, float], ...]
    session_coverage: tuple[tuple[str, str, float], ...]


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def plan_payload(plan: AdaptivePlan) -> dict[str, Any]:
    value = asdict(plan)
    for name in ("registered_utc", "development_cutoff_utc",
                 "evaluation_start_utc", "evaluation_end_utc"):
        value[name] = getattr(plan, name).isoformat().replace("+00:00", "Z")
    value.pop("registration_sha256")
    return value


def plan_hash(plan: AdaptivePlan) -> str:
    return hashlib.sha256(canonical(plan_payload(plan))).hexdigest()


def _nearest_rank(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    index = math.ceil(probability * len(ordered)) - 1
    return ordered[max(0, min(index, len(ordered) - 1))]


def _ordered_unique(rows: tuple[AdaptiveRow, ...]) -> bool:
    stamps = [row.observed_utc for row in rows]
    return stamps == sorted(stamps) and len(stamps) == len(set(stamps))


def _plan_reasons(plan: AdaptivePlan) -> list[str]:
    reasons: list[str] = []
    if plan.schema_version != "adaptive-cost-calibration-1.0":
        reasons.append("SCHEMA_INVALID")
    if (not HEX.fullmatch(plan.bundle_root_sha256)
            or not HEX.fullmatch(plan.registration_sha256)
            or plan.registration_sha256 != plan_hash(plan)):
        reasons.append("REGISTRATION_BINDING_INVALID")
    times = (plan.registered_utc, plan.development_cutoff_utc,
             plan.evaluation_start_utc, plan.evaluation_end_utc)
    if any(value.tzinfo is None or value.utcoffset() != timedelta(0)
           for value in times):
        reasons.append("PLAN_TIME_INVALID")
    elif not (plan.development_cutoff_utc < plan.registered_utc
              < plan.evaluation_start_utc < plan.evaluation_end_utc):
        reasons.append("PROSPECTIVE_CHRONOLOGY_INVALID")
    if (plan.lookback_days != 56 or plan.quantile_probability != 0.995
            or plan.minimum_history_rows_per_session != 500
            or plan.minimum_evaluation_rows != 2500
            or plan.minimum_evaluation_rows_per_session != 300
            or plan.minimum_overall_coverage != 0.99
            or plan.minimum_session_coverage != 0.985
            or plan.daily_freeze_utc_hour != 0):
        reasons.append("FROZEN_POLICY_INVALID")
    if (plan.external_python_trading_disabled is not True
            or plan.trading_authorized is not False):
        reasons.append("TRADING_BOUNDARY_INVALID")
    return reasons


def evaluate_adaptive_trial(
    plan: AdaptivePlan,
    development: tuple[AdaptiveRow, ...],
    evaluation: tuple[AdaptiveRow, ...],
) -> AdaptiveResult:
    reasons = _plan_reasons(plan)
    if not _ordered_unique(development) or not _ordered_unique(evaluation):
        reasons.append("ROW_CHRONOLOGY_INVALID")
    if any(row.observed_utc > plan.development_cutoff_utc for row in development):
        reasons.append("DEVELOPMENT_CUTOFF_VIOLATION")
    if any(not plan.evaluation_start_utc <= row.observed_utc <= plan.evaluation_end_utc
           for row in evaluation):
        reasons.append("EVALUATION_WINDOW_VIOLATION")
    if set(row.observed_utc for row in development) & set(
            row.observed_utc for row in evaluation):
        reasons.append("PARTITION_OVERLAP")
    if len(evaluation) < plan.minimum_evaluation_rows:
        reasons.append("EVALUATION_SAMPLE_INSUFFICIENT")
    for session in SESSIONS:
        if sum(row.session == session for row in evaluation) \
                < plan.minimum_evaluation_rows_per_session:
            reasons.append(f"{session}_EVALUATION_SAMPLE_INSUFFICIENT")
    if reasons:
        return AdaptiveResult("FAIL_CLOSED", tuple(dict.fromkeys(reasons)), 0, (), ())

    successes = {metric: 0 for metric in METRICS}
    session_successes = {(session, metric): 0 for session in SESSIONS for metric in METRICS}
    session_totals = {session: 0 for session in SESSIONS}
    evaluated = 0
    prior_evaluation: list[AdaptiveRow] = []
    day_groups: dict[datetime, list[AdaptiveRow]] = {}
    for row in evaluation:
        day = row.observed_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        day_groups.setdefault(day, []).append(row)

    for day in sorted(day_groups):
        lower = day - timedelta(days=plan.lookback_days)
        eligible = [row for row in development if lower <= row.observed_utc < day]
        eligible.extend(row for row in prior_evaluation if lower <= row.observed_utc < day)
        thresholds: dict[tuple[str, str], float] = {}
        for session in SESSIONS:
            pool = [row for row in eligible if row.session == session]
            if len(pool) < plan.minimum_history_rows_per_session:
                reasons.append(f"{session}_HISTORY_SAMPLE_INSUFFICIENT")
                continue
            for metric in METRICS:
                thresholds[(session, metric)] = _nearest_rank(
                    [getattr(row, metric) for row in pool], plan.quantile_probability)
        if reasons:
            break
        for row in day_groups[day]:
            evaluated += 1
            session_totals[row.session] += 1
            for metric in METRICS:
                if getattr(row, metric) <= thresholds[(row.session, metric)]:
                    successes[metric] += 1
                    session_successes[(row.session, metric)] += 1
        prior_evaluation.extend(day_groups[day])

    if reasons:
        return AdaptiveResult("FAIL_CLOSED", tuple(dict.fromkeys(reasons)), evaluated, (), ())
    overall = tuple((metric, successes[metric] / evaluated) for metric in METRICS)
    by_session = tuple(
        (session, metric, session_successes[(session, metric)] / session_totals[session])
        for session in SESSIONS for metric in METRICS
    )
    if any(value < plan.minimum_overall_coverage for _, value in overall):
        reasons.append("OVERALL_COVERAGE_REJECTED")
    if any(value < plan.minimum_session_coverage for _, _, value in by_session):
        reasons.append("SESSION_COVERAGE_REJECTED")
    status = "VALIDATED_NON_TRADING" if not reasons else "REJECTED"
    return AdaptiveResult(status, tuple(dict.fromkeys(reasons)), evaluated, overall, by_session)
