"""Broker-neutral chronological/session tests; no external MT5 data is fabricated as evidence."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from xauusd_agent.features.v2_chronology_audit import (
    SessionCalendarEvidence,
    SessionInterval,
    audit_seven_frame_chronology,
)
from xauusd_agent.features.v2_market_context import ContextBar, ContextTimeframe

NOW = datetime(2026, 10, 22, 12, tzinfo=UTC)
PRICE = Decimal("3000")
SOURCE = "c" * 64


def series(tf: ContextTimeframe) -> tuple[ContextBar, ...]:
    # W1 opens Sunday 00 UTC but does not imply Sunday is tradable.
    latest = (
        datetime(2026, 10, 11, tzinfo=UTC)
        if tf is ContextTimeframe.W1
        else NOW - tf.duration * 2
    )
    return tuple(
        ContextBar(
            timeframe=tf, open_time=latest - tf.duration * (2 - i),
            open=PRICE, high=PRICE + 1, low=PRICE - 1,
            close=PRICE, tick_volume=50,
        ) for i in range(3)
    )


def frames():
    return {tf: series(tf) for tf in ContextTimeframe}


def calendar(*, verified=True, anchor=True, intervals=None):
    return SessionCalendarEvidence(
        broker_session_source_sha256=SOURCE,
        revision="synthetic-test-only",
        coverage_start_utc=datetime(2026, 9, 1, tzinfo=UTC),
        coverage_end_utc=datetime(2026, 10, 30, tzinfo=UTC),
        open_intervals=tuple(
            intervals if intervals is not None else (
                SessionInterval(
                    NOW - timedelta(hours=2), NOW + timedelta(hours=2)
                ),
            )
        ),
        source_verified=verified,
        session_coverage_complete=True,
        weekly_sunday_utc_anchor_verified=anchor,
    )


def test_full_bars_and_confirmed_broker_session_source_can_pass_pure_audit() -> None:
    verdict = audit_seven_frame_chronology(
        frames=frames(), as_of=NOW, calendar=calendar()
    )
    assert verdict.accepted is True
    assert verdict.execution_permitted is False
    assert verdict.reviewed_frames == 7


def test_actual_owner_snapshot_cannot_infer_weekly_calendar_approval() -> None:
    verdict = audit_seven_frame_chronology(
        frames=frames(), as_of=NOW, calendar=None
    )
    assert verdict.accepted is False
    assert "W1_ANCHOR_UNVERIFIED" in verdict.reasons
    assert "OFFICIAL_BROKER_SESSION_SOURCE_UNVERIFIED" in verdict.reasons


def test_sunday_anchor_is_nominal_bucket_not_friday_last_trade() -> None:
    x = frames()
    week = list(x[ContextTimeframe.W1])
    week[-1] = replace(
        week[-1], open_time=week[-1].open_time + timedelta(hours=2)
    )
    x[ContextTimeframe.W1] = tuple(week)
    report = audit_seven_frame_chronology(
        frames=x, as_of=NOW, calendar=calendar()
    )
    assert "W1_BROKER_ANCHOR_CONFLICT" in report.reasons


def test_unexplained_missing_m1_during_verified_open_session_rejected() -> None:
    x = frames()
    m1 = list(x[ContextTimeframe.M1])
    m1[-1] = replace(
        m1[-1], open_time=m1[-1].open_time + timedelta(minutes=1)
    )
    x[ContextTimeframe.M1] = tuple(m1)
    report = audit_seven_frame_chronology(
        frames=x, as_of=NOW,
        calendar=calendar(
            intervals=(SessionInterval(
                NOW - timedelta(hours=2), NOW + timedelta(hours=2)
            ),),
        ),
    )
    assert "M1_MISSING_WHILE_SESSION_OPEN" in report.reasons


def test_missing_m1_in_verified_closed_session_is_not_automatically_corrupt() -> None:
    x = frames()
    m1 = list(x[ContextTimeframe.M1])
    m1[-1] = replace(
        m1[-1], open_time=m1[-1].open_time + timedelta(minutes=1)
    )
    x[ContextTimeframe.M1] = tuple(m1)
    closed_session = calendar(intervals=(
        SessionInterval(
            NOW - timedelta(days=5), NOW - timedelta(days=4)
        ),
    ))
    report = audit_seven_frame_chronology(
        frames=x, as_of=NOW, calendar=closed_session
    )
    assert report.accepted is True


def test_incomplete_and_bad_coverage_fail_closed() -> None:
    x = frames()
    del x[ContextTimeframe.D1]
    c = calendar()
    result = audit_seven_frame_chronology(
        frames=x, as_of=NOW, calendar=c
    )
    assert "SEVEN_FRAME_INCOMPLETE" in result.reasons
    assert "D1_MISSING" in result.reasons
    narrow = replace(
        c, coverage_start_utc=NOW - timedelta(days=2),
    )
    result = audit_seven_frame_chronology(
        frames=frames(), as_of=NOW, calendar=narrow
    )
    assert "W1_CALENDAR_COVERAGE_INSUFFICIENT" in result.reasons


def test_duplicate_future_and_unverified_sessions_are_fatal() -> None:
    x = frames()
    old = list(x[ContextTimeframe.H1])
    old[-1] = old[-2]
    x[ContextTimeframe.H1] = tuple(old)
    result = audit_seven_frame_chronology(
        frames=x, as_of=NOW, calendar=calendar(verified=False, anchor=False)
    )
    assert "H1_NOT_STRICTLY_ORDERED" in result.reasons
    assert "OFFICIAL_BROKER_SESSION_SOURCE_UNVERIFIED" in result.reasons
    assert "W1_ANCHOR_UNVERIFIED" in result.reasons


def test_invalid_session_metadata_rejected_early() -> None:
    with pytest.raises(ValueError, match="source SHA"):
        replace(calendar(), broker_session_source_sha256="bad")
    with pytest.raises(ValueError, match="positive"):
        SessionInterval(NOW, NOW)



def test_empty_or_incomplete_session_schedule_must_not_pass():
    with pytest.raises(ValueError, match="cannot be empty"):
        calendar(intervals=())
    incomplete = replace(calendar(), session_coverage_complete=False)
    result = audit_seven_frame_chronology(
        frames=frames(), as_of=NOW, calendar=incomplete
    )
    assert not result.accepted
    assert "SESSION_OPEN_CLOSED_CLASSIFICATION_INCOMPLETE" in result.reasons
