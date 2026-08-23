import ast
import copy
import csv
import io
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from admission import CSV_FIELDS, dataset_root, manifest_hash, sha256_bytes
from multiframe_admission import (
    REQUIRED, SCHEMA_VERSION, admit_multiframe_bundle, bundle_hash, bundle_root, split_hash,
)


END = datetime(2026, 2, 1, tzinfo=timezone.utc)


def csv_body(count, period):
    start = END - timedelta(seconds=(count - 1) * period)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for index in range(count):
        stamp = start + timedelta(seconds=index * period)
        price = 2300 + index / 100
        writer.writerow({
            "timestamp_utc": stamp.isoformat().replace("+00:00", "Z"),
            "receipt_utc": (stamp + timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
            "open_bid": price, "high_bid": price + 2, "low_bid": price - 1,
            "close_bid": price + 1, "open_ask": price + .2,
            "high_ask": price + 2.2, "low_ask": price - .8,
            "close_ask": price + 1.2, "tick_volume": 10 + index,
        })
    return stream.getvalue().encode(), start


def fixture():
    terms = b"synthetic rights fixture only"
    split = {
        "train_start_utc": "2026-01-22T00:15:00Z",
        "train_end_utc": "2026-01-26T00:00:00Z",
        "validation_start_utc": "2026-01-26T01:00:00Z",
        "validation_end_utc": "2026-01-27T00:00:00Z",
        "embargo_start_utc": "2026-01-27T01:00:00Z",
        "embargo_end_utc": "2026-01-28T00:00:00Z",
        "holdout_start_utc": "2026-01-28T01:00:00Z",
        "holdout_end_utc": "2026-02-01T00:00:00Z",
        "purge_seconds": 3600,
        "embargo_seconds": 3600,
        "sealed": True,
    }
    split_digest = split_hash(split)
    manifests = {}
    artifacts = {}
    declared = {}
    for name, (period, count) in REQUIRED.items():
        body, start = csv_body(count, period)
        path = f"data/{name.lower()}.csv"
        descriptor = {
            "path": path, "sha256": sha256_bytes(body), "bytes": len(body),
            "row_count": count,
            "start_utc": start.isoformat().replace("+00:00", "Z"),
            "end_utc": END.isoformat().replace("+00:00", "Z"),
        }
        manifest = {
            "schema_version": "replay-admission-1.0", "dataset_id": f"SYNTHETIC-{name}",
            "frozen_at_utc": "2026-02-02T00:00:00Z", "bar_period_seconds": period,
            "provenance": {
                "provider": "Synthetic Test Fixture", "source_uri": "https://example.invalid/source",
                "instrument": "XAUUSD", "instrument_semantics": "synthetic bid/ask OHLC",
                "timezone": "UTC", "acquisition_method": "offline test generator",
                "terms_identifier": "synthetic-test-only",
            },
            "rights": {
                "review_status": "APPROVED_FOR_INTERNAL_EVALUATION",
                "automated_use": True, "local_retention": True, "derived_data": True,
                "historical_replay": True, "internal_audit_retention": True,
                "redistribution": False, "reviewed_by": "TEST_FIXTURE",
                "reviewed_utc": "2026-02-01T12:00:00Z",
                "terms_artifact": "evidence/terms.txt", "terms_sha256": sha256_bytes(terms),
            },
            "registration": {
                "trial_id": f"TRIAL-{name}", "strategy_version": "1.0-rc1",
                "code_sha256": "1" * 64, "config_sha256": "2" * 64,
                "split_map_sha256": split_digest, "acceptance_rule_version": "1.0-rc1",
                "registered_utc": "2026-02-01T18:00:00Z", "holdout_status": "SEALED",
                "results_viewed": False,
            },
            "files": [descriptor], "authorized_gaps": [],
        }
        manifest["dataset_root_sha256"] = dataset_root(manifest["files"])
        manifest["manifest_sha256"] = manifest_hash(manifest)
        manifests[name] = manifest
        artifacts[name] = {path: body, "evidence/terms.txt": terms}
        declared[name] = {"dataset_id": manifest["dataset_id"],
                          "dataset_root_sha256": manifest["dataset_root_sha256"]}
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": "SYNTHETIC-BUNDLE", "frozen_at_utc": "2026-02-02T00:00:00Z",
        "timeframes": declared, "split": split, "split_map_sha256": split_digest,
    }
    bundle["bundle_root_sha256"] = bundle_root(declared)
    bundle["bundle_manifest_sha256"] = bundle_hash(bundle)
    return bundle, manifests, artifacts


def resign(bundle):
    bundle["bundle_root_sha256"] = bundle_root(bundle["timeframes"])
    bundle["bundle_manifest_sha256"] = bundle_hash(bundle)


class MultiFrameAdmissionTests(unittest.TestCase):
    def test_complete_300_500_1000_bundle_is_admitted_synthetic_only(self):
        bundle, manifests, artifacts = fixture()
        result = admit_multiframe_bundle(bundle, manifests, artifacts)
        self.assertEqual(result.status, "ADMITTED")
        self.assertEqual(dict(result.child_rows), {"H4": 300, "H1": 500, "M15": 1000})

    def test_missing_or_extra_timeframe_fails_closed(self):
        self.assertIn("BUNDLE_OR_CHILD_CONTAINER_INVALID",
                      admit_multiframe_bundle(None, {}, {}).reason_codes)
        bundle, manifests, artifacts = fixture()
        del manifests["H4"]
        self.assertIn("CHILD_INVENTORY_INVALID",
                      admit_multiframe_bundle(bundle, manifests, artifacts).reason_codes)
        bundle, manifests, artifacts = fixture()
        bundle["timeframes"]["M5"] = copy.deepcopy(bundle["timeframes"]["M15"])
        resign(bundle)
        self.assertIn("TIMEFRAME_INVENTORY_INVALID",
                      admit_multiframe_bundle(bundle, manifests, artifacts).reason_codes)

    def test_child_hash_rights_and_admission_failure_propagate(self):
        bundle, manifests, artifacts = fixture()
        artifacts["H1"]["evidence/terms.txt"] = b"tamper"
        result = admit_multiframe_bundle(bundle, manifests, artifacts)
        self.assertIn("H1_CHILD_NOT_ADMITTED", result.reason_codes)

    def test_cadence_and_minimum_rows_are_exactly_bound(self):
        bundle, manifests, artifacts = fixture()
        manifests["M15"]["bar_period_seconds"] = 3600
        manifests["M15"]["manifest_sha256"] = manifest_hash(manifests["M15"])
        result = admit_multiframe_bundle(bundle, manifests, artifacts)
        self.assertIn("M15_WARMUP_OR_CADENCE_INVALID", result.reason_codes)

    def test_provider_terms_semantics_and_child_roots_must_match(self):
        bundle, manifests, artifacts = fixture()
        manifests["H4"]["provenance"]["provider"] = "Different Provider"
        manifests["H4"]["manifest_sha256"] = manifest_hash(manifests["H4"])
        result = admit_multiframe_bundle(bundle, manifests, artifacts)
        self.assertIn("CROSS_TIMEFRAME_PROVENANCE_OR_RIGHTS_MISMATCH", result.reason_codes)
        bundle, manifests, artifacts = fixture()
        bundle["timeframes"]["H1"]["dataset_root_sha256"] = "0" * 64
        resign(bundle)
        self.assertIn("CHILD_ROOT_MISMATCH",
                      admit_multiframe_bundle(bundle, manifests, artifacts).reason_codes)

    def test_split_must_be_sealed_ordered_hashed_and_covered(self):
        bundle, manifests, artifacts = fixture()
        bundle["split"]["sealed"] = False
        resign(bundle)
        self.assertIn("SPLIT_MAP_INVALID",
                      admit_multiframe_bundle(bundle, manifests, artifacts).reason_codes)
        bundle, manifests, artifacts = fixture()
        bundle["split"]["train_start_utc"] = "2026-01-01T00:00:00Z"
        bundle["split_map_sha256"] = split_hash(bundle["split"])
        for manifest in manifests.values():
            manifest["registration"]["split_map_sha256"] = bundle["split_map_sha256"]
            manifest["manifest_sha256"] = manifest_hash(manifest)
        resign(bundle)
        self.assertIn("SPLIT_COVERAGE_INCOMPLETE",
                      admit_multiframe_bundle(bundle, manifests, artifacts).reason_codes)

    def test_split_requires_complete_inventory_and_declared_gaps(self):
        bundle, manifests, artifacts = fixture()
        del bundle["split"]["validation_start_utc"]
        bundle["split_map_sha256"] = split_hash(bundle["split"])
        for manifest in manifests.values():
            manifest["registration"]["split_map_sha256"] = bundle["split_map_sha256"]
            manifest["manifest_sha256"] = manifest_hash(manifest)
        resign(bundle)
        self.assertIn("SPLIT_MAP_INVALID",
                      admit_multiframe_bundle(bundle, manifests, artifacts).reason_codes)
        bundle, manifests, artifacts = fixture()
        bundle["split"]["purge_seconds"] = 3601
        bundle["split"]["embargo_seconds"] = 82801
        bundle["split_map_sha256"] = split_hash(bundle["split"])
        for manifest in manifests.values():
            manifest["registration"]["split_map_sha256"] = bundle["split_map_sha256"]
            manifest["manifest_sha256"] = manifest_hash(manifest)
        resign(bundle)
        self.assertIn("SPLIT_MAP_INVALID",
                      admit_multiframe_bundle(bundle, manifests, artifacts).reason_codes)

    def test_bundle_and_child_dataset_id_tamper_fail(self):
        bundle, manifests, artifacts = fixture()
        bundle["bundle_id"] = "MUTATED"
        self.assertIn("BUNDLE_HASH_MISMATCH",
                      admit_multiframe_bundle(bundle, manifests, artifacts).reason_codes)
        bundle, manifests, artifacts = fixture()
        manifests["H1"]["dataset_id"] = manifests["H4"]["dataset_id"]
        manifests["H1"]["manifest_sha256"] = manifest_hash(manifests["H1"])
        self.assertIn("CHILD_DATASET_ID_COLLISION",
                      admit_multiframe_bundle(bundle, manifests, artifacts).reason_codes)

    def test_oracle_has_no_network_broker_model_process_or_write_capability(self):
        tree = ast.parse(Path(__file__).with_name("multiframe_admission.py").read_text(encoding="utf-8"))
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
            {"MetaTrader5", "socket", "requests", "urllib", "httpx", "openai", "subprocess", "os", "pathlib"}
        ))
        self.assertTrue(calls.isdisjoint({"open", "write_text", "write_bytes", "order_send", "Popen", "run"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
