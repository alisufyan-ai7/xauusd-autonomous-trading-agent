import ast
import copy
import unittest
from pathlib import Path

from feature_oracle import Bar, completed_bars, fbr_reclaim, mirror_bars, moc_trigger, rsr_location
from registered_family_corpus import CASES, _long_passes, mirror_inputs


class RegisteredRawFamilyCorpusTests(unittest.TestCase):
    def test_registry_has_unique_ids_and_declared_35_case_coverage(self):
        self.assertEqual(len(CASES), 35)
        self.assertEqual(len({case.case_id for case in CASES}), 35)
        for family in ("TPB", "BRT", "FBR", "RSR", "MOC"):
            family_cases = [case for case in CASES if case.family == family]
            self.assertEqual(len(family_cases), 7)
            self.assertEqual({case.direction for case in family_cases if "PASS" in case.category}, {"LONG", "SHORT"})

    def test_every_registered_case_matches_frozen_terminal_result(self):
        for case in CASES:
            with self.subTest(case=case.case_id):
                result = case.evaluator(**copy.deepcopy(case.inputs))
                self.assertEqual((result.state, result.reason),
                                 (case.expected_state, case.expected_reason))

    def test_all_five_passes_are_exact_long_short_mirrors(self):
        passes = _long_passes()
        for family, (evaluator, inputs) in passes.items():
            with self.subTest(family=family):
                long_result = evaluator(**copy.deepcopy(inputs))
                short_result = evaluator(**mirror_inputs(inputs))
                self.assertEqual((long_result.state, short_result.state), ("PROPOSED", "PROPOSED"))
                self.assertEqual(long_result.expiry_bars, short_result.expiry_bars)
                self.assertAlmostEqual(float(long_result.entry) + float(short_result.entry), 220)
                self.assertAlmostEqual(float(long_result.stop) + float(short_result.stop), 220)

    def test_future_forming_bar_cannot_change_any_family_decision_slice(self):
        passes = _long_passes()
        for family, (evaluator, inputs) in passes.items():
            with self.subTest(family=family):
                base = copy.deepcopy(inputs)
                if family == "MOC":
                    decision_bars = [base["trigger"]]
                else:
                    decision_bars = list(base["following"])
                decision_time = max(bar.time + 900 for bar in decision_bars)
                future = Bar(decision_time, -999, 9999, -9999, 9999)
                visible = completed_bars(decision_bars + [future], decision_time, 900)
                self.assertEqual(visible, decision_bars)
                if family == "MOC":
                    base["trigger"] = visible[0]
                else:
                    base["following"] = visible
                expected = evaluator(**base)
                self.assertEqual(expected.state, "PROPOSED")

    def test_tpb_confirmation_exact_tick_boundary_and_one_side(self):
        evaluator, base = _long_passes()["TPB"]
        exact = copy.deepcopy(base)
        exact["following"] = [Bar(900, 111.8, 112.31, 111, 112.3)]
        self.assertEqual(evaluator(**exact).state, "PROPOSED")
        below = copy.deepcopy(exact)
        below["following"] = [Bar(900, 111.8, 112.31, 111, 112.299)]
        self.assertEqual(evaluator(**below).reason, "CONFIRMATION_MISSING")

    def test_brt_retest_window_exact_12_and_13(self):
        evaluator, base = _long_passes()["BRT"]
        exact = copy.deepcopy(base)
        exact["retest_h1"] = [Bar((i + 1) * 3600, 101, 102, 99.8, 100.5) for i in range(12)]
        self.assertEqual(evaluator(**exact).state, "PROPOSED")
        exact["retest_h1"].append(Bar(13 * 3600, 101, 102, 99.8, 100.5))
        self.assertEqual(evaluator(**exact).reason, "RETEST_INVALID")

    def test_fbr_excursion_exact_bounds_and_beyond(self):
        args = dict(direction="LONG", boundary=100, atr_h1=10, tick_size=.1, median_body_20=.5)
        for low in (99, 94):
            bars = [Bar(0, 100, 100.2, low, 99), Bar(900, 99, 101, low, 100.6)]
            self.assertTrue(fbr_reclaim(bars, **args))
        for low in (99.001, 93.999):
            bars = [Bar(0, 100, 100.2, low, 99), Bar(900, 99, 101, low, 100.6)]
            self.assertFalse(fbr_reclaim(bars, **args))

    def test_rsr_location_exact_15_percent_boundaries_and_one_side(self):
        self.assertTrue(rsr_location(103, 100, 120, "LONG"))
        self.assertFalse(rsr_location(103.001, 100, 120, "LONG"))
        self.assertTrue(rsr_location(117, 100, 120, "SHORT"))
        self.assertFalse(rsr_location(116.999, 100, 120, "SHORT"))

    def test_moc_rsi_exact_boundaries_and_one_side_with_mirror(self):
        _, base = _long_passes()["MOC"]
        trigger = base["trigger"]
        args = dict(direction="LONG", atr_m15=2, median_body_20=0, rsi14=55)
        self.assertTrue(moc_trigger(base["compression"], trigger, **args))
        self.assertFalse(moc_trigger(base["compression"], trigger, **dict(args, rsi14=54.999)))
        short_comp = mirror_bars(base["compression"], 110)
        short_trigger = mirror_bars([trigger], 110)[0]
        self.assertTrue(moc_trigger(short_comp, short_trigger, direction="SHORT", atr_m15=2, median_body_20=0, rsi14=45))
        self.assertFalse(moc_trigger(short_comp, short_trigger, direction="SHORT", atr_m15=2, median_body_20=0, rsi14=45.001))

    def test_registry_has_no_broker_network_model_or_process_imports(self):
        tree = ast.parse(Path(__file__).with_name("registered_family_corpus.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(imported.isdisjoint(
            {"MetaTrader5", "socket", "requests", "urllib", "httpx", "openai", "subprocess"}
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)
