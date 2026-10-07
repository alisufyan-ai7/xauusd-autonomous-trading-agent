import ast
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from phase0.validation.margin_evidence.margin_oracle import evaluate_m1_snapshot, incremental_margin
from phase0.validation.margin_evidence.test_stress_artifact import fixture as stress_fixture, resign


NOW=datetime(2026,8,23,12,0,tzinfo=timezone.utc)
ROOT="a"*64


def snapshot(**changes):
    row={"observed_utc":"2026-08-23T12:00:00Z","tradeapi_disabled":True,
         "equity":"15000","margin":"800","leverage":"2000","trade_calc_mode":0,
         "trade_contract_size":"100","currency_margin":"XAU","currency_base":"XAU",
         "currency_profit":"USD","account_currency":"USD","bid":"4000","ask":"4000"}
    row.update(changes); return row


def stress(**changes):
    artifact=stress_fixture()
    values={"spread_stress":"1000","slippage_stress":"1000",
            "gap_stress":"900","cost_stress":"100"}
    values.update(changes)
    for name,value in values.items():
        artifact["components"][name]["selected_value_usd"]=value
        artifact["components"][name]["empirical_value_usd"]=value
    resign(artifact)
    return artifact


def evaluate(snap, artifact, **changes):
    arguments={"now_utc":NOW,"expected_bundle_root_sha256":ROOT,
               "expected_stress_artifact_sha256":artifact["artifact_sha256"],
               "current_entry_cost":"0"}
    arguments.update(changes)
    return evaluate_m1_snapshot(snap,artifact,**arguments)


class MarginEvidenceTests(unittest.TestCase):
    def test_independent_calc_mode_zero_margin(self):
        self.assertEqual(Decimal("2.000"),incremental_margin(snapshot(),volume=Decimal("0.01")))

    def test_m1_both_states_pass_only_as_spec_evidence(self):
        artifact=stress(); result=evaluate(snapshot(),artifact)
        self.assertEqual("PASS_SPEC_ONLY",result.status)
        self.assertEqual("M1_PASS_NOT_TRADE_AUTHORITY",result.reason)

    def test_exact_stressed_1000_percent_and_90_percent_boundary_passes(self):
        exact=snapshot(bid="400000",ask="400000")  # fixture increment = 200
        artifact=stress(); result=evaluate(exact,artifact)
        self.assertEqual("PASS_SPEC_ONLY",result.status)
        self.assertEqual(Decimal("1000"),result.stressed_margin_level_percent)
        one_cent=stress(cost_stress="100.01")
        self.assertEqual("M1_STRESSED_THRESHOLD_FAILED",evaluate(exact,one_cent).reason)

    def test_stressed_threshold_and_unfrozen_stress_fail(self):
        stressed=stress(cost_stress="6000")
        self.assertEqual("M1_STRESSED_THRESHOLD_FAILED",evaluate(snapshot(),stressed).reason)
        artifact=stress(); artifact["status"]="CANDIDATE"; resign(artifact)
        self.assertEqual("STRESS_ARTIFACT_NOT_ADMITTED_OR_BOUND",evaluate(snapshot(),artifact).reason)
        artifact=stress()
        self.assertEqual("STRESS_ARTIFACT_NOT_ADMITTED_OR_BOUND",
                         evaluate(snapshot(),artifact,expected_stress_artifact_sha256="f"*64).reason)

    def test_stale_missing_and_ambiguous_conversion_fail_closed(self):
        stale=snapshot(observed_utc=(NOW-timedelta(seconds=31)).isoformat())
        artifact=stress()
        self.assertEqual("SNAPSHOT_STALE_OR_FUTURE",evaluate(stale,artifact).reason)
        self.assertEqual("MISSING_INVALID_OR_AMBIGUOUS_INPUT",evaluate(snapshot(ask=None),artifact).reason)
        self.assertEqual("MISSING_INVALID_OR_AMBIGUOUS_INPUT",evaluate(snapshot(currency_profit="EUR"),artifact).reason)
        self.assertEqual("MISSING_INVALID_OR_AMBIGUOUS_INPUT",
                         evaluate(snapshot(),artifact,now_utc=NOW.replace(tzinfo=None)).reason)

    def test_disabled_guard_is_mandatory(self):
        artifact=stress()
        self.assertEqual("EXTERNAL_PYTHON_TRADING_NOT_DISABLED",evaluate(snapshot(tradeapi_disabled=False),artifact).reason)

    def test_oracle_has_no_mt5_network_order_or_message_capability(self):
        forbidden_imports={"MetaTrader5","requests","socket","smtplib","subprocess"}
        forbidden_calls={"order_send","order_check","order_calc_margin","login","sendmail","exec","eval","compile"}
        for name in ("margin_oracle.py","capture_private_snapshot.py"):
            source=Path(__file__).with_name(name); tree=ast.parse(source.read_text(encoding="utf-8"))
            imports=set(); calls=set()
            for node in ast.walk(tree):
                if isinstance(node,ast.Import): imports.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node,ast.ImportFrom) and node.module: imports.add(node.module.split(".")[0])
                elif isinstance(node,ast.Call):
                    calls.add(node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else "")
            self.assertFalse(imports & forbidden_imports); self.assertFalse(calls & forbidden_calls)
        adapter=Path(__file__).with_name("readonly_mt5.py").read_text(encoding="utf-8")
        for forbidden in forbidden_calls | {"positions_get","orders_get","symbol_select"}: self.assertNotIn(forbidden,adapter)
        runner=Path(__file__).with_name("run_private_snapshot.ps1").read_text(encoding="utf-8")
        for forbidden in ("order_send","order_check","Send-MailMessage","Invoke-RestMethod"): self.assertNotIn(forbidden,runner)


if __name__=="__main__": unittest.main()
