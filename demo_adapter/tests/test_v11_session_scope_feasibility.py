"""Synthetic proof of Exness published trading-center overlap, not instrument admission."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from scripts.v11_session_scope_feasibility import (
    CenterInterval,
    intersection,
    published_exness_center_comparison,
)


@pytest.mark.parametrize(
    ("season", "expected_start", "expected_minutes"),
    [
        ("US_SUMMER", 13, 180),
        ("US_WINTER", 14, 120),
    ],
)
def test_no_full_4h_inside_published_london_new_york_centers(
    season: str, expected_start: int, expected_minutes: int
) -> None:
    result = published_exness_center_comparison("2026-10-20", season)
    assert result.published_overlap.start_utc.hour == expected_start
    assert result.published_overlap.start_utc.minute == 30
    assert result.published_overlap_minutes == expected_minutes
    assert not result.four_hours_fully_inside_published_overlap_possible
    assert result.proposed_observation.duration_minutes == 240
    assert result.proposed_observation_contains_entire_overlap
    assert result.minutes_of_observation_inside_published_overlap == expected_minutes
    assert result.proposed_entry_regime.startswith("OVERLAP_ONLY")
    assert result.external_source_verified is False
    assert result.owner_session_scope_amendment_adopted is False
    assert result.trading_or_capture_authorized is False


def test_summer_proposal_has_one_hour_london_only_not_for_demo_entry() -> None:
    result = published_exness_center_comparison("2026-10-22", "US_SUMMER")
    assert result.proposed_observation.start_utc.isoformat() == (
        "2026-10-22T12:30:00+00:00"
    )
    assert result.published_overlap.start_utc.isoformat() == (
        "2026-10-22T13:30:00+00:00"
    )
    assert result.published_overlap.end_utc.isoformat() == (
        "2026-10-22T16:30:00+00:00"
    )


def test_intersection_disjoint_returns_none() -> None:
    left = CenterInterval(
        datetime(2026, 10, 20, 8, tzinfo=UTC),
        datetime(2026, 10, 20, 10, tzinfo=UTC),
    )
    right = CenterInterval(
        datetime(2026, 10, 20, 11, tzinfo=UTC),
        datetime(2026, 10, 20, 13, tzinfo=UTC),
    )
    assert intersection(left, right) is None


def test_invalid_utc_and_season_fails_closed() -> None:
    with pytest.raises(ValueError, match="not valid UTC"):
        CenterInterval(datetime(2026, 10, 20, 8),
                       datetime(2026, 10, 20, 12, tzinfo=UTC))
    with pytest.raises(ValueError, match="unrecognized"):
        published_exness_center_comparison("2026-10-20", "GUESS")
