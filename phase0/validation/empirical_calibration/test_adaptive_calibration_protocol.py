from __future__ import annotations

import ast
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import unittest

from adaptive_calibration_protocol import (
    AdaptivePlan, AdaptiveRow, evaluate_adaptive_trial, plan_hash,
)


UTC = timezone.utc
CUTOFF = datetime(2026, 8, 23, 23, 45, tzinfo=UTC)
START = datetime(2026, 8, 25, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 23, 23, 45, tzinfo=UTC)


def session(stamp):
    if stamp.hour < 8:
        return "ASIA"
    if stamp.hour < 13:
        return "LONDON"
    if stamp.hour < 21:
        return "LONDON_NY"
    return "ROLLOVER"


def rows(start, end, value=1.0):
    output = []
    stamp = start
    while stamp <= end:
        output.append(AdaptiveRow(stamp, session(stamp), value, value, value))
        stamp += timedelta(minutes=15)
    return tuple(output)


def plan():
    draft = AdaptivePlan(
        schema_version="adaptive-cost-calibration-1.0",
        bundle_root_sha256="a" * 64,
        registered_utc=datetime(2026, 8, 24, 10, 41, 53, tzinfo=UTC),
        development_cutoff_utc=CUTOFF,
        evaluation_start_utc=START,
        evaluation_end_utc=END,
        lookback_days=56,
        quantile_probability=.995,
        minimum_history_rows_per_session=500,
        minimum_evaluation_rows=2500,
        minimum_evaluation_rows_per_session=300,
        minimum_overall_coverage=.99,
        minimum_session_coverage=.985,
        daily_freeze_utc_hour=0,
        external_python_trading_disabled=True,
        trading_authorized=False,
        registration_sha256="0" * 64,
    )
    return replace(draft, registration_sha256=plan_hash(draft))


DEVELOPMENT = rows(CUTOFF - timedelta(days=56), CUTOFF)
EVALUATION = rows(START, END)


class AdaptiveCalibrationProtocolTests(unittest.TestCase):
    def test_published_registration_is_canonical_and_code_bound(self):
        root = Path(__file__).parent
        record = json.loads((root / "ADAPTIVE_CALIBRATION_REGISTRATION_2026-08-24_R4.json").read_text())
        expected_record = record.pop("record_sha256")
        self.assertEqual(expected_record, hashlib.sha256(json.dumps(
            record, sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest())
        self.assertEqual(record["adaptive_protocol_sha256"], hashlib.sha256(
            (root / "adaptive_calibration_protocol.py").read_bytes()).hexdigest())
        registered = AdaptivePlan(
            schema_version="adaptive-cost-calibration-1.0",
            bundle_root_sha256=record["bundle_root_sha256"],
            registered_utc=datetime.fromisoformat(record["registered_utc"].replace("Z", "+00:00")),
            development_cutoff_utc=datetime.fromisoformat(
                record["development_cutoff_utc"].replace("Z", "+00:00")),
            evaluation_start_utc=datetime.fromisoformat(
                record["future_evaluation"]["start_utc"].replace("Z", "+00:00")),
            evaluation_end_utc=datetime.fromisoformat(
                record["future_evaluation"]["end_utc"].replace("Z", "+00:00")),
            lookback_days=record["adaptive_model"]["lookback_days"],
            quantile_probability=record["adaptive_model"]["quantile_probability"],
            minimum_history_rows_per_session=record["adaptive_model"][
                "minimum_history_rows_per_session"],
            minimum_evaluation_rows=record["future_evaluation"]["minimum_rows"],
            minimum_evaluation_rows_per_session=record["future_evaluation"][
                "minimum_rows_per_session"],
            minimum_overall_coverage=record["adaptive_model"]["overall_minimum_coverage"],
            minimum_session_coverage=record["adaptive_model"][
                "per_session_minimum_coverage"],
            daily_freeze_utc_hour=record["adaptive_model"]["daily_freeze_utc_hour"],
            external_python_trading_disabled=True,
            trading_authorized=record["trading_authorized"],
            registration_sha256=record["adaptive_plan_sha256"],
        )
        self.assertEqual(record["adaptive_plan_sha256"], plan_hash(registered))

    def test_registered_future_trial_validates_stable_fixture(self):
        result = evaluate_adaptive_trial(plan(), DEVELOPMENT, EVALUATION)
        self.assertEqual("VALIDATED_NON_TRADING", result.status)
        self.assertEqual(2880, result.evaluated_rows)

    def test_registration_hash_and_frozen_policy_are_exact(self):
        item = plan()
        self.assertEqual("FAIL_CLOSED", evaluate_adaptive_trial(
            replace(item, quantile_probability=.99), DEVELOPMENT, EVALUATION).status)
        self.assertEqual("FAIL_CLOSED", evaluate_adaptive_trial(
            replace(item, registration_sha256="f" * 64), DEVELOPMENT, EVALUATION).status)

    def test_trial_must_be_registered_before_future_evaluation(self):
        item = plan()
        changed = replace(item, registered_utc=START + timedelta(minutes=1))
        changed = replace(changed, registration_sha256=plan_hash(changed))
        self.assertIn("PROSPECTIVE_CHRONOLOGY_INVALID",
                      evaluate_adaptive_trial(changed, DEVELOPMENT, EVALUATION).reason_codes)

    def test_development_and_evaluation_partitions_are_strict(self):
        result = evaluate_adaptive_trial(plan(), DEVELOPMENT + (EVALUATION[0],), EVALUATION)
        self.assertIn("DEVELOPMENT_CUTOFF_VIOLATION", result.reason_codes)
        self.assertIn("PARTITION_OVERLAP", result.reason_codes)

    def test_insufficient_session_or_total_sample_fails_closed(self):
        result = evaluate_adaptive_trial(plan(), DEVELOPMENT, EVALUATION[:1000])
        self.assertIn("EVALUATION_SAMPLE_INSUFFICIENT", result.reason_codes)
        self.assertTrue(any(code.endswith("EVALUATION_SAMPLE_INSUFFICIENT")
                            for code in result.reason_codes))

    def test_large_future_tail_shift_is_rejected(self):
        shifted = tuple(replace(row, spread_points=10.0) for row in EVALUATION)
        result = evaluate_adaptive_trial(plan(), DEVELOPMENT, shifted)
        self.assertEqual("REJECTED", result.status)
        self.assertIn("OVERALL_COVERAGE_REJECTED", result.reason_codes)

    def test_daily_freeze_prevents_same_day_lookahead(self):
        shifted = tuple(replace(row, gap_points=10.0) if row.observed_utc.date() == START.date()
                        else row for row in EVALUATION)
        result = evaluate_adaptive_trial(plan(), DEVELOPMENT, shifted)
        self.assertEqual("REJECTED", result.status)
        first_day_session = next(value for session_name, metric, value in result.session_coverage
                                 if session_name == "ASIA" and metric == "gap_points")
        self.assertLess(first_day_session, 1.0)

    def test_module_has_no_file_network_broker_model_process_or_write_capability(self):
        tree = ast.parse(Path(__file__).with_name("adaptive_calibration_protocol.py").read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertTrue(imports.isdisjoint({
            "MetaTrader5", "openai", "requests", "socket", "subprocess", "pathlib",
            "os", "shutil", "smtplib", "telegram",
        }))


if __name__ == "__main__":
    unittest.main(verbosity=2)
