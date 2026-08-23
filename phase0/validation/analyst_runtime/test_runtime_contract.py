from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from runtime_contract_oracle import (
    OUTPUT_FORMAT, PROFILE, REGISTER, artifact_fingerprints, build_request,
    derive_snapshot_id, expected_fields, reserve_standard_cost,
    revalidation_required, strict_object_tree, validate_payload,
    validate_response_body, validate_response_envelope,
    evaluate_chronological_exchange,
)

UTC = timezone.utc
NOW = datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC)


def common(family, direction="BUY", regime="UP_TREND"):
    value = {
        "schema_version": "analyst-runtime-1.0",
        "analysis_id": "123e4567-e89b-42d3-a456-426614174000",
        "snapshot_id": "0" * 64,
        "snapshot_time_utc": "2026-08-23T12:00:00Z",
        "instrument_class": "XAUUSD_GOLD_CFD",
        "candidate_setup_family": family,
        "direction": direction,
        "h4_bar_close_utc": "2026-08-23T08:00:00Z",
        "h1_bar_close_utc": "2026-08-23T11:00:00Z",
        "m15_bar_close_utc": "2026-08-23T12:00:00Z",
        "quote_age_ms": 400,
        "completed_m15_delay_ms": 800,
        "regime": regime,
        "spread_state": "NORMAL",
        "volatility_state": "NORMAL",
        "session_state": "OPEN",
        "event_guard_state": "HEALTHY",
        "new_risk_allowed_locally": True,
        "unknown_exposure_present": False,
        "daily_limit_state": "CLEAR",
        "weekly_limit_state": "CLEAR",
        "drawdown_state": "CLEAR",
        "loss_pause_state": "CLEAR",
        "evidence_ids": ["regime-1", "structure-1", "trigger-1", "geometry-1"],
    }
    family_values = {
        "TPB": {
            "impulse_origin_price":"3300.000","impulse_endpoint_price":"3350.000",
            "active_zone":"A","zone_near_price":"3331.000","zone_far_price":"3325.000",
            "independent_location":"H1_SWING_LEVEL","rejection_extreme_price":"3324.500",
            "confirmation_extreme_price":"3332.000","first_target_price":"3350.000",
            "final_target_price":"3370.000","impulse_qualified":True,
            "zone_qualified":True,"confirmation_qualified":True,
        },
        "BRT": {
            "breakout_boundary_price":"3340.000","consolidation_far_boundary_price":"3310.000",
            "consolidation_width_atr_bp":10000,"breakout_close_price":"3345.000",
            "retest_extreme_price":"3339.000","confirmation_extreme_price":"3343.000",
            "first_target_price":"3360.000","final_target_price":"3370.000",
            "breakout_qualified":True,"retest_qualified":True,"confirmation_qualified":True,
        },
        "FBR": {
            "reference_boundary_price":"3320.000","failed_break_extreme_price":"3315.000",
            "failed_break_depth_atr_bp":2000,"reclaim_close_price":"3321.000",
            "confirmation_extreme_price":"3323.000","first_target_price":"3340.000",
            "final_target_price":"3360.000","reclaim_qualified":True,
            "hold_qualified":True,"confirmation_qualified":True,
        },
        "RSR": {
            "lower_boundary_price":"3300.000","upper_boundary_price":"3360.000",
            "midpoint_price":"3330.000","active_boundary_price":"3300.000",
            "rejection_extreme_price":"3299.000","confirmation_extreme_price":"3305.000",
            "distance_from_boundary_range_bp":500,"first_target_price":"3330.000",
            "final_target_price":"3359.000","range_qualified":True,
            "location_qualified":True,"confirmation_qualified":True,
        },
        "MOC": {
            "impulse_origin_price":"3300.000","impulse_endpoint_price":"3350.000",
            "compression_low_price":"3338.000","compression_high_price":"3348.000",
            "trigger_close_price":"3350.000","first_target_price":"3365.000",
            "final_target_price":"3380.000","compression_range_atr_bp":5000,
            "retracement_bp":2400,"quote_slippage_atr_bp":300,
            "compression_qualified":True,"trigger_qualified":True,
        },
    }
    value.update(family_values[family])
    value["snapshot_id"] = derive_snapshot_id(value)
    return value


def provider_response(body):
    return {
        "status": "completed",
        "model": "gpt-5.6-sol",
        "incomplete_details": None,
        "output": [{"type": "message", "content": [
            {"type": "output_text", "text": json.dumps(body, separators=(",", ":"))}
        ]}],
    }


def no_trade_body(payload):
    return {
        "schema_version": "analyst-runtime-1.0",
        "analysis_id": payload["analysis_id"],
        "snapshot_id": payload["snapshot_id"],
        "decision": "NO_TRADE",
        "reason_codes": ["MODEL_UNCERTAIN"],
        "summary": "No advisory setup accepted.",
        "proposal": {"kind": "NONE", "recheck_condition": "NEW_COMPLETED_BAR"},
    }


def trade_body(payload):
    return {
        "schema_version": "analyst-runtime-1.0",
        "analysis_id": payload["analysis_id"],
        "snapshot_id": payload["snapshot_id"],
        "decision": "PROPOSE_TRADE",
        "reason_codes": ["VALID_SETUP"],
        "summary": "Synthetic candidate passes the bounded advisory check.",
        "proposal": {
            "kind": "TRADE",
            "setup_family": payload["candidate_setup_family"],
            "direction": payload["direction"],
            "entry_type": "LIMIT",
            "entry": {"kind": "SINGLE", "price": payload["zone_near_price"]},
            "invalidation_price": payload["rejection_extreme_price"],
            "stop_loss": payload["zone_far_price"],
            "targets": [
                {"role": "TP1", "price": payload["first_target_price"]},
                {"role": "FINAL", "price": payload["final_target_price"]},
            ],
            "expiry_time_utc": "2026-08-23T13:00:00Z",
            "cancellation_conditions": ["COMMON_FILTER_FAILED", "EVENT_LOCK"],
            "confidence": 70,
            "evidence_refs": payload["evidence_ids"],
        },
    }


class AnalystRuntimeContractTests(unittest.TestCase):
    def test_profile_is_exact_sol_stateless_tool_free_and_single_attempt(self):
        request = PROFILE["request"]
        self.assertEqual("gpt-5.6-sol", PROFILE["model"])
        self.assertIs(request["store"], False)
        self.assertEqual([], request["tools"])
        self.assertEqual(1, request["max_attempts"])
        self.assertEqual("disabled", request["truncation"])
        self.assertIs(PROFILE["live_calls_authorized"], False)

    def test_current_sol_price_and_long_context_control_are_frozen(self):
        price = PROFILE["pricing_control"]
        self.assertEqual("4.00", price["standard_input_usd_per_million_tokens"])
        self.assertEqual("20.00", price["standard_output_usd_per_million_tokens"])
        self.assertEqual("2026-11-21", price["mandatory_revalidation_no_later_than_utc_date"])
        self.assertEqual(Decimal("0.028"), reserve_standard_cost(1000))
        self.assertGreater(reserve_standard_cost(272001), reserve_standard_cost(272000))

    def test_all_five_family_registers_are_closed_and_defined(self):
        self.assertEqual({"TPB", "BRT", "FBR", "RSR", "MOC"}, set(REGISTER["families"]))
        definitions = set(REGISTER["field_definitions"])
        for family in REGISTER["families"]:
            self.assertEqual(expected_fields(family), set(REGISTER["common_fields"]) | set(REGISTER["families"][family]))
            self.assertTrue(expected_fields(family) <= definitions)

    def test_each_family_minimized_payload_passes(self):
        for family in REGISTER["families"]:
            with self.subTest(family=family):
                direction, regime = ("BUY", "RANGE") if family == "RSR" else ("BUY", "UP_TREND")
                self.assertEqual((True, ()), validate_payload(common(family, direction, regime), NOW))

    def test_extra_missing_and_cross_family_fields_reject(self):
        payload = common("TPB")
        payload["account_number"] = "SYNTHETIC_FORBIDDEN_FIELD"
        payload.pop("zone_far_price")
        healthy, reasons = validate_payload(payload, NOW)
        self.assertFalse(healthy)
        self.assertIn("EXTRA_FIELDS", reasons)
        self.assertIn("MISSING_FIELDS", reasons)
        self.assertIn("PROHIBITED_DATA", reasons)

    def test_canonical_decimal_and_integer_types_reject_float_or_exponent(self):
        for field, bad in (("zone_near_price", 3331.0), ("zone_near_price", "3.331e3"),
                           ("quote_age_ms", 400.0)):
            with self.subTest(field=field, bad=bad):
                payload = common("TPB")
                payload[field] = bad
                payload["snapshot_id"] = derive_snapshot_id(payload)
                self.assertIn(f"INVALID_FIELD:{field}", validate_payload(payload, NOW)[1])

    def test_snapshot_hash_and_send_freshness_are_bound(self):
        payload = common("TPB")
        payload["zone_near_price"] = "3330.000"
        self.assertIn("SNAPSHOT_HASH", validate_payload(payload, NOW)[1])
        stale = common("TPB")
        stale["snapshot_time_utc"] = "2026-08-23T11:59:54Z"
        stale["snapshot_id"] = derive_snapshot_id(stale)
        self.assertIn("STALE_OR_FUTURE_SNAPSHOT", validate_payload(stale, NOW)[1])

    def test_every_blocked_or_unknown_local_gate_prevents_call(self):
        changes = {
            "spread_state":"BLOCKED", "volatility_state":"UNKNOWN",
            "session_state":"BLOCKED", "event_guard_state":"PRE_LOCK",
            "new_risk_allowed_locally":False, "unknown_exposure_present":True,
            "daily_limit_state":"NEAR_LIMIT", "weekly_limit_state":"BLOCKED",
            "drawdown_state":"UNKNOWN", "loss_pause_state":"BLOCKED",
        }
        for field, bad in changes.items():
            with self.subTest(field=field):
                payload = common("TPB")
                payload[field] = bad
                payload["snapshot_id"] = derive_snapshot_id(payload)
                self.assertIn("LOCAL_GATE_BLOCKED", validate_payload(payload, NOW)[1])
                with self.assertRaisesRegex(ValueError, "LOCAL_NO_CALL"):
                    build_request(payload, "fixed prompt", NOW)

    def test_required_family_predicates_must_all_be_true(self):
        payload = common("BRT")
        payload["retest_qualified"] = False
        payload["snapshot_id"] = derive_snapshot_id(payload)
        self.assertIn("FAMILY_PREDICATE_NOT_TRUE", validate_payload(payload, NOW)[1])

    def test_regime_family_and_direction_binding(self):
        tpb = common("TPB", "SELL", "UP_TREND")
        tpb["snapshot_id"] = derive_snapshot_id(tpb)
        self.assertIn("REGIME_DIRECTION_MISMATCH", validate_payload(tpb, NOW)[1])
        rsr = common("RSR", "BUY", "UP_TREND")
        rsr["snapshot_id"] = derive_snapshot_id(rsr)
        self.assertIn("REGIME_FAMILY_MISMATCH", validate_payload(rsr, NOW)[1])

    def test_request_has_only_frozen_parameters_and_strict_schema(self):
        request = build_request(common("TPB"), "fixed prompt", NOW)
        self.assertEqual(set(request), {"model","store","tools","reasoning","max_output_tokens","stream","background","truncation","service_tier","input","text"})
        self.assertEqual("json_schema", request["text"]["format"]["type"])
        self.assertTrue(request["text"]["format"]["strict"])
        self.assertTrue(strict_object_tree(OUTPUT_FORMAT["schema"]))
        self.assertFalse(set(PROFILE["forbidden_request_parameters"]) & set(request))

    def test_response_must_complete_on_exact_model_without_tools_or_refusal(self):
        good = {"status":"completed","model":"gpt-5.6-sol","incomplete_details":None,
                "output":[{"type":"reasoning","summary":[]},
                          {"type":"message","content":[{"type":"output_text","text":"{}"}]}]}
        self.assertEqual((True, ()), validate_response_envelope(good))
        bad = deepcopy(good)
        bad["model"] = "gpt-5.6-terra"
        bad["output"] = [{"type":"web_search_call","content":[]},
                         {"type":"message","content":[{"type":"refusal","refusal":"no"}]}]
        healthy, reasons = validate_response_envelope(bad)
        self.assertFalse(healthy)
        self.assertEqual({"MODEL_MISMATCH","TOOL_OR_UNKNOWN_OUTPUT_ITEM","REFUSAL",
                          "OUTPUT_TEXT_CARDINALITY"}, set(reasons))

    def test_strict_no_trade_and_trade_bodies_bind_to_snapshot(self):
        payload = common("TPB")
        self.assertEqual((True, ()), validate_response_body(provider_response(no_trade_body(payload)), payload))
        self.assertEqual((True, ()), validate_response_body(provider_response(trade_body(payload)), payload))

    def test_duplicate_json_wrong_ids_and_extra_fields_fail_closed(self):
        payload = common("TPB")
        duplicate = provider_response(no_trade_body(payload))
        duplicate["output"][0]["content"][0]["text"] = '{"schema_version":"analyst-runtime-1.0","schema_version":"analyst-runtime-1.0"}'
        self.assertEqual((False, ("OUTPUT_JSON_INVALID",)), validate_response_body(duplicate, payload))
        body = no_trade_body(payload)
        body["analysis_id"] = "223e4567-e89b-42d3-a456-426614174000"
        body["unexpected"] = True
        healthy, reasons = validate_response_body(provider_response(body), payload)
        self.assertFalse(healthy)
        self.assertIn("OUTPUT_FIELDS", reasons)

    def test_invented_price_evidence_and_target_order_are_rejected(self):
        payload = common("TPB")
        body = trade_body(payload)
        body["proposal"]["entry"]["price"] = "9999.000"
        body["proposal"]["evidence_refs"] = ["invented-evidence"]
        body["proposal"]["targets"].reverse()
        healthy, reasons = validate_response_body(provider_response(body), payload)
        self.assertFalse(healthy)
        self.assertEqual({"INVENTED_ENTRY_PRICE", "EVIDENCE_BINDING", "TARGET_BINDING"}, set(reasons))

    def test_proposal_never_authorizes_trading_and_state_change_rejects(self):
        payload = common("TPB")
        response = provider_response(trade_body(payload))
        result = evaluate_chronological_exchange(
            payload, response, NOW, NOW + timedelta(seconds=2), "state-a", "state-a", set()
        )
        self.assertTrue(result["advisory_accepted"])
        self.assertIs(result["trading_authorized"], False)
        changed = evaluate_chronological_exchange(
            payload, response, NOW, NOW + timedelta(seconds=2), "state-a", "state-b", set()
        )
        self.assertFalse(changed["advisory_accepted"])
        self.assertIn("LOCAL_STATE_CHANGED", changed["reason_codes"])
        self.assertIs(changed["trading_authorized"], False)

    def test_late_replayed_and_clock_reversed_responses_reject(self):
        payload = common("TPB")
        response = provider_response(no_trade_body(payload))
        consumed = set()
        first = evaluate_chronological_exchange(
            payload, response, NOW, NOW + timedelta(seconds=1), "state", "state", consumed
        )
        self.assertTrue(first["advisory_accepted"])
        replay = evaluate_chronological_exchange(
            payload, response, NOW, NOW + timedelta(seconds=2), "state", "state", consumed
        )
        self.assertIn("SNAPSHOT_REPLAY", replay["reason_codes"])
        late = evaluate_chronological_exchange(
            payload, response, NOW, NOW + timedelta(seconds=31), "state", "state", set()
        )
        self.assertIn("RESPONSE_STALE", late["reason_codes"])
        reversed_clock = evaluate_chronological_exchange(
            payload, response, NOW, NOW - timedelta(seconds=1), "state", "state", set()
        )
        self.assertIn("CLOCK_REVERSED", reversed_clock["reason_codes"])
        self.assertIs(reversed_clock["trading_authorized"], False)

    def test_production_prompt_is_frozen_non_trading_and_corpus_is_complete(self):
        root = Path(__file__).parent
        prompt = (root / "PRODUCTION_ANALYST_SYSTEM_PROMPT_V1.txt").read_text(encoding="utf-8")
        self.assertIn("never authorize, size, route, modify, cancel, or execute", prompt)
        self.assertIn("Default to NO_TRADE", prompt)
        self.assertIn("never constitutes permission to trade", prompt)
        corpus = json.loads((root / "CHRONOLOGICAL_VALIDATION_CORPUS_V1.json").read_text(encoding="utf-8"))
        self.assertEqual(10, len(corpus["cases"]))
        self.assertEqual(len(corpus["cases"]), len({case["case_id"] for case in corpus["cases"]}))
        self.assertEqual("NO_CASE_CAN_SET_TRADING_AUTHORIZED_TRUE", corpus["invariant"])

    def test_artifact_change_requires_revalidation(self):
        baseline = artifact_fingerprints("fixed prompt")
        self.assertFalse(revalidation_required(baseline, dict(baseline)))
        changed = dict(baseline, prompt_sha256="0" * 64)
        self.assertTrue(revalidation_required(baseline, changed))

    def test_no_free_text_or_broker_identity_field_exists(self):
        names = " ".join(REGISTER["field_definitions"]).lower()
        for forbidden in ("account", "ticket", "order", "position", "balance", "equity",
                          "margin", "leverage", "lot", "email", "phone", "comment", "headline"):
            self.assertNotIn(forbidden, names)
        self.assertTrue(all(spec["retention"] == "HASH_ONLY"
                            for spec in REGISTER["field_definitions"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
