import ast
import unittest
from decimal import Decimal
from pathlib import Path

from phase0.validation.operational_policy.operational_policy_oracle import (
    MarginInputs,
    Verdict,
    a1_critical_alert,
    combined_new_risk_gate,
    emergency_e1,
    evaluate_m1,
    evaluate_v1,
    p1_can_create_new_epoch,
)


D = Decimal
SOURCE = Path(__file__).with_name("operational_policy_oracle.py")


def margin(**changes):
    values = {
        "projected_equity": D("15000"),
        "used_margin_before": D("800"),
        "incremental_margin": D("200"),
        "spread_stress": D("1000"),
        "slippage_stress": D("1000"),
        "gap_stress": D("900"),
        "cost_stress": D("100"),
    }
    values.update(changes)
    return MarginInputs(**values)


class OperationalPolicyTests(unittest.TestCase):
    def test_v1_exact_cap_and_grid_pass(self):
        verdict = evaluate_v1(D("0.01"), broker_min=D("0.01"), broker_step=D("0.01"), account_validated_cap=D("0.05"))
        self.assertEqual(Verdict(True, "V1_PASS"), verdict)

    def test_v1_above_cap_or_broker_minimum_above_cap_rejects(self):
        self.assertFalse(evaluate_v1(D("0.02"), broker_min=D("0.01"), broker_step=D("0.01"), account_validated_cap=D("0.05")).accepted)
        self.assertEqual("BROKER_MINIMUM_EXCEEDS_V1_CAP", evaluate_v1(D("0.02"), broker_min=D("0.02"), broker_step=D("0.01"), account_validated_cap=D("0.05")).reason)

    def test_v1_invalid_or_off_grid_rejects(self):
        self.assertEqual("VOLUME_GRID_FAILED", evaluate_v1(D("0.008"), broker_min=D("0.005"), broker_step=D("0.002"), account_validated_cap=D("0.01")).reason)
        self.assertEqual("VOLUME_INPUT_INVALID", evaluate_v1(None, broker_min=D("0.01"), broker_step=D("0.01"), account_validated_cap=D("0.01")).reason)

    def test_m1_stressed_boundary_passes_exactly(self):
        # Current: 1500% / 93.33%; stressed: 1000% / 90% exactly.
        self.assertEqual(Verdict(True, "M1_PASS"), evaluate_m1(margin()))

    def test_m1_current_threshold_failure_rejects(self):
        result = evaluate_m1(margin(projected_equity=D("9999"), spread_stress=D("0"), slippage_stress=D("0"), gap_stress=D("0"), cost_stress=D("0")))
        self.assertEqual("M1_CURRENT_THRESHOLD_FAILED", result.reason)

    def test_m1_stressed_one_cent_below_boundary_rejects(self):
        result = evaluate_m1(margin(cost_stress=D("100.01")))
        self.assertEqual("M1_STRESSED_THRESHOLD_FAILED", result.reason)

    def test_m1_zero_used_margin_still_checks_free_margin(self):
        result = evaluate_m1(margin(used_margin_before=D("0"), incremental_margin=D("0"), spread_stress=D("0"), slippage_stress=D("0"), gap_stress=D("0"), cost_stress=D("0")))
        self.assertTrue(result.accepted)

    def test_m1_missing_nonfinite_or_negative_input_rejects(self):
        self.assertEqual("MARGIN_INPUT_INVALID", evaluate_m1(margin(gap_stress=None)).reason)
        self.assertEqual("MARGIN_INPUT_INVALID", evaluate_m1(margin(incremental_margin=D("NaN"))).reason)
        self.assertEqual("MARGIN_INPUT_INVALID", evaluate_m1(margin(cost_stress=D("-0.01"))).reason)

    def test_m1_cannot_override_any_other_governor_limit(self):
        v1 = Verdict(True, "V1_PASS")
        m1 = Verdict(True, "M1_PASS")
        result = combined_new_risk_gate(v1=v1, m1=m1, other_governor_limits_clear=False)
        self.assertEqual(Verdict(False, "OTHER_RISK_GOVERNOR_LIMIT_FAILED"), result)

    def test_combined_pass_has_no_trade_authority(self):
        result = combined_new_risk_gate(v1=Verdict(True, "V1_PASS"), m1=Verdict(True, "M1_PASS"), other_governor_limits_clear=True)
        self.assertEqual("POLICY_TEST_PASS_NOT_TRADE_AUTHORITY", result.reason)

    def test_e1_never_emits_cancel_modify_or_close(self):
        response = emergency_e1(True)
        self.assertTrue(response["block_new_risk"])
        self.assertEqual((), response["broker_requests"])
        self.assertFalse(response["automatic_unknown_close"])

    def test_p1_requires_every_human_and_health_condition(self):
        complete = dict(human_authorized=True, minimum_hold_complete=True, reconciliation_complete=True, diagnostics_pass=True, alert_acknowledged=True, fresh_preflight_pass=True, old_intent_terminal=True)
        self.assertTrue(p1_can_create_new_epoch(**complete))
        for key in complete:
            with self.subTest(missing=key):
                changed = {**complete, key: False}
                self.assertFalse(p1_can_create_new_epoch(**changed))

    def test_a1_uses_both_channels_and_five_minute_repeats(self):
        alert = a1_critical_alert(acknowledged_at_minute=None)
        self.assertEqual(("EMAIL", "TELEGRAM_PUSH"), alert["channels"])
        self.assertEqual((0, 5, 10, 15), alert["repeat_minutes"])
        self.assertFalse(alert["risk_authority_restored"])

    def test_a1_ack_deadline_boundary(self):
        self.assertTrue(a1_critical_alert(acknowledged_at_minute=15)["acknowledged_in_time"])
        self.assertFalse(a1_critical_alert(acknowledged_at_minute=16)["acknowledged_in_time"])

    def test_oracle_has_no_broker_network_messaging_or_process_capability(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        forbidden_imports = {"MetaTrader5", "socket", "requests", "httpx", "smtplib", "telegram", "subprocess"}
        forbidden_calls = {"initialize", "login", "order_check", "order_send", "sendmail", "send_message", "system", "popen", "exec", "eval", "compile"}
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


if __name__ == "__main__":
    unittest.main()
