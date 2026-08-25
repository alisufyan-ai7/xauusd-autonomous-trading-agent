from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest

from matrix_oracle import (
    CLAIM_PROVENANCE, FROZEN_ADMITTED_RECEIPTS, REQUIRED_CLAIMS, evaluate_matrix,
)


ROOT = Path(__file__).resolve().parents[3]
MATRIX = ROOT / "phase0" / "GATE_0_FINAL_EVIDENCE_MATRIX_R28.json"


def artifact_hashes(payload):
    paths = {
        receipt["artifact_path"]
        for row in payload["items"] for receipt in row["receipts"]
    }
    return {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in paths
    }


def receipt(item_id, claim, index=0):
    path = f"synthetic/{item_id}-{index}.json"
    digest = hashlib.sha256(path.encode()).hexdigest()
    return {
        "claim_type": claim,
        "artifact_path": path,
        "artifact_sha256": digest,
        "evidence_status": "ADMITTED",
        "observed_utc": "2026-08-23T00:00:00Z",
        "provenance": CLAIM_PROVENANCE[claim],
        "private_source": True,
        "published_hash_only": True,
        "trading_authorized": False,
        "external_python_trading_disabled": True,
        "claim_limit": "Synthetic unit-test receipt only.",
    }


class FinalGateMatrixTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(MATRIX.read_text(encoding="utf-8"))
        self.hashes = artifact_hashes(self.payload)

    def test_published_matrix_is_receipt_bound_seven_pass_seven_pending(self):
        result = evaluate_matrix(self.payload, self.hashes)
        self.assertEqual("INCOMPLETE", result.verdict)
        self.assertEqual((7, 7, 0), (result.passed, result.pending, result.failed))

    def test_declared_all_pass_without_receipts_fails_closed(self):
        payload = copy.deepcopy(self.payload)
        for row in payload["items"]:
            row["status"] = "PASS"
        payload["gate_0_verdict"] = "PASS"
        result = evaluate_matrix(payload, self.hashes)
        self.assertEqual("FAIL_CLOSED", result.verdict)
        self.assertTrue(any(reason.endswith("STATUS_DERIVATION_MISMATCH")
                            for reason in result.reasons))

    def test_self_asserted_pending_receipts_cannot_promote_gate(self):
        payload = copy.deepcopy(self.payload)
        hashes = {}
        for row in payload["items"]:
            row["receipts"] = []
            for index, claim in enumerate(REQUIRED_CLAIMS[row["id"]]):
                row["receipts"].append(receipt(row["id"], claim, index))
                item = row["receipts"][-1]
                hashes[item["artifact_path"]] = item["artifact_sha256"]
            row["status"] = "PASS"
        payload["gate_0_verdict"] = "PASS"
        result = evaluate_matrix(payload, hashes)
        self.assertEqual("FAIL_CLOSED", result.verdict)
        self.assertTrue(any(reason.endswith("RECEIPT_NOT_IN_FROZEN_REGISTRY")
                            for reason in result.reasons))

    def test_published_pass_receipts_are_exactly_the_frozen_registry(self):
        observed = {
            receipt["claim_type"]: (
                receipt["artifact_path"], receipt["artifact_sha256"],
                receipt["provenance"],
            )
            for row in self.payload["items"] for receipt in row["receipts"]
        }
        self.assertEqual(FROZEN_ADMITTED_RECEIPTS, observed)

    def test_missing_or_modified_artifact_fails_closed(self):
        payload = copy.deepcopy(self.payload)
        row = next(item for item in payload["items"] if item["status"] == "PASS")
        path = row["receipts"][0]["artifact_path"]
        missing = dict(self.hashes)
        del missing[path]
        self.assertTrue(any("ARTIFACT_HASH_MISMATCH" in reason
                            for reason in evaluate_matrix(payload, missing).reasons))
        changed = dict(self.hashes)
        changed[path] = "0" * 64
        self.assertTrue(any("ARTIFACT_HASH_MISMATCH" in reason
                            for reason in evaluate_matrix(payload, changed).reasons))

    def test_requirement_registry_and_provenance_are_frozen(self):
        payload = copy.deepcopy(self.payload)
        row = payload["items"][0]
        row["required_claims"] = ["EXHAUSTIVE_SETUP_CORPUS"]
        row["receipts"][0]["provenance"] = "UNVERIFIED"
        reasons = evaluate_matrix(payload, self.hashes).reasons
        self.assertIn("G0-01_REQUIREMENT_REGISTRY_MISMATCH", reasons)
        self.assertIn("G0-01_PROVENANCE_INVALID", reasons)

    def test_private_source_must_publish_hash_only(self):
        payload = copy.deepcopy(self.payload)
        row = payload["items"][0]
        row["receipts"][0]["published_hash_only"] = False
        self.assertIn("G0-01_PRIVATE_PUBLICATION_INVALID",
                      evaluate_matrix(payload, self.hashes).reasons)

    def test_unsafe_path_duplicate_claim_and_bad_time_fail(self):
        payload = copy.deepcopy(self.payload)
        row = payload["items"][0]
        duplicate = copy.deepcopy(row["receipts"][0])
        duplicate["artifact_path"] = "../private/raw.json"
        duplicate["observed_utc"] = "2026-08-23"
        row["receipts"].append(duplicate)
        reasons = evaluate_matrix(payload, self.hashes).reasons
        self.assertIn("G0-01_DUPLICATE_CLAIM_RECEIPT", reasons)
        self.assertIn("G0-01_ARTIFACT_PATH_INVALID", reasons)
        self.assertIn("G0-01_OBSERVED_TIME_INVALID", reasons)

    def test_external_python_trading_and_owner_action_guards_are_mandatory(self):
        payload = copy.deepcopy(self.payload)
        payload["trading_authorized"] = True
        payload["external_python_trading_required_state"] = "ENABLED"
        payload["owner_actions_requested_now"] = ["restart"]
        reasons = evaluate_matrix(payload, self.hashes).reasons
        self.assertIn("TRADING_AUTHORIZATION_INVALID", reasons)
        self.assertIn("EXTERNAL_PYTHON_STATE_INVALID", reasons)
        self.assertIn("UNEXPECTED_OWNER_ACTION_REQUEST", reasons)

    def test_missing_duplicate_or_extra_item_fails_closed(self):
        for mutate in ("missing", "duplicate", "extra"):
            payload = copy.deepcopy(self.payload)
            if mutate == "missing":
                payload["items"].pop()
            elif mutate == "duplicate":
                payload["items"][-1]["id"] = "G0-01"
            else:
                payload["items"].append(copy.deepcopy(payload["items"][-1]))
                payload["items"][-1]["id"] = "G0-15"
            self.assertIn("ITEM_INVENTORY_INVALID",
                          evaluate_matrix(payload, self.hashes).reasons)

    def test_oracle_has_no_network_broker_model_process_or_write_capability(self):
        tree = ast.parse(Path(__file__).with_name("matrix_oracle.py").read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertTrue(imports.isdisjoint({
            "MetaTrader5", "requests", "urllib3", "socket", "subprocess", "openai",
            "pathlib", "os", "shutil", "smtplib", "telegram",
        }))


if __name__ == "__main__":
    unittest.main(verbosity=2)
