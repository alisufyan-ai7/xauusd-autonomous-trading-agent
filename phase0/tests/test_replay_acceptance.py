import copy
import json
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


if __name__ == "__main__":
    unittest.main()
