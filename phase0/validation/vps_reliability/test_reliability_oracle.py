import ast
import json
import unittest
from pathlib import Path

from phase0.validation.vps_reliability.reliability_oracle import (
    Policy,
    ReliabilityOracle,
    load_corpus,
    run_scenario,
    verify_corpus,
)


HERE = Path(__file__).resolve().parent
CORPUS = HERE / "reliability_corpus.json"
SOURCE = HERE / "reliability_oracle.py"


class ReliabilityCorpusTests(unittest.TestCase):
    def test_all_25_fault_matrix_scenarios_match_exact_trace(self):
        scenarios = load_corpus(CORPUS)
        self.assertEqual(25, len(scenarios))
        self.assertEqual([], verify_corpus(scenarios))

    def test_each_scenario_has_explicit_claim_limit_and_expected_trace(self):
        payload = json.loads(CORPUS.read_text(encoding="utf-8"))
        self.assertIn("not VPS run evidence", payload["claim_limit"])
        for scenario in payload["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                self.assertEqual(len(scenario["frames"]), len(scenario["expected"]))
                self.assertTrue(all(":" in label for label in scenario["expected"]))

    def test_thresholds_are_injected_validation_policy_not_global_claims(self):
        oracle = ReliabilityOracle(Policy(max_tick_age_ms=5, max_abs_clock_offset_ms=7))
        startup = oracle.evaluate({"event":"STARTUP", "tick_age_ms":5, "clock_offset_ms":7})
        self.assertEqual("HEALTHY:OK", startup.label())
        stale = oracle.evaluate({
            "event":"SAMPLE", "sequence":1, "monotonic_ms":2000,
            "tick_age_ms":6, "clock_offset_ms":7,
        })
        self.assertEqual("UNHEALTHY:STALE_TICK", stale.label())

    def test_safe_stop_is_latched(self):
        oracle = ReliabilityOracle()
        first = oracle.evaluate({"event":"STARTUP", "tradeapi_disabled":False})
        second = oracle.evaluate({"event":"STARTUP"})
        self.assertEqual("SAFE_STOP:EXTERNAL_PYTHON_TRADING_NOT_DISABLED", first.label())
        self.assertEqual("SAFE_STOP:SAFE_STOP_LATCHED", second.label())

    def test_corpus_rejects_duplicate_scenario_ids(self):
        payload = json.loads(CORPUS.read_text(encoding="utf-8"))
        payload["scenarios"].append(payload["scenarios"][0])
        temporary = HERE / "_duplicate_id_fixture.json"
        try:
            temporary.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unique"):
                load_corpus(temporary)
        finally:
            temporary.unlink(missing_ok=True)

    def test_oracle_has_no_broker_network_or_process_control_capability(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        forbidden_imports = {"MetaTrader5", "socket", "requests", "httpx", "subprocess"}
        forbidden_calls = {
            "initialize", "login", "order_check", "order_send", "symbol_select",
            "system", "popen", "exec", "eval", "compile"
        }
        imports = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        self.assertFalse(imports & forbidden_imports)
        self.assertFalse(calls & forbidden_calls)

    def test_build_change_never_becomes_healthy_without_validation_boundary(self):
        scenarios = {row["id"]: row for row in load_corpus(CORPUS)}
        trace = run_scenario(scenarios["RVM-022-build-validation-without-reprobe-is-insufficient"])
        self.assertEqual("UNHEALTHY:BUILD_CHANGE_WITHOUT_REPROBE_BOUNDARY", trace[-1])


if __name__ == "__main__":
    unittest.main()
