"""Deterministic offline verifier for prospective 4h UTC session candidates.

This cannot authenticate source origins or grant capture/DEMO-ADMIT permission.
Official Exness, event and broker sources must be independently archived and
hashed before selection. Real source details are absent in the current repo.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any


class WindowReadinessError(ValueError):
    """Fail closed: not a verified four-hour restricted-session window."""


def utc(text: object) -> datetime:
    if type(text) is not str:
        raise WindowReadinessError("missing UTC timestamp")
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WindowReadinessError("bad UTC timestamp") from exc
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise WindowReadinessError("timestamp not explicit UTC")
    return value.astimezone(UTC)


def _digest(value: object) -> bool:
    return (type(value) is str and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def _interval(value: Mapping[str, Any]) -> tuple[datetime, datetime]:
    before = utc(value.get("start_utc"))
    after = utc(value.get("end_utc"))
    if after <= before:
        raise WindowReadinessError("inverted source interval")
    return before, after


def check_prospective_window(
    registration: Mapping[str, Any],
    independent_source_pins: Mapping[str, str],
    *,
    decision_time_utc: datetime,
) -> str:
    """Return REVIEWABLE_WINDOW_ONLY after syntactic/interval checks.

    Does NOT check that signed Exness or official Event Guard source was
    authentic. Pin equality is not itself a signature or independent source.
    No result from this function is a broker action/approval token.
    """
    if decision_time_utc.tzinfo is None or decision_time_utc.utcoffset() != timedelta(0):
        raise WindowReadinessError("decision clock not UTC")
    start, end = _interval({
        "start_utc": registration.get("exact_window_start_utc"),
        "end_utc": registration.get("exact_window_end_utc"),
    })
    if end - start != timedelta(hours=4):
        raise WindowReadinessError("window must span exactly 240 consecutive minutes")
    if decision_time_utc >= start:
        raise WindowReadinessError("not prospective: window already begun")
    if start.weekday() >= 5 or end.date() != start.date():
        raise WindowReadinessError("weekend or overnight restricted-state window")
    if registration.get("scope") != "DEMO_LIFECYCLE_ONLY":
        raise WindowReadinessError("not demo-only registration")
    if registration.get("execution_disabled") is not True:
        raise WindowReadinessError("trading-disable evidence not registered")
    if registration.get("event_guard_healthy") is not True:
        raise WindowReadinessError("Event Guard unhealthy or unverified")
    if registration.get("broker_xauusd_trade_enabled") is not True:
        raise WindowReadinessError("broker instrument not trade-enabled")
    if registration.get("holidays_reopen_rollover_excluded") is not True:
        raise WindowReadinessError("holiday/reopen/rollover scope unknown")
    if registration.get("shock_state") != "NORMAL":
        raise WindowReadinessError("shock state not normal")

    ids = (
        "exness_symbol_schedule", "london_session",
        "new_york_session", "bls", "bea", "census",
        "federal_reserve", "event_guard", "broker_identity",
        "collector_source", "tick_protocol", "holiday_and_dst",
    )
    registered = registration.get("source_sha256")
    if type(registered) is not dict or set(registered) != set(ids):
        raise WindowReadinessError("incomplete source provenance set")
    if set(independent_source_pins) != set(ids):
        raise WindowReadinessError("missing independently supplied source pins")
    for identifier in ids:
        recorded = registered[identifier]
        pinned = independent_source_pins[identifier]
        if not _digest(recorded) or not _digest(pinned) or recorded != pinned:
            raise WindowReadinessError(f"{identifier}: mismatched/unknown source hash")

    for name in ("exness_trade_windows", "london_liquid_windows",
                 "new_york_liquid_windows"):
        windows = registration.get(name)
        if not isinstance(windows, list) or not windows:
            raise WindowReadinessError(name + " source windows missing")
        if not any(
            _interval(w)[0] <= start and end <= _interval(w)[1]
            for w in windows
            if isinstance(w, dict)
        ):
            raise WindowReadinessError(name + ": not a full four-hour inclusion")

    blocks = registration.get("blocked_event_windows")
    if not isinstance(blocks, list):
        raise WindowReadinessError("blocked event schedule missing")
    for block in blocks:
        if not isinstance(block, dict):
            raise WindowReadinessError("invalid blocked event")
        left, right = _interval(block)
        if left < end and right > start:
            raise WindowReadinessError("blocked event overlaps four-hour window")

    return "REVIEWABLE_WINDOW_ONLY_NOT_OWNER_AUTHORIZATION"
