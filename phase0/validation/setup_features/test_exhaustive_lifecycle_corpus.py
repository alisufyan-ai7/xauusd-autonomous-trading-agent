import ast
import copy
import unittest
from dataclasses import replace
from pathlib import Path

from exhaustive_lifecycle_corpus import (
    CANCELLATION_CONDITIONS, COUNTS, DECISION_TIME, DIRECTIONS, FAMILIES,
    FIXTURES, LIFECYCLE_PATHS, PERIODS, AdvisoryLifecycle, advance_lifecycle,
    fixture_digest, fixture_reasons, run_path,
)
from feature_oracle import Bar, completed_bars, validate_series


class ExhaustiveLifecycleCorpusTests(unittest.TestCase):
    def test_registry_has_ten_full_histories_and_ninety_unique_paths(self):
        self.assertEqual(len(FIXTURES), 10)
        self.assertEqual(len({fixture.fixture_id for fixture in FIXTURES}), 10)
        self.assertEqual({(fixture.family, fixture.direction) for fixture in FIXTURES},
                         {(family, direction) for family in FAMILIES for direction in DIRECTIONS})
        self.assertEqual(len(LIFECYCLE_PATHS), 90)
        self.assertEqual(len({path.path_id for path in LIFECYCLE_PATHS}), 90)

    def test_every_fixture_has_exact_completed_300_500_1000_histories(self):
        for fixture in FIXTURES:
            with self.subTest(fixture=fixture.fixture_id):
                self.assertEqual((len(fixture.h4), len(fixture.h1), len(fixture.m15)),
                                 (COUNTS["H4"], COUNTS["H1"], COUNTS["M15"]))
                for name, bars in (("H4", fixture.h4), ("H1", fixture.h1), ("M15", fixture.m15)):
                    self.assertEqual(len(completed_bars(bars, DECISION_TIME, PERIODS[name])), COUNTS[name])

    def test_all_full_history_candidates_match_golden_terminal_result(self):
        for fixture in FIXTURES:
            with self.subTest(fixture=fixture.fixture_id):
                self.assertEqual(fixture_reasons(fixture), ())
                result = fixture.evaluator(**copy.deepcopy(fixture.evaluator_inputs))
                self.assertEqual((result.family, result.direction, result.state, result.reason),
                                 (fixture.family, fixture.direction, "PROPOSED", "GOLDEN_SLICE_PASS"))

    def test_every_cancellation_condition_is_exhaustive_by_family_and_direction(self):
        cancellation_paths = [path for path in LIFECYCLE_PATHS if path.terminal_event in CANCELLATION_CONDITIONS]
        self.assertEqual(len(cancellation_paths), 80)
        for family in FAMILIES:
            for direction in DIRECTIONS:
                observed = {path.terminal_event for path in cancellation_paths
                            if path.family == family and path.direction == direction}
                self.assertEqual(observed, set(CANCELLATION_CONDITIONS))

    def test_all_ninety_paths_reach_frozen_terminal_state_and_reason(self):
        for path in LIFECYCLE_PATHS:
            with self.subTest(path=path.path_id):
                terminal = run_path(path)
                self.assertEqual((terminal.state, terminal.terminal_reason),
                                 (path.expected_state, path.expected_reason))

    def test_terminal_paths_cannot_reactivate_and_event_time_is_strict(self):
        terminal = run_path(LIFECYCLE_PATHS[0])
        with self.assertRaisesRegex(ValueError, "terminal lifecycle"):
            advance_lifecycle(terminal, "PROPOSE", 4)
        state = AdvisoryLifecycle("fixture")
        state = advance_lifecycle(state, "PROPOSE", 1)
        with self.assertRaisesRegex(ValueError, "non-monotonic"):
            advance_lifecycle(state, "RESERVE", 1)

    def test_invalid_ordering_and_unknown_events_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "invalid lifecycle"):
            advance_lifecycle(AdvisoryLifecycle("fixture"), "FILLED", 1)
        with self.assertRaisesRegex(ValueError, "invalid lifecycle"):
            advance_lifecycle(AdvisoryLifecycle("fixture"), "UNKNOWN", 1)

    def test_future_forming_bar_cannot_enter_any_full_history_information_set(self):
        toxic = Bar(DECISION_TIME, -999, 9999, -9999, 9999)
        for fixture in FIXTURES:
            for name, bars in (("H4", fixture.h4), ("H1", fixture.h1), ("M15", fixture.m15)):
                visible = completed_bars([*bars, toxic], DECISION_TIME, PERIODS[name])
                self.assertEqual(tuple(visible), bars)

    def test_full_history_digest_is_stable_and_binds_every_bar(self):
        for fixture in FIXTURES:
            digest = fixture_digest(fixture)
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertEqual(digest, fixture_digest(fixture))
        first = FIXTURES[0]
        changed_h4 = list(first.h4)
        changed_h4[0] = replace(changed_h4[0], close=changed_h4[0].close + 0.001)
        self.assertNotEqual(fixture_digest(first), fixture_digest(replace(first, h4=tuple(changed_h4))))

    def test_malformed_ohlc_duplicate_and_gap_fail_series_health(self):
        fixture = FIXTURES[0]
        bad = list(fixture.m15)
        bad[-1] = replace(bad[-1], high=bad[-1].low - 1)
        self.assertEqual(validate_series(bad, decision_time=DECISION_TIME,
                                         period_seconds=PERIODS["M15"], minimum=COUNTS["M15"]),
                         (False, "OHLC_INVALID"))
        duplicate = list(fixture.h1)
        duplicate[-1] = replace(duplicate[-1], time=duplicate[-2].time)
        self.assertEqual(validate_series(duplicate, decision_time=DECISION_TIME,
                                         period_seconds=PERIODS["H1"], minimum=COUNTS["H1"]),
                         (False, "TIMESTAMP_DUPLICATE_OR_NONMONOTONIC"))
        gap = list(fixture.h4)
        gap[-1] = replace(gap[-1], time=gap[-1].time + PERIODS["H4"])
        self.assertEqual(validate_series(gap, decision_time=DECISION_TIME + PERIODS["H4"],
                                         period_seconds=PERIODS["H4"], minimum=COUNTS["H4"]),
                         (False, "UNEXPLAINED_GAP"))

    def test_module_has_no_broker_network_model_process_or_filesystem_write_capability(self):
        source = Path(__file__).with_name("exhaustive_lifecycle_corpus.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                calls.add(node.func.attr if isinstance(node.func, ast.Attribute)
                          else node.func.id if isinstance(node.func, ast.Name) else "")
        self.assertTrue(imported.isdisjoint(
            {"MetaTrader5", "socket", "requests", "urllib", "httpx", "openai", "subprocess"}
        ))
        self.assertTrue(calls.isdisjoint(
            {"open", "write_text", "write_bytes", "order_send", "order_check", "Popen", "run"}
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)
