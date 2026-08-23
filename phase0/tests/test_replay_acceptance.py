import copy
import json
import math
import unittest
from pathlib import Path

from replay_acceptance_evaluator import evaluate


FIXTURES = Path(__file__).with_name("replay_acceptance_vectors.json")


class ReplayAcceptanceVectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vectors = json.loads(FIXTURES.read_text(encoding="utf-8"))

    def test_all_frozen_vectors(self):
        self.assertEqual([v["id"] for v in self.vectors], [f"RA-{i:03d}" for i in range(1, 16)])
        for vector in self.vectors:
            with self.subTest(vector=vector["id"]):
                result = evaluate(copy.deepcopy(vector["input"]))
                self.assertEqual(result.verdict, vector["expected_verdict"])
                self.assertEqual(list(result.failures), vector.get("expected_failures", []))
                self.assertEqual(list(result.insufficient_evidence), vector.get("expected_insufficient", []))

    def test_nonfinite_metrics_fail_closed(self):
        record = copy.deepcopy(self.vectors[0]["input"])
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                altered = copy.deepcopy(record)
                altered["metrics"]["oos_mean_r"] = value
                result = evaluate(altered)
                self.assertEqual("REJECT", result.verdict)
                self.assertIn("metric:oos_mean_r_invalid", result.failures)

    def test_probability_ranges_drawdown_and_ci_are_coherent(self):
        cases = (
            ("dsr_probability", 1.01, "metric:dsr_probability_outside_0_1"),
            ("pbo", -0.01, "metric:pbo_outside_0_1"),
            ("max_drawdown_usd", -1, "metric:max_drawdown_usd_negative"),
            ("ci95_lower_r", 0.11, "metric:ci95_lower_above_mean"),
        )
        for metric, value, expected in cases:
            with self.subTest(metric=metric):
                altered = copy.deepcopy(self.vectors[0]["input"])
                altered["metrics"][metric] = value
                result = evaluate(altered)
                self.assertEqual("REJECT", result.verdict)
                self.assertIn(expected, result.failures)


if __name__ == "__main__":
    unittest.main()
