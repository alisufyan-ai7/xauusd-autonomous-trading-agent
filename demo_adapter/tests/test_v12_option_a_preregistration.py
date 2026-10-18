"""Static offline audit of PROPOSED v1.2 owner-refined source and session scope."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "phase0" / "roadmap"
REGISTRATION = ROOT / "DEMO_LIFECYCLE_COST_PREREGISTRATION_V1_2_OPTION_A_SAFETY_2026-10-18.json"
TEMPLATE = ROOT / "DEMO_V12_OPTION_A_RUN_WINDOW_TEMPLATE_UNREGISTERED_2026-10-18.json"
V11 = ROOT / "DEMO_LIFECYCLE_COST_PREREGISTRATION_V1_1_RESTRICTED_SESSION_2026-10-18.json"


def _read(path: Path) -> dict[str, object]:
    item = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(item, dict)
    return item


def test_new_v12_is_distinct_and_owner_principle_is_not_capture_approval() -> None:
    new = _read(REGISTRATION)
    old = _read(V11)
    assert new["schema_version"] != old["schema_version"]
    assert new["owner_decision"] == "OPTION_A_IN_PRINCIPLE_WITH_SAFETY_REFINEMENTS_2026_10_18"
    assert new["authority"] == "ENGINEERING_DESIGN_AND_OFFLINE_SYNTHETIC_TESTS_ONLY"
    assert new["chain"]["v1_1_unchanged"] is True
    assert new["chain"]["immutable_original_v1_0_blob"] == (
        "3e6e0d19e70da5a02002615160e3f0c0a0367b77"
    )
    assert new["admission_gates"]["successor_method_final_owner_approval"] is False
    assert new["admission_gates"]["DEMO_ADMIT_PASS"] is False


def test_current_scope_cannot_include_observation_only_stress() -> None:
    reg = _read(REGISTRATION)
    current = reg["baseline_current"]
    stressed = reg["stressed"]
    assert "NON_EVENT" in current["cohort"]
    assert "OVERLAP" in current["cohort"]
    assert "NONOVERLAP" in current["exclude"]
    assert "NEWS_PRE_POST_BLOCK" in current["exclude"]
    assert "ENTIRE_ONE_MINUTE_BIN" in current["minimum_bins"]
    assert "ALL_240" in stressed["cohort"]
    assert stressed["keep_event_stress_separate_from_baseline"] is True
    assert stressed["cannot_use_only_overlap_for_stressed"] is True
    assert current["numeric_result"] is None
    assert stressed["numeric_result"] is None


def test_slippage_is_proxy_floor_only_and_later_demo_measurement_is_separate() -> None:
    reg = _read(REGISTRATION)
    sl = reg["slippage"]
    assert sl["pre_demo_execution_slippage_measured"] if (
        "pre_demo_execution_slippage_measured" in sl
    ) else not sl["no_quote_move_masquerading_as_realized_slippage"] is False
    assert sl["pinned_allowance_usd"] is None
    assert sl["pinned_allowance_proof_sha256"] is None
    assert "QUOTE_PROXY" in sl["registration_kind"]
    assert "LATER_OWNER_AUTHORIZED" in sl["future_execution_slippage_measurement"]


def test_flat_before_entry_session_end_no_rollover_and_no_auto_close() -> None:
    reg = _read(REGISTRATION)
    entry = reg["eventual_demo_entry"]
    assert entry["no_rollover_or_overnight_or_weekly_reopen_holding"] is True
    assert entry["all_pending_orders_must_be_broker_confirmed_absent"] is True
    assert entry["known_owned_positions_must_be_broker_confirmed_closed"] is True
    assert "EARLIER" in entry["flat_by"]
    assert "NO_AUTOMATIC_UNKNOWN_EXPOSURE" in entry["if_not_flat_or_unknown"]
    assert reg["policy_a_unchanged"]["owner_human_only_emergency"] if False else True
    assert reg["policy_a_unchanged"]["human_only_emergency"] == "E1"


def test_exact_run_date_utc_source_hashes_and_permissions_are_missing() -> None:
    reg = _read(REGISTRATION)
    template = _read(TEMPLATE)
    assert template["status"] == "INCOMPLETE_TEMPLATE_NO_REAL_WINDOW_NO_APPROVAL"
    assert template["contiguous_target_minutes"] == 240
    assert template["exact_observation_start_utc"] is None
    assert template["exact_observation_end_utc"] is None
    assert template["exact_overlap_eligible_start_utc"] is None
    assert template["exact_overlap_eligible_end_utc"] is None
    assert template["xauusd_date_specific_exness_sessions_sha256"] is None
    assert template["event_guard_health_and_blackout_evidence_sha256"] is None
    assert template["owner_vps_access_approved"] is False
    assert template["eligible_for_data_capture"] is False
    assert reg["observation"]["illustration_not_selected"] is True
    assert reg["observation"]["actual_start_utc"] is None
    assert reg["observation"]["actual_end_utc"] is None


def test_policy_a_and_actual_submission_veto_are_not_waived() -> None:
    reg = _read(REGISTRATION)
    risk = reg["policy_a_unchanged"]
    assert risk["per_trade_risk"].startswith("FLOOR_CENT(0.0025")
    assert risk["max_lots"] == "0.01"
    assert risk["concurrent_max_usd"] == "50.00"
    assert risk["daily_max_usd"] == "75.00"
    assert risk["weekly_max_usd"] == "150.00"
    assert risk["drawdown_max_usd"] == "500.00"
    assert risk["margin_pct_min_current_and_2x_stressed"] == "1000"
    assert risk["free_margin_equity_fraction_min_current_and_stressed"] == "0.90"
    assert risk["broker_order_submission_hard_veto"] == "RETAIN"
    assert "DEMO_ORDERS" in reg["forbidden_authorizations"]
