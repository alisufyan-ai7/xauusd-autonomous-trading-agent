import copy
import ast
import json
import unittest
from decimal import Decimal
from pathlib import Path

from harness import (
    ALLOWED, COMMON_LOCKS, FAMILIES, TERMINAL, UNCERTAIN, EventClass, IntentMachine, State,
    classify_attribution, classify_event, closure_allowed, evaluate_setup, safe_exit_volume,
    select_candidate, setup_key,
)


ROOT = Path(__file__).parent
CORPUS = json.loads((ROOT / "setup_corpus.json").read_text(encoding="utf-8"))


class SetupCorpusTests(unittest.TestCase):
    def test_registered_corpus(self):
        self.assertEqual({c["family"] for c in CORPUS}, set(FAMILIES))
        for case in CORPUS:
            with self.subTest(case=case["id"]):
                result = evaluate_setup(case)
                self.assertEqual(result["result"], case["expected"])
                if reason := case.get("expected_reason"):
                    self.assertIn(reason, result["reason_codes"])

    def test_each_common_unknown_fails_closed(self):
        base = copy.deepcopy(CORPUS[0])
        for field, reason in COMMON_LOCKS.items():
            case = copy.deepcopy(base)
            case.pop(field)
            result = evaluate_setup(case)
            self.assertEqual(result["result"], "NO_TRADE")
            self.assertIn(reason, result["reason_codes"])

    def test_rr_exact_boundaries_and_one_side(self):
        base = copy.deepcopy(CORPUS[0])
        base.update(gross_rr="2.10", tp1_gross_rr="1.60", cost_r="0.10")
        self.assertEqual(evaluate_setup(base)["result"], "PASS_CANDIDATE")
        base["gross_rr"] = "2.099"
        self.assertIn("RR_INSUFFICIENT", evaluate_setup(base)["reason_codes"])
        base.update(gross_rr="2.10", tp1_gross_rr="1.599")
        self.assertIn("RR_INSUFFICIENT", evaluate_setup(base)["reason_codes"])

    def test_stop_exact_bounds_and_one_side(self):
        base = copy.deepcopy(CORPUS[0])
        base["stop_distance"] = "0.5"  # 0.25 * ATR_M15
        self.assertEqual(evaluate_setup(base)["result"], "PASS_CANDIDATE")
        base["stop_distance"] = "0.499"
        self.assertEqual(evaluate_setup(base)["result"], "NO_TRADE")
        base["stop_distance"] = "8.0"  # 2 * ATR_H1
        self.assertEqual(evaluate_setup(base)["result"], "PASS_CANDIDATE")
        base["stop_distance"] = "8.001"
        self.assertEqual(evaluate_setup(base)["result"], "NO_TRADE")

    def test_worse_cost_never_improves_result_or_rr(self):
        base = copy.deepcopy(CORPUS[0])
        prior = Decimal(evaluate_setup(base)["net_final_rr"])
        for cost in ("0.2", "0.5", "1.0", "3.0"):
            base["cost_r"] = cost
            current = evaluate_setup(base)
            self.assertLess(Decimal(current["net_final_rr"]), prior)
            prior = Decimal(current["net_final_rr"])

    def test_identical_input_one_key_and_safety_field_changes_key_policy(self):
        base = copy.deepcopy(CORPUS[0])
        self.assertEqual(setup_key(base), setup_key(copy.deepcopy(base)))
        for field in ("family", "direction", "trigger_bar_time", "anchor_swing_times", "level_prices"):
            changed = copy.deepcopy(base)
            changed[field] = "CHANGED" if field not in ("anchor_swing_times", "level_prices") else [999]
            self.assertNotEqual(setup_key(base), setup_key(changed))

    def test_selector_conflict_and_precedence(self):
        fbr = evaluate_setup(CORPUS[4])
        moc = evaluate_setup(CORPUS[8])
        moc["net_final_rr"] = str(Decimal(fbr["net_final_rr"]) - Decimal("0.09"))
        self.assertEqual(select_candidate([moc, fbr])["family"], "FBR")
        opposite = copy.deepcopy(moc)
        opposite["direction"] = "SHORT"
        self.assertIsNone(select_candidate([fbr, opposite]))


class ExecutionCorpusTests(unittest.TestCase):
    def test_harness_has_no_broker_or_network_imports(self):
        tree = ast.parse((ROOT / "harness.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(imported.isdisjoint({"MetaTrader5", "socket", "requests", "urllib", "httpx"}))

    def test_every_unlisted_transition_incidents(self):
        for source in State:
            for target in State:
                if target in ALLOWED.get(source, set()):
                    continue
                machine = IntentMachine(state=source)
                self.assertEqual(machine.transition(target, expected_version=0), State.INCIDENT)

    def test_all_allowed_transitions_are_deterministic(self):
        for source, targets in ALLOWED.items():
            for target in targets:
                machine = IntentMachine(state=source)
                self.assertEqual(machine.transition(target, expected_version=0), target)

    def test_single_attempt_and_duplicate_claim(self):
        m = IntentMachine(state=State.READY)
        self.assertEqual(m.transition(State.SUBMITTING, expected_version=0), State.SUBMITTING)
        self.assertTrue(m.claim_call())
        self.assertFalse(m.claim_call())

    def test_compare_and_swap_conflict_incidents(self):
        m = IntentMachine(state=State.READY, version=4)
        self.assertEqual(m.transition(State.SUBMITTING, expected_version=3), State.INCIDENT)

    def test_timeout_later_fill_reconciles_original(self):
        m = IntentMachine(state=State.SUBMITTING, attempt_committed=True, call_claimed=True)
        m.transition(State.SUBMISSION_UNCERTAIN, expected_version=0)
        # Recovery does not submit: broker evidence maps the existing intent externally.
        self.assertEqual(m.restart_outcome(), State.QUARANTINED)
        self.assertFalse(m.claim_call())

    def test_ack_without_evidence_uncertain(self):
        m = IntentMachine(state=State.ACKNOWLEDGED)
        self.assertEqual(m.transition(State.SUBMISSION_UNCERTAIN, expected_version=0), State.SUBMISSION_UNCERTAIN)

    def test_restart_from_every_state_is_fail_closed(self):
        expected = {
            State.OBSERVED: State.OBSERVED, State.PROPOSED: State.PROPOSED,
            State.REJECTED: State.REJECTED, State.APPROVED: State.APPROVED,
            State.READY: State.APPROVED, State.SUBMITTING: State.QUARANTINED,
            State.SUBMISSION_UNCERTAIN: State.QUARANTINED,
            State.ACKNOWLEDGED: State.QUARANTINED,
            State.RECONCILED_OPEN: State.QUARANTINED,
            State.MANAGING: State.QUARANTINED,
            State.EXIT_SUBMITTING: State.QUARANTINED,
            State.EXIT_UNCERTAIN: State.QUARANTINED,
            State.RECONCILED_CLOSED: State.RECONCILED_CLOSED,
            State.EXPIRED: State.EXPIRED, State.CANCELLED: State.CANCELLED,
            State.QUARANTINED: State.QUARANTINED, State.INCIDENT: State.INCIDENT,
        }
        for state in State:
            result = IntentMachine(state=state).restart_outcome()
            self.assertEqual(result, expected[state])
            self.assertNotEqual(result, State.READY)

    def test_event_class_precedence_is_total(self):
        self.assertIsNone(classify_event(EventClass.NORMAL_TRANSITION))
        self.assertEqual(State.QUARANTINED, classify_event(EventClass.SAFETY_OBSERVATION))
        self.assertEqual(State.INCIDENT, classify_event(EventClass.PROTOCOL_INVALID))
        self.assertEqual(State.INCIDENT, classify_event(EventClass.EVIDENCE_CORRUPTION))
        self.assertEqual(
            State.INCIDENT,
            classify_event(EventClass.SAFETY_OBSERVATION, EventClass.PROTOCOL_INVALID),
        )

    def test_terminal_cannot_reactivate(self):
        for state in TERMINAL:
            self.assertEqual(IntentMachine(state=state).transition(State.READY, expected_version=0), State.INCIDENT)

    def test_uncertain_never_allows_call(self):
        for state in UNCERTAIN:
            self.assertFalse(IntentMachine(state=state, attempt_committed=True).claim_call())

    def test_attribution_requires_all_agreeing_fields(self):
        full = {k: True for k in ("account", "symbol", "magic", "fingerprint", "direction", "volume", "linkage")}
        self.assertEqual(classify_attribution(full), "OWNED_UNIQUE")
        collision = dict(full, linkage=False)
        self.assertEqual(classify_attribution(collision), "CONFLICTING")
        self.assertEqual(classify_attribution({"known_external": True}), "KNOWN_EXTERNAL")
        self.assertEqual(classify_attribution({}), "UNKNOWN")

    def test_closure_conservation_and_history(self):
        self.assertTrue(closure_allowed(open_volume=Decimal("0"), entry_volume=Decimal("0.02"), exit_volume=Decimal("0.02"), history_complete=True))
        self.assertFalse(closure_allowed(open_volume=Decimal("0"), entry_volume=Decimal("0.02"), exit_volume=Decimal("0.01"), history_complete=True))
        self.assertFalse(closure_allowed(open_volume=Decimal("0"), entry_volume=Decimal("0.02"), exit_volume=Decimal("0.02"), history_complete=False))

    def test_exit_cannot_invert_or_increase_gross(self):
        self.assertTrue(safe_exit_volume(Decimal("0.01"), Decimal("0.02")))
        self.assertTrue(safe_exit_volume(Decimal("0.02"), Decimal("0.02")))
        self.assertFalse(safe_exit_volume(Decimal("0.03"), Decimal("0.02")))
        self.assertFalse(safe_exit_volume(Decimal("0"), Decimal("0.02")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
