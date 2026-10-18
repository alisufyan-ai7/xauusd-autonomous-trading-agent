"""Review exact-bounded v1.2 Option A source packets IN MEMORY, offline only.

This module never authenticates an external provider, chooses a real capture
window, approves VPS access, admits numerical calibration or enables orders.
Source bytes/pins are injected solely to make tampering/missing input detectable
in deterministic synthetic tests; matching SHA-256 is NOT proof of provenance.
Do not connect a passing report to a permit, MT5 or a scheduler.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping

APPROVED_PR13_SHA = "847829378956670e8936bf46c82e685de41145fd"
APPROVED_PARENT_PR12_SHA = "b03e1ba3ee2434744010ac8bdf37904ba19df730"
FROZEN_V12_PREREG_GIT_BLOB = "c7dcf520fe2a3b12437cec6a1b5dd06c25494d5f"
OWNER_APPROVAL_COMMENT_ID = 6256228112
REQUIRED_SOURCE_IDS = (
    "exness_xauusd_hours", "exness_holiday_dst", "london_session",
    "new_york_session", "bls_calendar", "bea_calendar", "census_calendar",
    "fed_calendar", "dol_calendar", "event_guard_health_blackout",
    "demo_account_identity", "clock_sync", "tick_protocol",
    "collector_source", "host_source", "private_output_policy",
    "broker_fee_swap", "tick_loss_usd_conversion", "pre_demo_quote_proxy_floor",
    "gap_floor", "stress_event_external", "nonoverlap_components",
    "supervised_exit_reconciliation",
)
BLOCKED_ACTIONS = (
    "pr_merge", "vps_access", "broker_capture", "mt5_config_changes",
    "external_python_trading", "demo_orders", "live_orders",
    "order_modify_cancel_close",
)


class OfflinePacketError(ValueError):
    """Unknown or inconsistent input: fail closed with NO admission."""


@dataclass(frozen=True, slots=True)
class SourcePacketReview:
    status: str
    packet_sha256: str
    source_count: int
    observation_minutes: int
    eligible_overlap_minutes: int
    latest_synthetic_entry_utc: datetime
    synthetic_flat_deadline_utc: datetime
    source_origin_authenticated: bool = False
    numeric_cost_calibration_admitted: bool = False
    capture_authorized: bool = False
    demo_order_authorized: bool = False


def _time(value: Any, label: str) -> datetime:
    if type(value) is not str:
        raise OfflinePacketError(label + ": missing explicit UTC time")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OfflinePacketError(label + ": invalid UTC time") from exc
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise OfflinePacketError(label + ": non-UTC or naive timestamp")
    return dt.astimezone(UTC)


def _sha(value: Any) -> bool:
    return type(value) is str and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value
    )


def _interval(value: Any, label: str) -> tuple[datetime, datetime]:
    if type(value) is not dict or set(value) != {"start_utc", "end_utc"}:
        raise OfflinePacketError(label + ": missing source interval")
    start = _time(value["start_utc"], label + " start")
    end = _time(value["end_utc"], label + " end")
    if end <= start:
        raise OfflinePacketError(label + ": inverted interval")
    return start, end


def _strict_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise OfflinePacketError(label + ": positive integer required")
    return value


def _safe_json(value: Any) -> bytes:
    def valid(obj: Any) -> None:
        if type(obj) is dict:
            for k, v in obj.items():
                if type(k) is not str:
                    raise OfflinePacketError("non-string packet key")
                valid(v)
        elif type(obj) is list:
            for v in obj:
                valid(v)
        elif type(obj) not in (str, int, bool, type(None)):
            raise OfflinePacketError("float/NaN/noncanonical packet value forbidden")
    valid(value)
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")


def review_v12_capture_proposal(
    packet: Mapping[str, Any],
    source_bytes: Mapping[str, bytes],
    independent_pins: Mapping[str, str],
    *,
    review_utc: datetime,
) -> SourcePacketReview:
    """Pure synthetic preflight schema review; outcome never confers authority.

    A passing result merely reports internally consistent caller-supplied
    material. Independently authenticated source origin, owner permission,
    dated broker market eligibility and actual account risks are NOT proven.
    """
    if type(packet) is not dict:
        raise OfflinePacketError("packet must be canonical mapping")
    now = _time(review_utc.isoformat(), "review clock") if (
        type(review_utc) is datetime
    ) else _time(None, "review clock")
    if packet.get("scope") != "SYNTHETIC_OFFLINE_DESIGN_REHEARSAL_ONLY":
        raise OfflinePacketError("not a synthetic-only packet")
    if (packet.get("approved_design_pr13_sha") != APPROVED_PR13_SHA
            or packet.get("approved_parent_pr12_sha") != APPROVED_PARENT_PR12_SHA
            or packet.get("frozen_v12_prereg_git_blob") != FROZEN_V12_PREREG_GIT_BLOB
            or packet.get("owner_design_comment_id") != OWNER_APPROVAL_COMMENT_ID):
        raise OfflinePacketError("frozen owner-approved design binding mismatch")
    action = packet.get("action_authorizations")
    if type(action) is not dict or set(action) != set(BLOCKED_ACTIONS):
        raise OfflinePacketError("permission fields incomplete or unexpected")
    if any(action[name] is not False for name in BLOCKED_ACTIONS):
        raise OfflinePacketError("no operational authority from design approval")
    if (packet.get("actual_broker_data_used") is not False
            or packet.get("execution_slippage_measured") is not False
            or packet.get("numeric_costs_admitted") is not False):
        raise OfflinePacketError("actual data/fees/real slippage wrongly admitted")

    begin, end = _interval(packet.get("observation"), "observation")
    overlap_begin, overlap_end = _interval(packet.get("entry_overlap"), "overlap")
    broker_begin, broker_end = _interval(packet.get("broker_eligible"), "broker eligibility")
    if now >= begin or end - begin != timedelta(hours=4):
        raise OfflinePacketError("observation not a prospective exactly four-hour window")
    if begin.weekday() >= 5 or begin.date() != end.date():
        raise OfflinePacketError("weekend/overnight observation forbidden")
    if not (broker_begin <= begin < end <= broker_end):
        raise OfflinePacketError("broker eligibility does not enclose whole 4h")
    if not begin <= overlap_begin < overlap_end <= end:
        raise OfflinePacketError("entry overlap must be wholly inside 4h")
    if overlap_begin < broker_begin or overlap_end > broker_end:
        raise OfflinePacketError("overlap not broker eligible")
    if (overlap_begin.second or overlap_end.second
            or overlap_begin.microsecond or overlap_end.microsecond):
        raise OfflinePacketError("overlap boundary not minute aligned")
    overlap_duration = overlap_end - overlap_begin
    if overlap_duration.total_seconds() % 60 or overlap_duration > timedelta(hours=4):
        raise OfflinePacketError("overlap invalid minute alignment/duration")

    # If a release/holiday/maintenance guard blocks the overlap, do NOT
    # retroactively cut/relabel the baseline, even for a single second.
    blocks = packet.get("blocked_event_windows")
    if type(blocks) is not list:
        raise OfflinePacketError("Event Guard block schedule missing")
    for i, block in enumerate(blocks):
        bad_start, bad_end = _interval(block, "blocked event " + str(i))
        if bad_start < overlap_end and bad_end > overlap_begin:
            raise OfflinePacketError("non-event eligible overlap contaminated")
        if bad_start < end and bad_end > begin:
            raise OfflinePacketError("unapproved event/stress capture within 4h")
    if packet.get("full_240m_liquidity_flag") is not True:
        raise OfflinePacketError("240m liquidity claim missing (not independently verified)")
    if packet.get("overlap_event_free_flag") is not True:
        raise OfflinePacketError("non-event overlap claim missing")
    if packet.get("event_guard_healthy_flag") is not True:
        raise OfflinePacketError("unhealthy Event Guard")
    if packet.get("external_python_trade_api_disabled") is not True:
        raise OfflinePacketError("external trading must remain disabled")

    timing = packet.get("flat_plan")
    if type(timing) is not dict or set(timing) != {
        "verified_broker_session_end_utc", "flat_confirmation_lead_seconds",
        "max_holding_seconds", "exit_reconciliation_seconds",
        "owner_attended_plan_only",
    }:
        raise OfflinePacketError("complete attended flat plan missing")
    eligible_end = _time(timing["verified_broker_session_end_utc"], "broker end")
    if eligible_end != broker_end or timing["owner_attended_plan_only"] is not True:
        raise OfflinePacketError("flat exit plan inconsistent with broker cutoff")
    flat_lead = _strict_int(timing["flat_confirmation_lead_seconds"], "flat lead")
    hold = _strict_int(timing["max_holding_seconds"], "holding limit")
    settle = _strict_int(timing["exit_reconciliation_seconds"], "exit settle")
    flat_deadline = min(overlap_end, broker_end) - timedelta(seconds=flat_lead)
    entry_cutoff = flat_deadline - timedelta(seconds=hold + settle)
    if entry_cutoff <= overlap_begin or flat_deadline >= overlap_end:
        raise OfflinePacketError("no strictly early owner-attended exit/flat budget")

    sources = packet.get("sources")
    if type(sources) is not dict or set(sources) != set(REQUIRED_SOURCE_IDS):
        raise OfflinePacketError("missing or unexpected source classes")
    if (set(source_bytes) != set(REQUIRED_SOURCE_IDS)
            or set(independent_pins) != set(REQUIRED_SOURCE_IDS)):
        raise OfflinePacketError("independently injected source bytes/pins incomplete")
    for name in REQUIRED_SOURCE_IDS:
        record = sources[name]
        if type(record) is not dict or set(record) != {
            "sha256", "source_url_or_protected_locator",
            "retrieved_utc", "expected_regime",
        }:
            raise OfflinePacketError(name + ": incomplete source provenance")
        digest, pinned, raw = record["sha256"], independent_pins[name], source_bytes[name]
        if type(raw) is not bytes or not _sha(digest) or not _sha(pinned):
            raise OfflinePacketError(name + ": invalid private evidence or pin")
        if digest != pinned or hashlib.sha256(raw).hexdigest() != digest:
            raise OfflinePacketError(name + ": private source-byte SHA mismatch")
        if (type(record["source_url_or_protected_locator"]) is not str
                or not record["source_url_or_protected_locator"].strip()
                or type(record["expected_regime"]) is not str
                or not record["expected_regime"].strip()):
            raise OfflinePacketError(name + ": origin or regime unregistered")
        observed = _time(record["retrieved_utc"], name + " observed UTC")
        if observed > now:
            raise OfflinePacketError(name + ": future-dated source")
    canonical = _safe_json(packet)
    return SourcePacketReview(
        status="SYNTHETIC_OFFLINE_SCHEMA_REVIEW_ONLY__NOT_CAPTURE_OR_DEMO_ADMISSION",
        packet_sha256=hashlib.sha256(canonical).hexdigest(),
        source_count=len(REQUIRED_SOURCE_IDS),
        observation_minutes=240,
        eligible_overlap_minutes=int(overlap_duration.total_seconds() // 60),
        latest_synthetic_entry_utc=entry_cutoff,
        synthetic_flat_deadline_utc=flat_deadline,
    )
