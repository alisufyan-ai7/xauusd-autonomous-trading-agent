"""Prospective screen cannot turn selected calendar events into a permit."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCREEN = ROOT / (
    "phase0/roadmap/DEMO_V12_GUARD_SCREEN_OCT23_NOV30_2026_2026-10-20.json"
)
REAL_TEMPLATE = ROOT / (
    "phase0/roadmap/DEMO_V12_EXACT_FIRST_READONLY_RUN_UNFROZEN_TEMPLATE_2026-10-19.json"
)


def test_calendar_does_not_fabricate_a_four_hour_capture() -> None:
    screen = json.loads(SCREEN.read_text("utf-8"))
    assert screen["date_candidate_disposition"] == "ALL_SCREENED_ONLY_NONE_QUALIFIED"
    assert screen["source_healthy"] is False
    assert screen["coverage_complete"] is False
    assert screen["actual_guard_observation_utc"] is None
    assert screen["tier_1_pre_minutes"] == screen["tier_1_post_minutes"] == 30
    assert screen["tier_2_pre_minutes"] == screen["tier_2_post_minutes"] == 15
    assert screen["day_screens"]
    for day in screen["day_screens"]:
        assert day["qualified"] is False
        assert day["actual_observation_start_utc"] is None
        assert day["actual_entry_start_utc"] is None
        assert not day["all_4h_broker_eligibility_verified"]
        assert not day["live_guard_healthy"]
    for e in screen["source_events"]:
        assert e["registered_tier"] is None
        assert e["blackout_start_utc"] is None
        assert e["normalization_proven"] is None
        assert e["entry_eligibility"] == "UNKNOWN_FAIL_CLOSED"


def test_first_capture_registry_unchanged_unexecutable_after_screen() -> None:
    packet = json.loads(REAL_TEMPLATE.read_text("utf-8"))
    for name in (
        "exact_window_start_utc", "exact_window_end_utc",
        "v12_overlap_start_utc", "v12_overlap_end_utc",
        "owner_first_run_confirmation_id", "private_output_path",
        "existing_terminal_exe_path",
    ):
        assert packet[name] is None
    assert packet["approval_for_vps_capture"] != "EXPLICIT_OWNER_APPROVED"
    assert packet["all_demo_live_order_actions_forbidden"] is True
