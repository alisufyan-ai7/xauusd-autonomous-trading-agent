import ast
import copy
import csv
import io
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from admission import (
    CSV_FIELDS, admit, dataset_root, manifest_hash, sha256_bytes,
)


def csv_bytes(start: datetime, count: int, step_seconds: int = 900) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for index in range(count):
        stamp = start + timedelta(seconds=index * step_seconds)
        price = 2300 + index
        writer.writerow({
            "timestamp_utc": stamp.isoformat().replace("+00:00", "Z"),
            "receipt_utc": (stamp + timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
            "open_bid": price, "high_bid": price + 2, "low_bid": price - 1,
            "close_bid": price + 1, "open_ask": price + .2,
            "high_ask": price + 2.2, "low_ask": price - .8,
            "close_ask": price + 1.2, "tick_volume": 10 + index,
        })
    return stream.getvalue().encode("utf-8")


def fixture():
    terms = b"synthetic test terms: automated use, retention, derived data, replay"
    body = csv_bytes(datetime(2026, 1, 5, tzinfo=timezone.utc), 4)
    descriptor = {
        "path": "data/xauusd-2026-01.csv", "sha256": sha256_bytes(body),
        "bytes": len(body), "row_count": 4,
        "start_utc": "2026-01-05T00:00:00Z", "end_utc": "2026-01-05T00:45:00Z",
    }
    manifest = {
        "schema_version": "replay-admission-1.0", "dataset_id": "SYNTHETIC-ONLY",
        "frozen_at_utc": "2026-01-10T00:00:00Z", "bar_period_seconds": 900,
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
            "reviewed_utc": "2026-01-09T00:00:00Z",
            "terms_artifact": "evidence/terms.txt", "terms_sha256": sha256_bytes(terms),
        },
        "registration": {
            "trial_id": "TRIAL-SYNTHETIC-001", "strategy_version": "1.0-rc1",
            "code_sha256": "1" * 64, "config_sha256": "2" * 64,
            "split_map_sha256": "3" * 64, "acceptance_rule_version": "1.0-rc1",
            "registered_utc": "2026-01-09T12:00:00Z", "holdout_status": "SEALED",
            "results_viewed": False,
        },
        "files": [descriptor], "authorized_gaps": [],
    }
    manifest["dataset_root_sha256"] = dataset_root(manifest["files"])
    manifest["manifest_sha256"] = manifest_hash(manifest)
    return manifest, {descriptor["path"]: body, "evidence/terms.txt": terms}


def resign(manifest):
    manifest["dataset_root_sha256"] = dataset_root(manifest["files"])
    manifest["manifest_sha256"] = manifest_hash(manifest)


class ReplayAdmissionTests(unittest.TestCase):
    def test_oracle_has_no_broker_network_model_process_or_filesystem_imports(self):
        tree = ast.parse(Path(__file__).with_name("admission.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(imported.isdisjoint({
            "MetaTrader5", "socket", "requests", "urllib", "httpx", "openai",
            "subprocess", "pathlib", "os", "shutil",
        }))

    def test_complete_synthetic_fixture_is_admitted_but_is_not_real_evidence(self):
        manifest, artifacts = fixture()
        result = admit(manifest, artifacts)
        self.assertEqual((result.status, result.rows, result.data_files), ("ADMITTED", 4, 1))

    def test_manifest_and_market_file_mutation_are_detected(self):
        manifest, artifacts = fixture()
        manifest["dataset_id"] = "MUTATED"
        self.assertIn("MANIFEST_HASH_MISMATCH", admit(manifest, artifacts).reason_codes)
        manifest, artifacts = fixture()
        artifacts["data/xauusd-2026-01.csv"] += b"tamper"
        self.assertIn("FILE_HASH_OR_SIZE_MISMATCH", admit(manifest, artifacts).reason_codes)

    def test_each_required_right_and_terms_evidence_fails_closed(self):
        for field in ("automated_use", "local_retention", "derived_data", "historical_replay", "internal_audit_retention"):
            manifest, artifacts = fixture()
            manifest["rights"][field] = False
            resign(manifest)
            self.assertIn("RIGHTS_NOT_ESTABLISHED", admit(manifest, artifacts).reason_codes)
        manifest, artifacts = fixture()
        artifacts["evidence/terms.txt"] = b"different terms"
        self.assertIn("RIGHTS_EVIDENCE_HASH_MISMATCH", admit(manifest, artifacts).reason_codes)

    def test_provenance_and_sealed_registration_are_mandatory(self):
        manifest, artifacts = fixture()
        manifest["provenance"]["source_uri"] = "http://not-authoritative.invalid"
        manifest["registration"]["holdout_status"] = "OPENED"
        manifest["registration"]["results_viewed"] = True
        resign(manifest)
        result = admit(manifest, artifacts)
        self.assertIn("PROVENANCE_INCOMPLETE", result.reason_codes)
        self.assertIn("REGISTRATION_INCOMPLETE", result.reason_codes)

    def test_duplicate_and_reversed_timestamps_are_rejected(self):
        manifest, artifacts = fixture()
        body = csv_bytes(datetime(2026, 1, 5, tzinfo=timezone.utc), 2, 0)
        manifest["files"][0].update(
            sha256=sha256_bytes(body), bytes=len(body), row_count=2,
            start_utc="2026-01-05T00:00:00Z", end_utc="2026-01-05T00:00:00Z",
        )
        artifacts["data/xauusd-2026-01.csv"] = body
        resign(manifest)
        result = admit(manifest, artifacts)
        self.assertIn("DUPLICATE_TIMESTAMP", result.reason_codes)
        self.assertIn("NON_CHRONOLOGICAL", result.reason_codes)

    def test_unexplained_gap_rejects_and_exact_evidenced_gap_admits(self):
        manifest, artifacts = fixture()
        body = csv_bytes(datetime(2026, 1, 5, tzinfo=timezone.utc), 3, 1800)
        manifest["files"][0].update(
            sha256=sha256_bytes(body), bytes=len(body), row_count=3,
            start_utc="2026-01-05T00:00:00Z", end_utc="2026-01-05T01:00:00Z",
        )
        artifacts["data/xauusd-2026-01.csv"] = body
        resign(manifest)
        self.assertIn("UNEXPLAINED_GAP", admit(manifest, artifacts).reason_codes)

        evidence = b"synthetic official-session evidence"
        artifacts["evidence/session.txt"] = evidence
        manifest["authorized_gaps"] = [
            {
                "after_utc": "2026-01-05T00:00:00Z", "before_utc": "2026-01-05T00:30:00Z",
                "reason": "SESSION_CLOSED", "source_uri": "https://example.invalid/session",
                "evidence_artifact": "evidence/session.txt", "evidence_sha256": sha256_bytes(evidence),
            },
            {
                "after_utc": "2026-01-05T00:30:00Z", "before_utc": "2026-01-05T01:00:00Z",
                "reason": "PROVIDER_SIDE_MISMATCH", "source_uri": "https://example.invalid/raw-side-hashes",
                "evidence_artifact": "evidence/session.txt", "evidence_sha256": sha256_bytes(evidence),
            },
        ]
        resign(manifest)
        result = admit(manifest, artifacts)
        self.assertEqual((result.status, result.authorized_gaps), ("ADMITTED", 2))

    def test_unused_or_weak_gap_authorization_is_rejected(self):
        manifest, artifacts = fixture()
        evidence = b"gap"
        artifacts["evidence/gap.txt"] = evidence
        manifest["authorized_gaps"] = [{
            "after_utc": "2026-01-06T00:00:00Z", "before_utc": "2026-01-06T01:00:00Z",
            "reason": "UNKNOWN", "source_uri": "http://example.invalid",
            "evidence_artifact": "evidence/gap.txt", "evidence_sha256": sha256_bytes(evidence),
        }]
        resign(manifest)
        result = admit(manifest, artifacts)
        self.assertIn("GAP_REGISTRY_INVALID", result.reason_codes)

    def test_bad_schema_ohlc_bid_ask_receipt_and_extra_artifact_fail(self):
        mutations = (
            b"bad,header\n1,2\n",
            csv_bytes(datetime(2026, 1, 5, tzinfo=timezone.utc), 2).replace(b"2301,2303", b"2301,2299", 1),
        )
        for body in mutations:
            manifest, artifacts = fixture()
            manifest["files"][0].update(sha256=sha256_bytes(body), bytes=len(body))
            artifacts["data/xauusd-2026-01.csv"] = body
            resign(manifest)
            self.assertEqual(admit(manifest, artifacts).status, "REJECTED")
        manifest, artifacts = fixture()
        artifacts["unregistered.bin"] = b"surprise"
        self.assertIn("ARTIFACT_SET_MISMATCH", admit(manifest, artifacts).reason_codes)

    def test_malformed_descriptor_and_gap_fail_closed_without_exception(self):
        manifest, artifacts = fixture()
        manifest["files"] = [None]
        manifest["authorized_gaps"] = [{"after_utc": [], "before_utc": {}}]
        manifest["dataset_root_sha256"] = "0" * 64
        manifest["manifest_sha256"] = manifest_hash(manifest)
        result = admit(manifest, artifacts)
        self.assertEqual(result.status, "REJECTED")
        self.assertIn("FILES_INCOMPLETE", result.reason_codes)
        self.assertIn("GAP_REGISTRY_INVALID", result.reason_codes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
