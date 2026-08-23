from __future__ import annotations

import ast
import copy
from pathlib import Path
import unittest

from acquisition_protocol import (
    canonical_hash, evaluate_plan, inventory_root, plan_hash, sha256_bytes,
    split_hash, verify_sealed_inventory,
)


TERMS = b"synthetic rights evidence; not provider authorization"
H = "1" * 64


def fixture():
    split = {
        "sealed": True,
        "train_start_utc": "2020-01-01T00:00:00Z",
        "train_end_utc": "2023-12-31T23:45:00Z",
        "validation_start_utc": "2024-01-08T00:00:00Z",
        "validation_end_utc": "2024-12-31T23:45:00Z",
        "embargo_start_utc": "2025-01-01T00:00:00Z",
        "embargo_end_utc": "2025-01-08T00:00:00Z",
        "holdout_start_utc": "2025-01-09T00:00:00Z",
        "holdout_end_utc": "2026-07-31T23:45:00Z",
        "purge_seconds": 604800,
        "embargo_seconds": 604800,
    }
    plan = {
        "schema_version": "xauusd-acquisition-plan-1.0",
        "registered_utc": "2019-12-01T00:00:00Z",
        "provider": {
            "name": "Synthetic Provider", "legal_entity": "Synthetic Provider Ltd",
            "source_uri": "https://provider.invalid/xauusd", "instrument": "XAUUSD",
            "instrument_semantics": "provider spot gold CFD best bid/ask",
            "timezone": "UTC", "price_content": "TICK_BID_ASK",
            "entitlement_status": "DOCUMENTED_ACTIVE", "terms_identifier": "terms-v1",
        },
        "rights": {
            "review_status": "APPROVED_FOR_INTERNAL_EVALUATION",
            "terms_uri": "https://provider.invalid/terms", "terms_effective_date": "2019-01-01",
            "terms_artifact": "terms.txt", "terms_sha256": sha256_bytes(TERMS),
            "reviewed_utc": "2019-11-30T00:00:00Z", "reviewed_by_role": "LICENSE_REVIEWER",
            "automated_use": True, "local_retention": True, "derived_data": True,
            "historical_replay": True, "internal_audit_retention": True,
            "redistribution": False, "termination_retention": "EXPLICITLY_PERMITTED",
        },
        "acquisition": {
            "method": "HTTPS_EXPORT", "http_method": "GET",
            "start_utc": "2020-01-01T00:00:00Z", "end_utc": "2026-08-01T00:00:00Z",
            "output_outside_repository": True, "raw_bytes_preserved": True,
            "immutable_after_seal": True, "credentials_in_manifest": False,
        },
        "timeframes": {
            "H4": {"period_seconds": 14400, "minimum_rows": 300,
                   "derivation": "DETERMINISTIC_FROM_ADMITTED_SOURCE"},
            "H1": {"period_seconds": 3600, "minimum_rows": 500,
                   "derivation": "DETERMINISTIC_FROM_ADMITTED_SOURCE"},
            "M15": {"period_seconds": 900, "minimum_rows": 1000,
                    "derivation": "DETERMINISTIC_FROM_ADMITTED_SOURCE"},
        },
        "split": split, "split_map_sha256": split_hash(split),
        "registration": {
            "holdout_status": "SEALED_UNVIEWED", "results_viewed": False,
            "random_split": False, "code_sha256": H, "config_sha256": H,
            "acceptance_rules_sha256": H,
        },
        "transformations": {
            "raw_bytes_immutable": True, "deterministic": True,
            "bid_ask_preserved": True, "forming_bars_excluded": True,
            "code_sha256": H,
        },
    }
    plan["plan_sha256"] = plan_hash(plan)
    return plan


def resign(plan):
    plan["plan_sha256"] = plan_hash(plan)


class AcquisitionProtocolTests(unittest.TestCase):
    def test_complete_plan_is_readiness_only(self):
        result = evaluate_plan(fixture(), {"terms.txt": TERMS})
        self.assertEqual("READY_FOR_AUTHORIZED_ACQUISITION", result.status)
        self.assertEqual(canonical_hash(fixture()["split"]), result.split_map_sha256)

    def test_public_candidate_without_explicit_rights_fails(self):
        plan = fixture()
        plan["rights"]["derived_data"] = False
        plan["rights"]["termination_retention"] = "UNCLEAR"
        resign(plan)
        self.assertIn("RIGHTS_NOT_ESTABLISHED",
                      evaluate_plan(plan, {"terms.txt": TERMS}).reason_codes)

    def test_terms_bytes_and_plan_mutation_are_detected(self):
        plan = fixture()
        self.assertIn("RIGHTS_EVIDENCE_HASH_MISMATCH",
                      evaluate_plan(plan, {"terms.txt": b"changed"}).reason_codes)
        plan["provider"]["name"] = "changed"
        self.assertIn("PLAN_HASH_MISMATCH",
                      evaluate_plan(plan, {"terms.txt": TERMS}).reason_codes)

    def test_exact_timeframe_inventory_and_minima(self):
        plan = fixture()
        del plan["timeframes"]["H4"]
        resign(plan)
        self.assertIn("TIMEFRAME_INVENTORY_INVALID",
                      evaluate_plan(plan, {"terms.txt": TERMS}).reason_codes)
        plan = fixture()
        plan["timeframes"]["M15"]["minimum_rows"] = 999
        resign(plan)
        self.assertIn("M15_PROCEDURE_INVALID",
                      evaluate_plan(plan, {"terms.txt": TERMS}).reason_codes)

    def test_split_is_strict_preregistered_and_inside_range(self):
        plan = fixture()
        plan["split"]["validation_start_utc"] = plan["split"]["train_end_utc"]
        plan["split_map_sha256"] = split_hash(plan["split"])
        resign(plan)
        self.assertIn("SPLIT_NOT_PREREGISTERED",
                      evaluate_plan(plan, {"terms.txt": TERMS}).reason_codes)
        plan = fixture()
        plan["split"]["train_start_utc"] = "2019-01-01T00:00:00Z"
        plan["split_map_sha256"] = split_hash(plan["split"])
        resign(plan)
        self.assertIn("SPLIT_OUTSIDE_ACQUISITION_RANGE",
                      evaluate_plan(plan, {"terms.txt": TERMS}).reason_codes)

    def test_declared_purge_and_embargo_durations_are_enforced(self):
        plan = fixture()
        plan["split"]["purge_seconds"] += 3600
        plan["split"]["embargo_seconds"] += 3600
        plan["split_map_sha256"] = split_hash(plan["split"])
        resign(plan)
        reasons = evaluate_plan(plan, {"terms.txt": TERMS}).reason_codes
        self.assertIn("PURGE_GAP_TOO_SHORT", reasons)
        self.assertIn("EMBARGO_GAP_TOO_SHORT", reasons)

    def test_terms_must_be_effective_at_review_and_acquisition(self):
        plan = fixture()
        plan["rights"]["terms_effective_date"] = "2020-01-02"
        resign(plan)
        reasons = evaluate_plan(plan, {"terms.txt": TERMS}).reason_codes
        self.assertIn("TERMS_NOT_EFFECTIVE_AT_REVIEW", reasons)
        self.assertIn("TERMS_NOT_EFFECTIVE_AT_ACQUISITION", reasons)

    def test_holdout_random_split_and_transform_relaxation_fail(self):
        plan = fixture()
        plan["registration"]["holdout_status"] = "OPEN"
        plan["registration"]["random_split"] = True
        plan["transformations"]["forming_bars_excluded"] = False
        resign(plan)
        reasons = evaluate_plan(plan, {"terms.txt": TERMS}).reason_codes
        self.assertIn("TRIAL_REGISTRATION_INVALID", reasons)
        self.assertIn("TRANSFORMATION_CONTRACT_INVALID", reasons)

    def test_only_get_read_only_acquisition_outside_repo_is_admitted(self):
        plan = fixture()
        plan["acquisition"].update(http_method="POST", output_outside_repository=False)
        resign(plan)
        self.assertIn("ACQUISITION_PROCEDURE_INVALID",
                      evaluate_plan(plan, {"terms.txt": TERMS}).reason_codes)

    def test_inventory_root_binds_every_byte_path_and_size(self):
        artifacts = {"raw/a.bin": b"alpha", "raw/b.bin": b"beta"}
        descriptors = [{"path": path, "bytes": len(body), "sha256": sha256_bytes(body)}
                       for path, body in artifacts.items()]
        result = verify_sealed_inventory(descriptors, artifacts, inventory_root(descriptors))
        self.assertEqual("SEALED", result.status)
        self.assertEqual(9, result.total_bytes)
        altered = copy.deepcopy(descriptors)
        altered[0]["bytes"] += 1
        self.assertEqual("FAIL_CLOSED", verify_sealed_inventory(
            altered, artifacts, inventory_root(descriptors)).status)

    def test_inventory_root_is_order_independent_and_paths_are_repository_safe(self):
        artifacts = {"raw/a.bin": b"alpha", "raw/b.bin": b"beta"}
        descriptors = [{"path": path, "bytes": len(body), "sha256": sha256_bytes(body)}
                       for path, body in artifacts.items()]
        self.assertEqual(inventory_root(descriptors), inventory_root(list(reversed(descriptors))))
        unsafe_artifacts = {"../private/raw.bin": b"secret"}
        unsafe = [{"path": "../private/raw.bin", "bytes": 6,
                   "sha256": sha256_bytes(b"secret")}]
        self.assertEqual("FAIL_CLOSED", verify_sealed_inventory(
            unsafe, unsafe_artifacts, inventory_root(unsafe)).status)

    def test_module_has_no_network_broker_model_process_or_write_capability(self):
        tree = ast.parse(Path(__file__).with_name("acquisition_protocol.py").read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertTrue(imports.isdisjoint({
            "MetaTrader5", "requests", "urllib3", "socket", "subprocess", "openai",
            "pathlib", "os", "shutil",
        }))


if __name__ == "__main__":
    unittest.main(verbosity=2)
