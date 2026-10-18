"""Prospective synthetic session/official calendar test fixtures, no broker reads."""
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from scripts.v11_window_readiness import (
    WindowReadinessError,
    check_prospective_window,
)

SOURCE_IDS = (
    "exness_symbol_schedule", "london_session",
    "new_york_session", "bls", "bea", "census",
    "federal_reserve", "event_guard", "broker_identity",
    "collector_source", "tick_protocol", "holiday_and_dst",
)


def example() -> tuple[dict[str, object], dict[str, str]]:
    sha = {key: str(n % 10) * 64 for n, key in enumerate(SOURCE_IDS)}
    item: dict[str, object] = {
        "exact_window_start_utc": "2026-10-20T13:00:00Z",
        "exact_window_end_utc": "2026-10-20T17:00:00Z",
        "scope": "DEMO_LIFECYCLE_ONLY",
        "execution_disabled": True,
        "event_guard_healthy": True,
        "broker_xauusd_trade_enabled": True,
        "holidays_reopen_rollover_excluded": True,
        "shock_state": "NORMAL",
        "source_sha256": sha,
        "exness_trade_windows": [{
            "start_utc": "2026-10-20T12:00:00Z",
            "end_utc": "2026-10-20T20:00:00Z",
        }],
        "london_liquid_windows": [{
            "start_utc": "2026-10-20T12:00:00Z",
            "end_utc": "2026-10-20T18:00:00Z",
        }],
        "new_york_liquid_windows": [{
            "start_utc": "2026-10-20T13:00:00Z",
            "end_utc": "2026-10-20T18:00:00Z",
        }],
        "blocked_event_windows": [],
    }
    return item, sha


def review(item: dict[str, object], pins: dict[str, str] | None = None) -> str:
    _, default = example()
    return check_prospective_window(
        item, default if pins is None else pins,
        decision_time_utc=datetime(2026, 10, 18, 12, tzinfo=UTC),
    )


def test_synthetic_full_overlap_not_real_world_certification() -> None:
    window, pins = example()
    assert review(window, pins) == "REVIEWABLE_WINDOW_ONLY_NOT_OWNER_AUTHORIZATION"


def test_official_exness_center_three_hour_overlap_rejected() -> None:
    candidate, _ = example()
    candidate["london_liquid_windows"] = [{
        "start_utc": "2026-10-20T08:00:00Z",
        "end_utc": "2026-10-20T16:30:00Z",
    }]
    candidate["new_york_liquid_windows"] = [{
        "start_utc": "2026-10-20T13:30:00Z",
        "end_utc": "2026-10-20T20:00:00Z",
    }]
    with pytest.raises(WindowReadinessError, match="full four-hour inclusion"):
        review(candidate)


def test_october_20_bls_1400_utc_event_requires_exclusion() -> None:
    candidate, _ = example()
    candidate["blocked_event_windows"] = [{
        "start_utc": "2026-10-20T13:45:00Z",
        "end_utc": "2026-10-20T14:15:00Z",
    }]
    with pytest.raises(WindowReadinessError, match="blocked event"):
        review(candidate)


@pytest.mark.parametrize(("field", "value"), [
    ("exact_window_end_utc", "2026-10-20T16:59:59Z"),
    ("exact_window_start_utc", "2026-10-18T13:00:00Z"),
    ("scope", "LIVE"),
    ("event_guard_healthy", None),
    ("broker_xauusd_trade_enabled", False),
    ("execution_disabled", False),
    ("holidays_reopen_rollover_excluded", None),
    ("shock_state", "UNKNOWN"),
    ("blocked_event_windows", None),
    ("exness_trade_windows", []),
])
def test_unknown_or_invalid_window_never_becomes_reviewable(
    field: str, value: object,
) -> None:
    candidate, _ = example()
    candidate[field] = value
    with pytest.raises(WindowReadinessError):
        review(candidate)


def test_mismatched_or_missing_independent_source_hashes_rejected() -> None:
    candidate, pins = example()
    changed = dict(pins)
    changed["bls"] = "f" * 64
    with pytest.raises(WindowReadinessError, match="bls"):
        review(candidate, changed)
    candidate = deepcopy(candidate)
    source = candidate["source_sha256"]
    assert isinstance(source, dict)
    source.pop("event_guard")
    with pytest.raises(WindowReadinessError, match="provenance"):
        review(candidate, pins)


def test_nonprospective_or_non_utc_decision_rejected() -> None:
    candidate, pins = example()
    with pytest.raises(WindowReadinessError, match="not prospective"):
        check_prospective_window(
            candidate, pins, decision_time_utc=datetime(2026, 10, 21, tzinfo=UTC)
        )
    with pytest.raises(WindowReadinessError, match="not UTC"):
        check_prospective_window(
            candidate, pins, decision_time_utc=datetime(2026, 10, 18)
        )
