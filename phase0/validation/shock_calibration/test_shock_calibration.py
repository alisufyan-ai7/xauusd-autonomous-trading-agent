from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shock_calibration import (
    DatasetManifest, FeatureRow, NormalizationGate, ShockConfig,
    assess_admission, calibrate_candidate, dataset_digest, is_abnormal,
)

UTC = timezone.utc


def row(index: int, *, shock=False, event_phase="NORMAL", spread=None) -> FeatureRow:
    return FeatureRow(
        datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=index),
        "LONDON_NY", event_phase, spread if spread is not None else 10 + index % 3, 10,
        2 + index % 2, 2, 3 + index % 2, 3, 100 + index % 5, 50 + index % 4,
        shock,
    )


def manifest(rows, cutoff_index=29, **overrides):
    values = dict(
        dataset_id="licensed-derived-xauusd-v1", dataset_sha256=dataset_digest(rows),
        rights_status="ADMITTED", immutable=True, derived_features_only=True,
        train_end_utc=rows[cutoff_index].observed_utc,
        minimum_train_rows=30, minimum_validation_rows=10,
    )
    values.update(overrides)
    return DatasetManifest(**values)


def config(**overrides):
    values = dict(
        spread_absolute_points=20, spread_relative_multiple=2,
        return_absolute_bps=10, return_relative_multiple=5,
        range_absolute_bps=15, range_relative_multiple=5,
        quote_gap_max_ms=500, tick_staleness_max_ms=1000,
        baseline_minimum_samples=20, minimum_shock_hold_seconds=60,
        normalization_seconds=120, repeated_trip_window_seconds=600,
        repeated_trip_count=3,
    )
    values.update(overrides)
    return ShockConfig(**values)


class ShockCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.rows = tuple(row(index, shock=index >= 35, spread=30 if index >= 35 else None)
                          for index in range(40))

    def test_missing_manifest_and_empty_data_fail_closed(self):
        result = calibrate_candidate(None, ())
        self.assertEqual("FAIL_CLOSED", result.status)
        self.assertEqual(("MANIFEST_MISSING",), result.reasons)

    def test_rights_immutability_and_derived_only_are_required(self):
        bad = manifest(self.rows, rights_status="UNKNOWN", immutable=False,
                       derived_features_only=False)
        admitted, reasons = assess_admission(bad, self.rows)
        self.assertFalse(admitted)
        self.assertEqual(
            {"RIGHTS_NOT_ADMITTED", "DATASET_NOT_IMMUTABLE", "RAW_DATA_NOT_ADMITTED"},
            set(reasons),
        )

    def test_hash_tamper_and_nonchronological_rows_fail(self):
        reversed_rows = tuple(reversed(self.rows))
        admitted, reasons = assess_admission(manifest(self.rows), reversed_rows)
        self.assertFalse(admitted)
        self.assertIn("DATASET_HASH_MISMATCH", reasons)
        self.assertIn("NOT_STRICTLY_CHRONOLOGICAL", reasons)

    def test_training_baseline_rejects_event_contamination(self):
        contaminated = (replace(self.rows[0], event_phase="POST_EVENT"),) + self.rows[1:]
        admitted, reasons = assess_admission(manifest(contaminated), contaminated)
        self.assertFalse(admitted)
        self.assertIn("TRAINING_BASELINE_CONTAMINATED", reasons)

    def test_zero_robust_baseline_is_rejected_before_calibration(self):
        invalid = (replace(self.rows[0], spread_baseline_points=0),) + self.rows[1:]
        admitted, reasons = assess_admission(manifest(invalid), invalid)
        self.assertFalse(admitted)
        self.assertIn("BASELINE_INVALID", reasons)

    def test_candidate_is_training_only_and_never_runtime_ready(self):
        first = calibrate_candidate(manifest(self.rows), self.rows)
        altered = self.rows[:30] + tuple(replace(item, spread_points=1000) for item in self.rows[30:])
        second = calibrate_candidate(manifest(altered), altered)
        self.assertEqual("CANDIDATE_ONLY", first.status)
        self.assertEqual(first.candidate, second.candidate)
        self.assertEqual(0, first.candidate.normalization_seconds)

    def test_candidate_reports_untouched_validation_metrics(self):
        result = calibrate_candidate(manifest(self.rows), self.rows)
        self.assertEqual(30, result.training_rows)
        self.assertEqual(10, result.validation_rows)
        self.assertIsNotNone(result.false_lock_rate)
        self.assertIsNotNone(result.missed_shock_rate)

    def test_missing_baseline_and_exact_threshold_lock(self):
        normal = row(50)
        self.assertTrue(is_abnormal(normal, config(), 19))
        exact = replace(normal, spread_points=20)
        self.assertTrue(is_abnormal(exact, config(), 20))

    def test_shock_lock_is_independent_of_scheduled_event(self):
        gate = NormalizationGate(config())
        shock = row(50, spread=30)
        self.assertEqual("SHOCK_LOCK", gate.step(shock, baseline_samples=20,
                                                 scheduled_lock_active=False))

    def test_release_requires_hold_and_sustained_normalization(self):
        gate = NormalizationGate(config())
        shock = row(50, spread=30)
        self.assertEqual("SHOCK_LOCK", gate.step(shock, baseline_samples=20))
        self.assertEqual("NORMALIZATION_PENDING", gate.step(row(51), baseline_samples=20))
        self.assertEqual("NORMALIZATION_PENDING", gate.step(row(52), baseline_samples=20))
        self.assertEqual("HEALTHY", gate.step(row(53), baseline_samples=20))

    def test_scheduled_post_event_lock_prevents_normalization_release(self):
        gate = NormalizationGate(config())
        gate.step(row(50, spread=30), baseline_samples=20)
        self.assertEqual("NORMALIZATION_PENDING", gate.step(
            row(51, event_phase="POST_EVENT"), baseline_samples=20,
            scheduled_lock_active=True,
        ))

    def test_repeated_shocks_escalate_to_quarantine(self):
        gate = NormalizationGate(config(normalization_seconds=30))
        for index in (50, 53):
            self.assertEqual("SHOCK_LOCK", gate.step(row(index, spread=30), baseline_samples=20))
            self.assertEqual("NORMALIZATION_PENDING", gate.step(row(index + 1), baseline_samples=20))
            self.assertEqual("HEALTHY", gate.step(row(index + 2), baseline_samples=20))
        self.assertEqual("QUARANTINE", gate.step(row(56, spread=30), baseline_samples=20))

    def test_unfrozen_candidate_cannot_construct_runtime_gate(self):
        candidate = calibrate_candidate(manifest(self.rows), self.rows).candidate
        with self.assertRaises(ValueError):
            NormalizationGate(candidate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
