"""Prospective, non-trading empirical calibration workflow.

The workflow consumes caller-supplied derived observations from an admitted
immutable bundle.  It produces training-only candidates for shock detection,
post-event normalization, and adverse spread/slippage-proxy/gap/cost stresses.
It cannot read raw market data, call a provider, contact MT5, write files, send
messages or authorize runtime constants.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
from typing import Any


HEX = re.compile(r"^[0-9a-f]{64}$")
SESSIONS = ("ASIA", "LONDON", "LONDON_NY", "ROLLOVER")
PHASES = ("NORMAL", "EVENT", "POST_EVENT")


@dataclass(frozen=True)
class Observation:
    observed_utc: datetime
    partition: str
    session: str
    event_phase: str
    event_id: str | None
    spread_points: float
    spread_baseline_points: float
    adverse_latency_move_points: float
    gap_points: float
    absolute_return_bps: float
    return_baseline_bps: float
    range_bps: float
    range_baseline_bps: float
    quote_gap_ms: float
    tick_age_ms: float
    round_trip_cost_usd: float

    def __post_init__(self) -> None:
        if self.observed_utc.tzinfo is None or self.observed_utc.utcoffset() != timedelta(0):
            raise ValueError("UTC timestamp required")
        if self.partition not in {"TRAIN", "VALIDATION", "HOLDOUT"}:
            raise ValueError("invalid partition")
        if self.session not in SESSIONS or self.event_phase not in PHASES:
            raise ValueError("invalid stratum")
        if self.event_phase in {"EVENT", "POST_EVENT"} and not self.event_id:
            raise ValueError("event and post-event rows require event_id")
        numeric = (
            self.spread_points, self.spread_baseline_points,
            self.adverse_latency_move_points, self.gap_points,
            self.absolute_return_bps, self.return_baseline_bps,
            self.range_bps, self.range_baseline_bps, self.quote_gap_ms,
            self.tick_age_ms, self.round_trip_cost_usd,
        )
        if any(not math.isfinite(value) or value < 0 for value in numeric):
            raise ValueError("finite non-negative values required")
        if min(self.spread_baseline_points, self.return_baseline_bps,
               self.range_baseline_bps) <= 0:
            raise ValueError("positive baselines required")


@dataclass(frozen=True)
class CalibrationPlan:
    bundle_root_sha256: str
    derived_dataset_sha256: str
    rights_status: str
    frozen_utc: datetime
    train_end_utc: datetime
    holdout_status: str
    minimum_rows_per_session: int
    minimum_post_event_rows: int
    minimum_complete_events: int
    quantile_probability: float
    normalization_ratio_limit: float
    consecutive_normal_rows: int
    max_post_event_gap_seconds: int
    code_sha256: str
    split_map_sha256: str


@dataclass(frozen=True)
class CandidateArtifact:
    spread_points: float
    slippage_proxy_points: float
    gap_points: float
    round_trip_cost_usd: float
    return_bps: float
    range_bps: float
    quote_gap_ms: float
    tick_age_ms: float
    post_event_normalization_seconds: int
    slippage_basis: str
    artifact_sha256: str


@dataclass(frozen=True)
class WorkflowResult:
    status: str
    reason_codes: tuple[str, ...]
    training_rows: int
    validation_rows: int
    complete_post_events: int
    candidate: CandidateArtifact | None


def canonical_rows(rows: tuple[Observation, ...]) -> bytes:
    values = []
    for row in rows:
        value = asdict(row)
        value["observed_utc"] = row.observed_utc.isoformat().replace("+00:00", "Z")
        values.append(value)
    return json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")


def rows_hash(rows: tuple[Observation, ...]) -> str:
    return hashlib.sha256(canonical_rows(rows)).hexdigest()


def artifact_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    index = math.ceil(probability * len(ordered)) - 1
    return ordered[max(0, min(index, len(ordered) - 1))]


def _complete_recoveries(
    rows: tuple[Observation, ...], *, ratio_limit: float, consecutive: int,
    max_gap_seconds: int,
) -> tuple[list[int], list[str]]:
    markers: dict[str, list[datetime]] = {}
    by_event: dict[str, list[Observation]] = {}
    for row in rows:
        if row.event_phase == "EVENT" and row.event_id:
            markers.setdefault(row.event_id, []).append(row.observed_utc)
        if row.event_phase == "POST_EVENT" and row.event_id:
            by_event.setdefault(row.event_id, []).append(row)
    durations: list[int] = []
    reasons: list[str] = []
    for event_id, event_rows in by_event.items():
        event_rows.sort(key=lambda item: item.observed_utc)
        event_markers = markers.get(event_id, [])
        if len(event_markers) != 1:
            reasons.append("EVENT_MARKER_MISSING_OR_DUPLICATE")
            continue
        start = event_markers[0]
        first_gap = (event_rows[0].observed_utc - start).total_seconds()
        if first_gap <= 0:
            reasons.append("POST_EVENT_NOT_AFTER_EVENT")
            continue
        if first_gap > max_gap_seconds:
            reasons.append("POST_EVENT_INITIAL_GAP")
            continue
        streak = 0
        previous: datetime | None = start
        for row in event_rows:
            if previous is not None \
                    and (row.observed_utc - previous).total_seconds() > max_gap_seconds:
                # Missing observations cannot prove continuous normalization.
                break
            previous = row.observed_utc
            normal = (
                row.spread_points / row.spread_baseline_points <= ratio_limit
                and row.absolute_return_bps / row.return_baseline_bps <= ratio_limit
                and row.range_bps / row.range_baseline_bps <= ratio_limit
            )
            streak = streak + 1 if normal else 0
            if streak >= consecutive:
                durations.append(int((row.observed_utc - start).total_seconds()))
                break
    return durations, reasons


def calibrate(plan: CalibrationPlan, rows: tuple[Observation, ...]) -> WorkflowResult:
    reasons: list[str] = []
    if any(not HEX.fullmatch(value) for value in (
        plan.bundle_root_sha256, plan.derived_dataset_sha256,
        plan.code_sha256, plan.split_map_sha256,
    )):
        reasons.append("HASH_BINDING_INVALID")
    if rows_hash(rows) != plan.derived_dataset_sha256:
        reasons.append("DATASET_HASH_MISMATCH")
    if plan.rights_status != "ADMITTED" or plan.holdout_status != "SEALED_UNVIEWED":
        reasons.append("RIGHTS_OR_HOLDOUT_INVALID")
    if (plan.frozen_utc.tzinfo is None or plan.frozen_utc.utcoffset() != timedelta(0)
            or plan.train_end_utc.tzinfo is None
            or plan.train_end_utc.utcoffset() != timedelta(0)
            or plan.frozen_utc > plan.train_end_utc):
        reasons.append("FREEZE_CHRONOLOGY_INVALID")
    if (plan.minimum_rows_per_session < 1 or plan.minimum_post_event_rows < 1
            or plan.minimum_complete_events < 1 or plan.consecutive_normal_rows < 1
            or plan.max_post_event_gap_seconds < 1
            or not 0.5 < plan.quantile_probability < 1
            or plan.normalization_ratio_limit <= 1):
        reasons.append("CALIBRATION_POLICY_INVALID")
    times = [row.observed_utc for row in rows]
    if not rows or times != sorted(times) or len(times) != len(set(times)):
        reasons.append("CHRONOLOGY_INVALID")
    if any(row.partition == "HOLDOUT" for row in rows):
        reasons.append("HOLDOUT_EXPOSED")
    training = tuple(row for row in rows if row.partition == "TRAIN")
    validation = tuple(row for row in rows if row.partition == "VALIDATION")
    if any(row.observed_utc > plan.train_end_utc for row in training):
        reasons.append("TRAIN_CUTOFF_VIOLATION")
    if any(row.observed_utc <= plan.train_end_utc for row in validation):
        reasons.append("VALIDATION_BEFORE_TRAIN_CUTOFF")
    for session in SESSIONS:
        if sum(row.session == session and row.event_phase == "NORMAL" for row in training) \
                < plan.minimum_rows_per_session:
            reasons.append(f"{session}_BASELINE_INSUFFICIENT")
    post_rows = tuple(row for row in training if row.event_phase == "POST_EVENT")
    if len(post_rows) < plan.minimum_post_event_rows:
        reasons.append("POST_EVENT_SAMPLE_INSUFFICIENT")
    recoveries, recovery_reasons = _complete_recoveries(
        training, ratio_limit=plan.normalization_ratio_limit,
        consecutive=plan.consecutive_normal_rows,
        max_gap_seconds=plan.max_post_event_gap_seconds,
    )
    reasons.extend(recovery_reasons)
    if len(recoveries) < plan.minimum_complete_events:
        reasons.append("COMPLETE_EVENT_RECOVERY_INSUFFICIENT")
    if reasons:
        return WorkflowResult("FAIL_CLOSED", tuple(dict.fromkeys(reasons)),
                              len(training), len(validation), len(recoveries), None)

    normal = [row for row in training if row.event_phase == "NORMAL"]
    q = plan.quantile_probability
    values = {
        "spread_points": _quantile([row.spread_points for row in normal], q),
        "slippage_proxy_points": _quantile(
            [row.adverse_latency_move_points for row in training], q),
        "gap_points": _quantile([row.gap_points for row in training], q),
        "round_trip_cost_usd": _quantile([row.round_trip_cost_usd for row in training], q),
        "return_bps": _quantile([row.absolute_return_bps for row in normal], q),
        "range_bps": _quantile([row.range_bps for row in normal], q),
        "quote_gap_ms": _quantile([row.quote_gap_ms for row in training], q),
        "tick_age_ms": _quantile([row.tick_age_ms for row in training], q),
        "post_event_normalization_seconds": int(_quantile([float(x) for x in recoveries], q)),
        "slippage_basis": "NON_TRADING_ADVERSE_LATENCY_PROXY",
    }
    candidate = CandidateArtifact(**values, artifact_sha256=artifact_hash(values))
    return WorkflowResult(
        "CANDIDATE_ONLY",
        ("INDEPENDENT_REVIEW_AND_VALIDATION_REQUIRED", "NO_EXECUTION_SLIPPAGE_CLAIM"),
        len(training), len(validation), len(recoveries), candidate,
    )
