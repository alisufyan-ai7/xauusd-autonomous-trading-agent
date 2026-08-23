from __future__ import annotations

import ast
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from calibration_workflow import (
    CalibrationPlan, Observation, SESSIONS, artifact_hash, calibrate, rows_hash,
)


UTC = timezone.utc
H = "2" * 64


def make_rows():
    rows = []
    start = datetime(2025, 1, 1, tzinfo=UTC)
    index = 0
    for session in SESSIONS:
        for sample in range(5):
            rows.append(Observation(
                start + timedelta(minutes=index), "TRAIN", session, "NORMAL", None,
                10 + sample, 10, 1 + sample / 10, 0.5 + sample / 10,
                2 + sample / 10, 2, 3 + sample / 10, 3,
                100 + sample, 50 + sample, 0.4 + sample / 100,
            ))
            index += 1
    for event in range(2):
        rows.append(Observation(
            start + timedelta(minutes=index), "TRAIN", "LONDON_NY", "EVENT",
            f"event-{event}", 30, 10, 1, 1, 6, 2, 9, 3, 150, 80, .5,
        ))
        index += 1
        for sample, ratio in enumerate((3.0, 1.4, 1.3, 1.2)):
            rows.append(Observation(
                start + timedelta(minutes=index), "TRAIN", "LONDON_NY", "POST_EVENT",
                f"event-{event}", 10 * ratio, 10, 1 + sample / 10, 1 + sample / 10,
                2 * ratio, 2, 3 * ratio, 3, 120 + sample, 60 + sample, .5,
            ))
            index += 1
    for sample in range(4):
        rows.append(Observation(
            start + timedelta(minutes=index), "VALIDATION", "LONDON", "EVENT", "v-event",
            20, 10, 2, 2, 5, 2, 6, 3, 200, 80, .6,
        ))
        index += 1
    return tuple(rows)


def make_plan(rows):
    return CalibrationPlan(
        bundle_root_sha256=H, derived_dataset_sha256=rows_hash(rows),
        rights_status="ADMITTED", frozen_utc=datetime(2024, 12, 1, tzinfo=UTC),
        train_end_utc=datetime(2025, 1, 1, 0, 29, tzinfo=UTC),
        holdout_status="SEALED_UNVIEWED", minimum_rows_per_session=5,
        minimum_post_event_rows=8, minimum_complete_events=2,
        quantile_probability=.99, normalization_ratio_limit=1.5,
        consecutive_normal_rows=3, max_post_event_gap_seconds=60,
        code_sha256=H, split_map_sha256=H,
    )


class CalibrationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.rows = make_rows()
        self.plan = make_plan(self.rows)

    def test_complete_workflow_is_candidate_only(self):
        result = calibrate(self.plan, self.rows)
        self.assertEqual("CANDIDATE_ONLY", result.status)
        self.assertEqual(2, result.complete_post_events)
        self.assertEqual("NON_TRADING_ADVERSE_LATENCY_PROXY",
                         result.candidate.slippage_basis)
        self.assertEqual(240, result.candidate.post_event_normalization_seconds)
        values = {key: value for key, value in result.candidate.__dict__.items()
                  if key != "artifact_sha256"}
        self.assertEqual(artifact_hash(values), result.candidate.artifact_sha256)

    def test_holdout_exposure_fails_closed(self):
        altered = self.rows + (replace(
            self.rows[-1], observed_utc=self.rows[-1].observed_utc + timedelta(minutes=1),
            partition="HOLDOUT"),)
        plan = replace(self.plan, derived_dataset_sha256=rows_hash(altered))
        self.assertIn("HOLDOUT_EXPOSED", calibrate(plan, altered).reason_codes)

    def test_hash_and_chronology_are_bound(self):
        reversed_rows = tuple(reversed(self.rows))
        reasons = calibrate(self.plan, reversed_rows).reason_codes
        self.assertIn("DATASET_HASH_MISMATCH", reasons)
        self.assertIn("CHRONOLOGY_INVALID", reasons)

    def test_every_normal_session_requires_prospective_coverage(self):
        rows = tuple(row for row in self.rows
                     if not (row.partition == "TRAIN" and row.session == "ASIA"
                             and row.event_phase == "NORMAL"))
        plan = replace(self.plan, derived_dataset_sha256=rows_hash(rows))
        self.assertIn("ASIA_BASELINE_INSUFFICIENT", calibrate(plan, rows).reason_codes)

    def test_post_event_count_and_complete_recovery_are_independent(self):
        plan = replace(self.plan, minimum_post_event_rows=9)
        self.assertIn("POST_EVENT_SAMPLE_INSUFFICIENT",
                      calibrate(plan, self.rows).reason_codes)
        incomplete = tuple(replace(row, spread_points=30)
                           if row.event_id == "event-1" else row for row in self.rows)
        plan = replace(self.plan, derived_dataset_sha256=rows_hash(incomplete))
        self.assertIn("COMPLETE_EVENT_RECOVERY_INSUFFICIENT",
                      calibrate(plan, incomplete).reason_codes)

    def test_post_event_recovery_must_be_contiguously_observed(self):
        altered = []
        for row in self.rows:
            if row.event_id == "event-1" and row.event_phase == "POST_EVENT" \
                    and row.observed_utc.minute >= 28:
                altered.append(replace(row, observed_utc=row.observed_utc + timedelta(minutes=5)))
            else:
                altered.append(row)
        altered = tuple(sorted(altered, key=lambda row: row.observed_utc))
        plan = replace(self.plan, derived_dataset_sha256=rows_hash(altered),
                       train_end_utc=datetime(2025, 1, 1, 0, 40, tzinfo=UTC))
        self.assertIn("COMPLETE_EVENT_RECOVERY_INSUFFICIENT",
                      calibrate(plan, altered).reason_codes)

    def test_recovery_is_anchored_to_one_event_marker(self):
        missing = tuple(row for row in self.rows
                        if not (row.event_id == "event-1" and row.event_phase == "EVENT"))
        plan = replace(self.plan, derived_dataset_sha256=rows_hash(missing))
        reasons = calibrate(plan, missing).reason_codes
        self.assertIn("EVENT_MARKER_MISSING_OR_DUPLICATE", reasons)

        delayed = tuple(replace(row, observed_utc=row.observed_utc + timedelta(minutes=5))
                        if row.event_id == "event-1" and row.event_phase == "POST_EVENT"
                        else row for row in self.rows)
        delayed = tuple(sorted(delayed, key=lambda row: row.observed_utc))
        plan = replace(self.plan, derived_dataset_sha256=rows_hash(delayed),
                       train_end_utc=datetime(2025, 1, 1, 0, 40, tzinfo=UTC))
        self.assertIn("POST_EVENT_INITIAL_GAP", calibrate(plan, delayed).reason_codes)

    def test_event_rows_require_stable_event_id(self):
        with self.assertRaisesRegex(ValueError, "require event_id"):
            replace(self.rows[20], event_id=None)

    def test_validation_must_follow_frozen_training_cutoff(self):
        altered = tuple(replace(row, observed_utc=row.observed_utc - timedelta(minutes=20))
                        if row.partition == "VALIDATION" else row for row in self.rows)
        altered = tuple(sorted(altered, key=lambda row: row.observed_utc))
        plan = replace(self.plan, derived_dataset_sha256=rows_hash(altered))
        self.assertIn("VALIDATION_BEFORE_TRAIN_CUTOFF",
                      calibrate(plan, altered).reason_codes)

    def test_freeze_cutoff_rights_and_policy_fail_closed(self):
        bad = replace(
            self.plan, rights_status="UNKNOWN", holdout_status="OPEN",
            frozen_utc=datetime(2026, 1, 1, tzinfo=UTC), quantile_probability=1,
        )
        reasons = calibrate(bad, self.rows).reason_codes
        self.assertIn("RIGHTS_OR_HOLDOUT_INVALID", reasons)
        self.assertIn("FREEZE_CHRONOLOGY_INVALID", reasons)
        self.assertIn("CALIBRATION_POLICY_INVALID", reasons)

    def test_validation_changes_cannot_change_training_candidate(self):
        first = calibrate(self.plan, self.rows)
        altered = tuple(replace(row, spread_points=999, gap_points=999)
                        if row.partition == "VALIDATION" else row for row in self.rows)
        plan = replace(self.plan, derived_dataset_sha256=rows_hash(altered))
        second = calibrate(plan, altered)
        self.assertEqual(first.candidate, second.candidate)

    def test_module_has_no_raw_data_network_broker_model_process_or_write_capability(self):
        tree = ast.parse(Path(__file__).with_name("calibration_workflow.py").read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertTrue(imports.isdisjoint({
            "MetaTrader5", "requests", "urllib3", "socket", "subprocess", "openai",
            "pathlib", "os", "shutil", "csv", "pandas", "numpy",
        }))


if __name__ == "__main__":
    unittest.main(verbosity=2)
