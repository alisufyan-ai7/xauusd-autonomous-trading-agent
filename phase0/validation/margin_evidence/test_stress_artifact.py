import ast
import copy
import unittest
from datetime import datetime, timezone
from pathlib import Path

from phase0.validation.margin_evidence.stress_artifact import admit_stress_artifact, artifact_hash


NOW = datetime(2026, 8, 23, 12, tzinfo=timezone.utc)
ROOT = "a" * 64


def fixture():
    artifact = {
        "schema_version": "gate0-m1-adverse-stress-1.0",
        "artifact_id": "SYNTHETIC-STRESS-ONLY",
        "status": "FROZEN",
        "holdout_results_viewed": False,
        "scope": {"symbol": "XAUUSD", "volume_lots": "0.01", "currency": "USD",
                  "contract_spec_sha256": "b" * 64},
        "provenance": {"bundle_root_sha256": ROOT, "calibration_code_sha256": "c" * 64,
                       "config_sha256": "d" * 64, "split_map_sha256": "e" * 64},
        "training_start_utc": "2026-01-01T00:00:00Z",
        "training_end_utc": "2026-07-31T00:00:00Z",
        "frozen_at_utc": "2026-08-01T00:00:00Z",
        "review_due_utc": "2026-11-01T00:00:00Z",
        "components": {},
    }
    for index, name in enumerate(("spread_stress", "slippage_stress", "gap_stress", "cost_stress"), 1):
        artifact["components"][name] = {
            "method": "TRAIN_ONLY_EMPIRICAL_QUANTILE", "quantile_basis_points": 9900,
            "sample_count": 1000, "empirical_value_usd": str(index),
            "selected_value_usd": str(index + 1), "evidence_sha256": str(index) * 64,
        }
    artifact["artifact_sha256"] = artifact_hash(artifact)
    return artifact


def resign(artifact):
    artifact["artifact_sha256"] = artifact_hash(artifact)


class StressArtifactTests(unittest.TestCase):
    def test_complete_frozen_artifact_is_admitted_spec_only(self):
        result = admit_stress_artifact(fixture(), expected_bundle_root_sha256=ROOT, now_utc=NOW)
        self.assertEqual(result.status, "ADMITTED_SPEC_ONLY")
        self.assertEqual(dict(result.adverse_stresses),
                         {"spread_stress": 2, "slippage_stress": 3, "gap_stress": 4, "cost_stress": 5})

    def test_unfrozen_or_holdout_viewed_rejects(self):
        artifact = fixture(); artifact["status"] = "CANDIDATE"; artifact["holdout_results_viewed"] = True
        resign(artifact)
        self.assertIn("STRESS_NOT_FROZEN_PRE_HOLDOUT",
                      admit_stress_artifact(artifact, expected_bundle_root_sha256=ROOT, now_utc=NOW).reason_codes)

    def test_zero_placeholder_and_selected_below_empirical_reject(self):
        artifact = fixture(); artifact["components"]["gap_stress"]["selected_value_usd"] = "0"
        resign(artifact)
        self.assertIn("STRESS_COMPONENT_INVALID",
                      admit_stress_artifact(artifact, expected_bundle_root_sha256=ROOT, now_utc=NOW).reason_codes)
        artifact = fixture(); artifact["components"]["cost_stress"]["selected_value_usd"] = "1"
        resign(artifact)
        self.assertIn("STRESS_SELECTED_BELOW_EMPIRICAL",
                      admit_stress_artifact(artifact, expected_bundle_root_sha256=ROOT, now_utc=NOW).reason_codes)

    def test_scope_bundle_and_digest_binding_are_mandatory(self):
        artifact = fixture(); artifact["scope"]["volume_lots"] = "0.02"
        artifact["provenance"]["bundle_root_sha256"] = "f" * 64
        resign(artifact)
        result = admit_stress_artifact(artifact, expected_bundle_root_sha256=ROOT, now_utc=NOW)
        self.assertIn("STRESS_SCOPE_INVALID", result.reason_codes)
        self.assertIn("STRESS_PROVENANCE_INVALID", result.reason_codes)

    def test_training_freeze_and_review_chronology_fail_closed(self):
        artifact = fixture(); artifact["training_end_utc"] = "2026-08-02T00:00:00Z"
        resign(artifact)
        self.assertIn("STRESS_CHRONOLOGY_OR_REVIEW_INVALID",
                      admit_stress_artifact(artifact, expected_bundle_root_sha256=ROOT, now_utc=NOW).reason_codes)
        artifact = fixture(); artifact["review_due_utc"] = "2026-08-01T00:00:00Z"
        resign(artifact)
        self.assertIn("STRESS_CHRONOLOGY_OR_REVIEW_INVALID",
                      admit_stress_artifact(artifact, expected_bundle_root_sha256=ROOT, now_utc=NOW).reason_codes)

    def test_any_unsigned_mutation_is_detected(self):
        artifact = fixture(); artifact["components"]["spread_stress"]["sample_count"] += 1
        self.assertIn("STRESS_ARTIFACT_HASH_MISMATCH",
                      admit_stress_artifact(artifact, expected_bundle_root_sha256=ROOT, now_utc=NOW).reason_codes)

    def test_oracle_has_no_private_broker_network_model_process_or_write_capability(self):
        tree = ast.parse(Path(__file__).with_name("stress_artifact.py").read_text(encoding="utf-8"))
        imported, calls = set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                calls.add(node.func.attr if isinstance(node.func, ast.Attribute)
                          else node.func.id if isinstance(node.func, ast.Name) else "")
        self.assertTrue(imported.isdisjoint(
            {"MetaTrader5", "socket", "requests", "urllib", "httpx", "openai", "subprocess", "pathlib", "os"}
        ))
        self.assertTrue(calls.isdisjoint({"open", "write_text", "write_bytes", "order_send", "Popen", "run"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
