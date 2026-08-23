from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
import unittest

from matrix_oracle import evaluate_matrix


MATRIX = Path(__file__).resolve().parents[2] / "GATE_0_FINAL_EVIDENCE_MATRIX_R24.json"


class FinalGateMatrixTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(MATRIX.read_text(encoding="utf-8"))

    def test_published_matrix_is_exactly_five_pass_nine_pending(self):
        result = evaluate_matrix(self.payload)
        self.assertEqual("INCOMPLETE", result.verdict)
        self.assertEqual((5, 9, 0), (result.passed, result.pending, result.failed))

    def test_any_pending_item_prevents_pass(self):
        self.assertEqual("INCOMPLETE", evaluate_matrix(self.payload).verdict)

    def test_all_pass_is_the_only_pass_path(self):
        payload = copy.deepcopy(self.payload)
        for row in payload["items"]:
            row["status"] = "PASS"
        payload["gate_0_verdict"] = "PASS"
        self.assertEqual("PASS", evaluate_matrix(payload).verdict)

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
            self.assertIn("ITEM_INVENTORY_INVALID", evaluate_matrix(payload).reasons)

    def test_declared_verdict_cannot_overstate_evidence(self):
        payload = copy.deepcopy(self.payload)
        payload["gate_0_verdict"] = "PASS"
        self.assertIn("DECLARED_VERDICT_MISMATCH", evaluate_matrix(payload).reasons)

    def test_external_python_and_trading_guards_are_mandatory(self):
        payload = copy.deepcopy(self.payload)
        payload["trading_authorized"] = True
        payload["external_python_trading_required_state"] = "ENABLED"
        reasons = evaluate_matrix(payload).reasons
        self.assertIn("TRADING_AUTHORIZATION_INVALID", reasons)
        self.assertIn("EXTERNAL_PYTHON_STATE_INVALID", reasons)

    def test_no_owner_action_may_be_silently_requested(self):
        payload = copy.deepcopy(self.payload)
        payload["owner_actions_requested_now"] = ["restart"]
        self.assertIn("UNEXPECTED_OWNER_ACTION_REQUEST", evaluate_matrix(payload).reasons)

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
