import ast
import json
import tempfile
import unittest
from pathlib import Path

from phase0.validation.exposure_preflight.exposure_preflight import capture, verify_reconciliation


class Rec:
    def __init__(self, **values):
        self.values = values

    def _asdict(self):
        return self.values


class FakeAPI:
    attached = True
    connected = True
    disabled = True
    positions = ()
    orders = ()

    @classmethod
    def initialize(cls):
        return cls.attached

    @classmethod
    def shutdown(cls):
        return True

    @classmethod
    def terminal_info(cls):
        return Rec(connected=cls.connected, tradeapi_disabled=cls.disabled)

    @classmethod
    def positions_get(cls):
        return cls.positions

    @classmethod
    def orders_get(cls):
        return cls.orders


class ExposurePreflightTests(unittest.TestCase):
    def setUp(self):
        FakeAPI.attached = True
        FakeAPI.connected = True
        FakeAPI.disabled = True
        FakeAPI.positions = ()
        FakeAPI.orders = ()

    def _capture(self, phase="PRE_DRILL"):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        output = Path(temp.name) / "private"
        return capture(FakeAPI, output, phase), output

    def test_zero_exposure_passes_and_is_hash_chained(self):
        result, output = self._capture()
        self.assertEqual("PASS_NO_OPEN_EXPOSURE", result["status"])
        rows = [json.loads(line) for line in
                (output / "exposure_preflight_records.jsonl").read_text().splitlines()]
        self.assertEqual(0, rows[0]["positions_count"])
        self.assertEqual(0, rows[0]["pending_orders_count"])
        second = capture(FakeAPI, output, "POST_RECOVERY")
        self.assertEqual("PASS_NO_OPEN_EXPOSURE", second["status"])
        rows = [json.loads(line) for line in
                (output / "exposure_preflight_records.jsonl").read_text().splitlines()]
        self.assertEqual(rows[0]["record_sha256"], rows[1]["prior_record_sha256"])
        reconciled = verify_reconciliation(output)
        self.assertEqual("PASS_RECONCILED", reconciled["status"])
        self.assertEqual(rows[0]["record_sha256"], reconciled["pre_record_sha256"])
        self.assertEqual(rows[1]["record_sha256"], reconciled["post_record_sha256"])

    def test_reconciliation_requires_exact_safe_pre_post_pair(self):
        _, output = self._capture()
        self.assertIn("EXACT_PRE_POST_PAIR_REQUIRED", verify_reconciliation(output)["reasons"])
        capture(FakeAPI, output, "POST_RECOVERY")
        capture(FakeAPI, output, "POST_RECOVERY")
        result = verify_reconciliation(output)
        self.assertEqual("FAIL_CLOSED", result["status"])
        self.assertIn("EXACT_PRE_POST_PAIR_REQUIRED", result["reasons"])

    def test_reconciliation_binds_latest_retry_pair_without_deleting_history(self):
        old_pre, output = self._capture()
        current_pre = capture(FakeAPI, output, "PRE_DRILL")
        current_post = capture(FakeAPI, output, "POST_RECOVERY")
        result = verify_reconciliation(
            output, pre_sha256=current_pre["record_sha256"],
            post_sha256=current_post["record_sha256"],
        )
        self.assertEqual("PASS_RECONCILED", result["status"], result["reasons"])
        self.assertNotEqual(old_pre["record_sha256"], result["pre_record_sha256"])
        stale = verify_reconciliation(
            output, pre_sha256=old_pre["record_sha256"],
            post_sha256=current_post["record_sha256"],
        )
        self.assertIn("BOUND_PAIR_NOT_LATEST_CONTIGUOUS", stale["reasons"])

    def test_positions_or_orders_fail_closed(self):
        FakeAPI.positions = (object(),)
        self.assertIn("OPEN_POSITIONS_PRESENT", self._capture()[0]["reasons"])
        FakeAPI.positions = ()
        FakeAPI.orders = (object(),)
        self.assertIn("PENDING_ORDERS_PRESENT", self._capture()[0]["reasons"])

    def test_unknown_or_unhealthy_state_fails_closed(self):
        FakeAPI.positions = None
        self.assertIn("EXPOSURE_STATE_UNKNOWN", self._capture()[0]["reasons"])
        FakeAPI.positions = ()
        FakeAPI.connected = False
        self.assertIn("TERMINAL_NOT_CONNECTED", self._capture()[0]["reasons"])
        FakeAPI.connected = True
        FakeAPI.disabled = False
        self.assertIn("EXTERNAL_PYTHON_TRADING_NOT_DISABLED", self._capture()[0]["reasons"])
        FakeAPI.disabled = True
        FakeAPI.attached = False
        self.assertIn("MT5_INITIALIZE_FAILED", self._capture()[0]["reasons"])

    def test_tampered_chain_and_repository_output_fail_closed(self):
        _, output = self._capture()
        chain = output / "exposure_preflight_records.jsonl"
        chain.write_text(chain.read_text().replace('"positions_count":0', '"positions_count":1'))
        with self.assertRaisesRegex(ValueError, "chain invalid"):
            capture(FakeAPI, output, "POST_RECOVERY")
        with self.assertRaisesRegex(ValueError, "outside repository"):
            capture(FakeAPI, Path(__file__).parent / "forbidden", "PRE_DRILL")

    def test_capability_is_read_only_and_non_messaging(self):
        directory = Path(__file__).resolve().parent
        forbidden_imports = {"requests", "socket", "smtplib", "subprocess", "telegram"}
        forbidden_calls = {
            "order_send", "order_check", "order_calc_margin", "login", "symbol_select",
            "sendmail", "send_message", "system", "popen", "run", "Popen",
        }
        for name in ("readonly_mt5.py", "exposure_preflight.py"):
            tree = ast.parse((directory / name).read_text(encoding="utf-8"))
            imports = set()
            calls = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])
                elif isinstance(node, ast.Call):
                    calls.add(node.func.id if isinstance(node.func, ast.Name)
                              else node.func.attr if isinstance(node.func, ast.Attribute) else "")
            self.assertFalse(imports & forbidden_imports)
            self.assertFalse(calls & forbidden_calls)
        adapter = (directory / "readonly_mt5.py").read_text(encoding="utf-8")
        for forbidden in forbidden_calls:
            self.assertNotIn(forbidden, adapter)


if __name__ == "__main__":
    unittest.main()
