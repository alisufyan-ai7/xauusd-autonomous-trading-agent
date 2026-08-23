"""Fail-closed empirical calibration scaffold for the independent shock guard.

Only minimized, derived analytical rows are accepted. Candidate thresholds are
research output and cannot authorize a runtime or a trade.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re

UTC = timezone.utc
SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class FeatureRow:
    observed_utc: datetime
    session: str
    event_phase: str
    spread_points: float
    spread_baseline_points: float
    absolute_return_bps: float
    return_baseline_bps: float
    range_bps: float
    range_baseline_bps: float
    quote_gap_ms: float
    tick_age_ms: float
    known_shock: bool = False

    def __post_init__(self) -> None:
        if self.observed_utc.tzinfo is None or self.observed_utc.utcoffset() != timedelta(0):
            raise ValueError("observed_utc must be timezone-aware UTC")
        if self.event_phase not in {"NORMAL", "PRE_EVENT", "EVENT", "POST_EVENT"}:
            raise ValueError("invalid event phase")
        values = (
            self.spread_points, self.spread_baseline_points, self.absolute_return_bps,
            self.return_baseline_bps, self.range_bps, self.range_baseline_bps,
            self.quote_gap_ms, self.tick_age_ms,
        )
        if any(not math.isfinite(value) or value < 0 for value in values):
            raise ValueError("features must be finite and non-negative")


@dataclass(frozen=True)
class DatasetManifest:
    dataset_id: str
    dataset_sha256: str
    rights_status: str
    immutable: bool
    derived_features_only: bool
    train_end_utc: datetime
    minimum_train_rows: int
    minimum_validation_rows: int


@dataclass(frozen=True)
class ShockConfig:
    spread_absolute_points: float
    spread_relative_multiple: float
    return_absolute_bps: float
    return_relative_multiple: float
    range_absolute_bps: float
    range_relative_multiple: float
    quote_gap_max_ms: float
    tick_staleness_max_ms: float
    baseline_minimum_samples: int
    minimum_shock_hold_seconds: int
    normalization_seconds: int
    repeated_trip_window_seconds: int
    repeated_trip_count: int


@dataclass(frozen=True)
class CalibrationResult:
    status: str
    reasons: tuple[str, ...]
    training_rows: int
    validation_rows: int
    candidate: ShockConfig | None
    false_lock_rate: float | None
    missed_shock_rate: float | None


def canonical_rows(rows: tuple[FeatureRow, ...]) -> bytes:
    values = []
    for row in rows:
        value = asdict(row)
        value["observed_utc"] = row.observed_utc.isoformat().replace("+00:00", "Z")
        values.append(value)
    return json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")


def dataset_digest(rows: tuple[FeatureRow, ...]) -> str:
    return hashlib.sha256(canonical_rows(rows)).hexdigest()


def assess_admission(manifest: DatasetManifest | None,
                     rows: tuple[FeatureRow, ...]) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if manifest is None:
        return False, ("MANIFEST_MISSING",)
    if not rows:
        reasons.append("DATASET_EMPTY")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", manifest.dataset_id):
        reasons.append("DATASET_ID_INVALID")
    if not SHA256.fullmatch(manifest.dataset_sha256):
        reasons.append("DATASET_HASH_INVALID")
    elif dataset_digest(rows) != manifest.dataset_sha256:
        reasons.append("DATASET_HASH_MISMATCH")
    if manifest.rights_status != "ADMITTED":
        reasons.append("RIGHTS_NOT_ADMITTED")
    if not manifest.immutable:
        reasons.append("DATASET_NOT_IMMUTABLE")
    if not manifest.derived_features_only:
        reasons.append("RAW_DATA_NOT_ADMITTED")
    if (manifest.train_end_utc.tzinfo is None
            or manifest.train_end_utc.utcoffset() != timedelta(0)):
        reasons.append("TRAIN_CUTOFF_INVALID")
    if manifest.minimum_train_rows < 1 or manifest.minimum_validation_rows < 1:
        reasons.append("MINIMUM_SAMPLE_POLICY_INVALID")
    timestamps = [row.observed_utc for row in rows]
    if timestamps != sorted(timestamps) or len(set(timestamps)) != len(timestamps):
        reasons.append("NOT_STRICTLY_CHRONOLOGICAL")
    training = [row for row in rows if row.observed_utc <= manifest.train_end_utc]
    validation = [row for row in rows if row.observed_utc > manifest.train_end_utc]
    if len(training) < manifest.minimum_train_rows:
        reasons.append("TRAINING_SAMPLE_INSUFFICIENT")
    if len(validation) < manifest.minimum_validation_rows:
        reasons.append("VALIDATION_SAMPLE_INSUFFICIENT")
    if any(row.event_phase != "NORMAL" for row in training):
        reasons.append("TRAINING_BASELINE_CONTAMINATED")
    if any(min(row.spread_baseline_points, row.return_baseline_bps,
               row.range_baseline_bps) <= 0 for row in rows):
        reasons.append("BASELINE_INVALID")
    return not reasons, tuple(sorted(set(reasons)))


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("empty quantile")
    index = math.ceil(probability * len(ordered)) - 1
    return ordered[max(0, min(index, len(ordered) - 1))]


def is_abnormal(row: FeatureRow, config: ShockConfig,
                baseline_samples: int) -> bool:
    """Exact-boundary values are unsafe; missing baselines never relax a limit."""
    if baseline_samples < config.baseline_minimum_samples:
        return True
    if min(row.spread_baseline_points, row.return_baseline_bps,
           row.range_baseline_bps) <= 0:
        return True
    return any((
        row.spread_points >= config.spread_absolute_points,
        row.spread_points / row.spread_baseline_points >= config.spread_relative_multiple,
        row.absolute_return_bps >= config.return_absolute_bps,
        row.absolute_return_bps / row.return_baseline_bps >= config.return_relative_multiple,
        row.range_bps >= config.range_absolute_bps,
        row.range_bps / row.range_baseline_bps >= config.range_relative_multiple,
        row.quote_gap_ms >= config.quote_gap_max_ms,
        row.tick_age_ms >= config.tick_staleness_max_ms,
    ))


def calibrate_candidate(manifest: DatasetManifest | None,
                        rows: tuple[FeatureRow, ...]) -> CalibrationResult:
    admitted, reasons = assess_admission(manifest, rows)
    if not admitted or manifest is None:
        return CalibrationResult("FAIL_CLOSED", reasons, 0, 0, None, None, None)
    training = tuple(row for row in rows if row.observed_utc <= manifest.train_end_utc)
    validation = tuple(row for row in rows if row.observed_utc > manifest.train_end_utc)

    # 99th-percentile candidate generation is prospective and training-only.
    # Operational hold/release constants deliberately remain zero/unfrozen.
    candidate = ShockConfig(
        spread_absolute_points=_quantile([r.spread_points for r in training], .99),
        spread_relative_multiple=_quantile(
            [r.spread_points / r.spread_baseline_points for r in training], .99),
        return_absolute_bps=_quantile([r.absolute_return_bps for r in training], .99),
        return_relative_multiple=_quantile(
            [r.absolute_return_bps / r.return_baseline_bps for r in training], .99),
        range_absolute_bps=_quantile([r.range_bps for r in training], .99),
        range_relative_multiple=_quantile(
            [r.range_bps / r.range_baseline_bps for r in training], .99),
        quote_gap_max_ms=_quantile([r.quote_gap_ms for r in training], .99),
        tick_staleness_max_ms=_quantile([r.tick_age_ms for r in training], .99),
        baseline_minimum_samples=len(training),
        minimum_shock_hold_seconds=0,
        normalization_seconds=0,
        repeated_trip_window_seconds=0,
        repeated_trip_count=0,
    )
    predicted = [is_abnormal(row, candidate, len(training)) for row in validation]
    negatives = [index for index, row in enumerate(validation) if not row.known_shock]
    positives = [index for index, row in enumerate(validation) if row.known_shock]
    false_rate = (sum(predicted[index] for index in negatives) / len(negatives)) if negatives else None
    missed_rate = (sum(not predicted[index] for index in positives) / len(positives)) if positives else None
    return CalibrationResult(
        "CANDIDATE_ONLY", ("RUNTIME_CONSTANTS_UNFROZEN",), len(training), len(validation),
        candidate, false_rate, missed_rate,
    )


class NormalizationGate:
    """Deterministic replay gate; a candidate with zero constants is rejected."""

    def __init__(self, config: ShockConfig):
        if min(config.minimum_shock_hold_seconds, config.normalization_seconds,
               config.repeated_trip_window_seconds, config.repeated_trip_count) <= 0:
            raise ValueError("all operational release constants must be frozen above zero")
        self.config = config
        self.locked_since: datetime | None = None
        self.normal_since: datetime | None = None
        self.trips: list[datetime] = []

    def step(self, row: FeatureRow, *, baseline_samples: int,
             scheduled_lock_active: bool = False) -> str:
        now = row.observed_utc
        cutoff = now - timedelta(seconds=self.config.repeated_trip_window_seconds)
        self.trips = [trip for trip in self.trips if trip >= cutoff]
        abnormal = is_abnormal(row, self.config, baseline_samples)
        if abnormal:
            if self.locked_since is None:
                self.locked_since = now
                self.trips.append(now)
            self.normal_since = None
            if len(self.trips) >= self.config.repeated_trip_count:
                return "QUARANTINE"
            return "SHOCK_LOCK"
        if scheduled_lock_active:
            self.normal_since = None
            return "NORMALIZATION_PENDING"
        if self.locked_since is not None:
            if self.normal_since is None:
                self.normal_since = now
            hold_complete = now - self.locked_since >= timedelta(
                seconds=self.config.minimum_shock_hold_seconds
            )
            normalized = now - self.normal_since >= timedelta(
                seconds=self.config.normalization_seconds
            )
            if not (hold_complete and normalized):
                return "NORMALIZATION_PENDING"
            self.locked_since = None
            self.normal_since = None
        return "HEALTHY"
