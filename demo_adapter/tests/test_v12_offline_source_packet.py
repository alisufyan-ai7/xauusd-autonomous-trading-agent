"""Adversarial injected-source tests; no VPS, real MT5, web or broker IO."""
from __future__ import annotations

import copy
import hashlib
import inspect
from datetime import UTC, datetime
from typing import Any

import pytest

from scripts import v12_offline_source_packet as gate
from scripts.v12_offline_source_packet import OfflinePacketError

NOW = datetime(2026, 10, 19, 10, tzinfo=UTC)


def example() -> tuple[dict[str, Any], dict[str, bytes], dict[str, str]]:
    sources: dict[str, dict[str, str]] = {}
    raw: dict[str, bytes] = {}
    pins: dict[str, str] = {}
    for name in gate.REQUIRED_SOURCE_IDS:
        data = ("SYNTHETIC_UNAUTHENTICATED_" + name).encode("ascii")
        digest = hashlib.sha256(data).hexdigest()
        raw[name] = data
        pins[name] = digest
        sources[name] = {
            "sha256": digest,
            "source_url_or_protected_locator": "synthetic-fixture:" + name,
            "retrieved_utc": "2026-10-18T11:00:00Z",
            "expected_regime": "REHEARSAL_NOT_REAL_SOURCE",
        }
    p: dict[str, Any] = {
        "scope": "SYNTHETIC_OFFLINE_DESIGN_REHEARSAL_ONLY",
        "approved_design_pr13_sha": gate.APPROVED_PR13_SHA,
        "approved_parent_pr12_sha": gate.APPROVED_PARENT_PR12_SHA,
        "frozen_v12_prereg_git_blob": gate.FROZEN_V12_PREREG_GIT_BLOB,
        "owner_design_comment_id": gate.OWNER_APPROVAL_COMMENT_ID,
        "action_authorizations": {name: False for name in gate.BLOCKED_ACTIONS},
        "actual_broker_data_used": False,
        "execution_slippage_measured": False,
        "numeric_costs_admitted": False,
        "observation": {
            "start_utc": "2026-10-20T12:30:00Z",
            "end_utc": "2026-10-20T16:30:00Z",
        },
        "entry_overlap": {
            "start_utc": "2026-10-20T13:30:00Z",
            "end_utc": "2026-10-20T16:30:00Z",
        },
        "broker_eligible": {
            "start_utc": "2026-10-20T12:00:00Z",
            "end_utc": "2026-10-20T18:00:00Z",
        },
        "blocked_event_windows": [],
        "full_240m_liquidity_flag": True,
        "overlap_event_free_flag": True,
        "event_guard_healthy_flag": True,
        "external_python_trade_api_disabled": True,
        "flat_plan": {
            "verified_broker_session_end_utc": "2026-10-20T18:00:00Z",
            "flat_confirmation_lead_seconds": 300,
            "max_holding_seconds": 600,
            "exit_reconciliation_seconds": 120,
            "owner_attended_plan_only": True,
        },
        "sources": sources,
    }
    return p, raw, pins


def check(
    packet: dict[str, Any] | None = None,
    raw: dict[str, bytes] | None = None,
    pins: dict[str, str] | None = None,
    now: datetime = NOW,
) -> gate.SourcePacketReview:
    a, b, c = example()
    return gate.review_v12_capture_proposal(
        a if packet is None else packet,
        b if raw is None else raw,
        c if pins is None else pins,
        review_utc=now,
    )


def test_full_synthetic_rehearsal_never_grants_capture_or_trading() -> None:
    result = check()
    assert result.status == (
        "SYNTHETIC_OFFLINE_SCHEMA_REVIEW_ONLY__NOT_CAPTURE_OR_DEMO_ADMISSION"
    )
    assert result.source_count == 23
    assert result.observation_minutes == 240
    assert result.eligible_overlap_minutes == 180
    assert result.latest_synthetic_entry_utc == datetime(
        2026, 10, 20, 16, 13, tzinfo=UTC
    )
    assert result.synthetic_flat_deadline_utc == datetime(
        2026, 10, 20, 16, 25, tzinfo=UTC
    )
    assert len(result.packet_sha256) == 64
    assert not result.source_origin_authenticated
    assert not result.numeric_cost_calibration_admitted
    assert not result.capture_authorized
    assert not result.demo_order_authorized


@pytest.mark.parametrize(("field", "bad"), [
    ("approved_design_pr13_sha", "0" * 40),
    ("approved_parent_pr12_sha", "0" * 40),
    ("frozen_v12_prereg_git_blob", "0" * 40),
    ("owner_design_comment_id", 0),
    ("actual_broker_data_used", True),
    ("execution_slippage_measured", True),
    ("numeric_costs_admitted", True),
    ("scope", "READY_TO_TRADE"),
    ("external_python_trade_api_disabled", False),
    ("event_guard_healthy_flag", False),
    ("overlap_event_free_flag", None),
    ("full_240m_liquidity_flag", False),
])
def test_false_design_binding_or_source_claims_fail(
    field: str, bad: Any
) -> None:
    p, raw, pins = example()
    p[field] = bad
    with pytest.raises(OfflinePacketError):
        check(p, raw, pins)


@pytest.mark.parametrize("action", gate.BLOCKED_ACTIONS)
def test_no_action_can_be_claimed_from_a_design_signature(
    action: str,
) -> None:
    p, raw, pins = example()
    p["action_authorizations"][action] = True
    with pytest.raises(OfflinePacketError, match="no operational authority"):
        check(p, raw, pins)


def test_tampered_private_source_bytes_fail_against_fixed_pin() -> None:
    p, raw, pins = example()
    raw["broker_fee_swap"] = b"forged statement of commission waiver"
    with pytest.raises(OfflinePacketError, match="source-byte SHA mismatch"):
        check(p, raw, pins)


def test_matching_attacker_written_pins_are_still_only_synthetic() -> None:
    p, raw, pins = example()
    data = b"totally fake, caller-generated XAUUSD broker claims"
    raw["broker_fee_swap"] = data
    pins["broker_fee_swap"] = hashlib.sha256(data).hexdigest()
    p["sources"]["broker_fee_swap"]["sha256"] = pins["broker_fee_swap"]
    result = check(p, raw, pins)
    assert not result.source_origin_authenticated
    assert not result.numeric_cost_calibration_admitted


def test_missing_independent_dol_fed_guard_clock_or_exit_proof() -> None:
    for name in ("dol_calendar", "fed_calendar", "clock_sync",
                 "event_guard_health_blackout", "supervised_exit_reconciliation"):
        p, raw, pins = example()
        p["sources"].pop(name)
        with pytest.raises(OfflinePacketError, match="source classes"):
            check(p, raw, pins)


def test_future_dated_official_source_rejected() -> None:
    p, raw, pins = example()
    p["sources"]["bls_calendar"]["retrieved_utc"] = "2026-10-20T12:31:00Z"
    with pytest.raises(OfflinePacketError, match="future-dated source"):
        check(p, raw, pins)


def test_missing_provenance_and_nan_float_not_accepted() -> None:
    p, raw, pins = example()
    p["sources"]["exness_xauusd_hours"]["source_url_or_protected_locator"] = ""
    with pytest.raises(OfflinePacketError, match="origin"):
        check(p, raw, pins)
    p, raw, pins = example()
    p["unknown_float"] = float("nan")
    with pytest.raises(OfflinePacketError, match="float"):
        check(p, raw, pins)


def test_bls_inside_overlap_blocks_all_baseline_not_shortens_it() -> None:
    p, raw, pins = example()
    p["blocked_event_windows"] = [{
        "start_utc": "2026-10-20T13:59:00Z",
        "end_utc": "2026-10-20T14:01:00Z",
    }]
    with pytest.raises(OfflinePacketError, match="overlap contaminated"):
        check(p, raw, pins)


def test_event_in_observation_only_segment_requires_separate_approval() -> None:
    p, raw, pins = example()
    p["blocked_event_windows"] = [{
        "start_utc": "2026-10-20T12:31:00Z",
        "end_utc": "2026-10-20T12:33:00Z",
    }]
    with pytest.raises(OfflinePacketError, match="unapproved event"):
        check(p, raw, pins)


def test_broker_hours_do_not_cover_full_observation() -> None:
    p, raw, pins = example()
    p["broker_eligible"]["start_utc"] = "2026-10-20T13:00:00Z"
    with pytest.raises(OfflinePacketError, match="whole 4h"):
        check(p, raw, pins)


def test_overlap_not_subset_of_observation_or_broker_fails() -> None:
    p, raw, pins = example()
    p["entry_overlap"]["end_utc"] = "2026-10-20T17:00:00Z"
    with pytest.raises(OfflinePacketError, match="inside 4h"):
        check(p, raw, pins)


def test_crossing_midnight_and_weekend_not_eligible() -> None:
    p, raw, pins = example()
    p["observation"] = {
        "start_utc": "2026-10-20T22:00:00Z",
        "end_utc": "2026-10-21T02:00:00Z",
    }
    with pytest.raises(OfflinePacketError, match="overnight"):
        check(p, raw, pins)
    p, raw, pins = example()
    p["observation"] = {
        "start_utc": "2026-10-24T12:30:00Z",
        "end_utc": "2026-10-24T16:30:00Z",
    }
    with pytest.raises(OfflinePacketError, match="weekend"):
        check(p, raw, pins)


def test_stale_or_past_registration_cannot_be_backdated() -> None:
    p, raw, pins = example()
    with pytest.raises(OfflinePacketError, match="prospective"):
        check(p, raw, pins, now=datetime(2026, 10, 20, 12, 31, tzinfo=UTC))


def test_missing_flat_buffer_or_late_entry_cutoff_denies() -> None:
    p, raw, pins = example()
    p["flat_plan"]["flat_confirmation_lead_seconds"] = 0
    with pytest.raises(OfflinePacketError, match="positive"):
        check(p, raw, pins)
    p, raw, pins = example()
    p["flat_plan"]["max_holding_seconds"] = 25000
    with pytest.raises(OfflinePacketError, match="positive|early"):
        check(p, raw, pins)


def test_broker_end_mismatch_to_flat_plan_fails() -> None:
    p, raw, pins = example()
    p["flat_plan"]["verified_broker_session_end_utc"] = "2026-10-20T18:01:00Z"
    with pytest.raises(OfflinePacketError, match="broker cutoff"):
        check(p, raw, pins)


def test_no_broker_capability_or_order_side_effects() -> None:
    src = inspect.getsource(gate)
    for banned in (
        "import MetaTrader5", "order_send(", "order_check(",
        "order_modify(", "order_close(", "initialize(",
        "shutdown(", "subprocess.", "socket.", "os.system(",
    ):
        assert banned not in src


def test_repeated_source_digest_does_not_upgrade_source_origin() -> None:
    p, raw, pins = example()
    raw["bea_calendar"] = raw["bls_calendar"]
    digest = hashlib.sha256(raw["bea_calendar"]).hexdigest()
    pins["bea_calendar"] = digest
    p["sources"]["bea_calendar"]["sha256"] = digest
    out = check(p, raw, pins)
    assert not out.source_origin_authenticated
    assert not out.capture_authorized


def test_private_packet_inputs_not_mutated_by_review() -> None:
    p, raw, pins = example()
    expected_packet = copy.deepcopy(p)
    expected_raw = copy.deepcopy(raw)
    check(p, raw, pins)
    assert p == expected_packet
    assert raw == expected_raw
