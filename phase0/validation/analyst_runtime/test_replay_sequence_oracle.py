import ast
import copy
import unittest
from datetime import timedelta
from pathlib import Path

from phase0.validation.analyst_runtime.replay_sequence_oracle import evaluate_registered_sequence
from phase0.validation.analyst_runtime.runtime_contract_oracle import derive_snapshot_id
from phase0.validation.analyst_runtime.test_runtime_contract import (
    NOW, common, no_trade_body, provider_response,
)


ROOT = "a" * 64
FAMILIES = ("TPB", "BRT", "FBR", "RSR", "MOC")


def sequence():
    exchanges = []
    for index, family in enumerate(FAMILIES):
        direction, regime = ("BUY", "RANGE") if family == "RSR" else ("BUY", "UP_TREND")
        payload = common(family, direction, regime)
        stamp = NOW + timedelta(seconds=index * 5)
        payload["analysis_id"] = f"123e4567-e89b-42d3-a456-42661417400{index}"
        payload["snapshot_time_utc"] = stamp.isoformat().replace("+00:00", "Z")
        payload["m15_bar_close_utc"] = payload["snapshot_time_utc"]
        payload["snapshot_id"] = derive_snapshot_id(payload)
        exchanges.append({
            "case_id": f"{family}-CHRONOLOGICAL",
            "kind": "PROVIDER_RESPONSE", "payload": payload,
            "response": provider_response(no_trade_body(payload)),
            "request_time": stamp + timedelta(milliseconds=100),
            "accept_time": stamp + timedelta(seconds=1),
            "state_fingerprint_at_send": "state-a",
            "state_fingerprint_at_accept": "state-a",
            "expected_advisory_accepted": True,
        })
    return exchanges


class ReplaySequenceOracleTests(unittest.TestCase):
    def test_five_family_chronological_sequence_passes_non_trading(self):
        result = evaluate_registered_sequence(
            bundle_admission_status="ADMITTED", bundle_root_sha256=ROOT,
            exchanges=sequence(),
        )
        self.assertEqual((result.status, result.accepted_advisories, result.rejected_responses),
                         ("PASS_NON_TRADING", 5, 0))
        self.assertFalse(result.trading_authorized)

    def test_unadmitted_bundle_blocks_entire_sequence(self):
        result = evaluate_registered_sequence(
            bundle_admission_status="REJECTED", bundle_root_sha256=ROOT,
            exchanges=sequence(),
        )
        self.assertEqual(result.status, "REJECTED")
        self.assertIn("REPLAY_BUNDLE_NOT_ADMITTED", result.reason_codes)

    def test_replay_and_inflight_state_change_are_expected_rejections(self):
        exchanges = sequence()
        replay = copy.deepcopy(exchanges[0])
        replay["case_id"] = "TPB-REPLAY-REJECT"
        replay["expected_advisory_accepted"] = False
        replay["request_time"] = exchanges[-1]["request_time"] + timedelta(seconds=1)
        replay["accept_time"] = exchanges[-1]["accept_time"] + timedelta(seconds=1)
        exchanges.append(replay)
        result = evaluate_registered_sequence(
            bundle_admission_status="ADMITTED", bundle_root_sha256=ROOT,
            exchanges=exchanges,
        )
        self.assertEqual(result.status, "PASS_NON_TRADING")
        self.assertIn("ANALYSIS_ID_INVALID_OR_DUPLICATE", result.case_results[-1][2])
        self.assertIn("SEQUENCE_SNAPSHOT_NOT_STRICTLY_INCREASING", result.case_results[-1][2])

        exchanges = sequence()
        exchanges[2]["state_fingerprint_at_accept"] = "changed"
        exchanges[2]["expected_advisory_accepted"] = False
        result = evaluate_registered_sequence(
            bundle_admission_status="ADMITTED", bundle_root_sha256=ROOT,
            exchanges=exchanges,
        )
        self.assertEqual(result.status, "PASS_NON_TRADING")
        self.assertIn("LOCAL_STATE_CHANGED", result.case_results[2][2])

    def test_registered_expectation_mismatch_fails_closed(self):
        exchanges = sequence(); exchanges[0]["expected_advisory_accepted"] = False
        result = evaluate_registered_sequence(
            bundle_admission_status="ADMITTED", bundle_root_sha256=ROOT,
            exchanges=exchanges,
        )
        self.assertIn("REGISTERED_EXPECTATION_MISMATCH", result.reason_codes)

    def test_local_no_call_has_no_response_and_never_authorizes(self):
        exchanges = sequence()
        exchanges.append({"case_id": "LOCAL-EVENT-LOCK", "kind": "LOCAL_NO_CALL",
                          "local_reason": "EVENT_LOCK", "response": None,
                          "expected_advisory_accepted": False})
        result = evaluate_registered_sequence(
            bundle_admission_status="ADMITTED", bundle_root_sha256=ROOT,
            exchanges=exchanges,
        )
        self.assertEqual((result.status, result.local_no_calls, result.trading_authorized),
                         ("PASS_NON_TRADING", 1, False))

    def test_sequence_requires_every_family_unique_ids_and_valid_times(self):
        exchanges = sequence(); exchanges[1]["case_id"] = exchanges[0]["case_id"]
        exchanges.pop()
        result = evaluate_registered_sequence(
            bundle_admission_status="ADMITTED", bundle_root_sha256=ROOT,
            exchanges=exchanges,
        )
        self.assertIn("CASE_ID_INVALID_OR_DUPLICATE", result.reason_codes)
        self.assertIn("FAMILY_SEQUENCE_INCOMPLETE", result.reason_codes)

    def test_oracle_has_no_network_broker_model_process_or_write_capability(self):
        tree = ast.parse(Path(__file__).with_name("replay_sequence_oracle.py").read_text(encoding="utf-8"))
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
