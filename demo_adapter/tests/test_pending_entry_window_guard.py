# ruff: noqa: I001
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from xauusd_agent.guards.event_guard import ProtectedEvent
from xauusd_agent.guards.v2_official_source_gate import VerifiedOfficialSnapshot
from xauusd_demo.pending_entry_window_guard import screen_pending_entry_window

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)
SOURCES = {
    "BLS": "bls.gov", "BEA": "bea.gov", "FED": "federalreserve.gov",
    "CENSUS": "census.gov", "DOL": "dol.gov",
}


def snapshots(*, event_after_minutes=240, tier="TIER_1"):
    return tuple(
        VerifiedOfficialSnapshot(
            agency=agency, source_host=host,
            raw_sha256=hex(i + 10)[2] * 64, parser_version="FIXTURE-1",
            captured_utc=NOW - timedelta(minutes=1),
            valid_through_utc=NOW + timedelta(hours=6),
            event_horizon_utc=NOW + timedelta(days=7),
            rights_for_local_processing_verified=True,
            parser_schema_verified=True,
            authoritative_release_coverage_verified=True,
            revision_conflicts_absent=True,
            events=(
                ProtectedEvent(
                    f"{agency}-event",
                    NOW + timedelta(minutes=event_after_minutes),
                    tier,
                ),
            ),
        )
        for i, (agency, host) in enumerate(SOURCES.items())
    )


def inspect(**change):
    params = dict(
        now=NOW, expires_utc=NOW + timedelta(minutes=40),
        session_verified_through_utc=NOW + timedelta(hours=3),
        snapshots=snapshots(), shock_locked=False, normalized=True,
    )
    params.update(change)
    return screen_pending_entry_window(**params)


def test_full_pending_lifetime_clear_including_settlement_margin():
    r = inspect()
    assert r.allowed_to_proceed_to_other_gates
    assert not r.execution_permitted


@pytest.mark.parametrize("minutes,tier", [
    (31, "TIER_1"), (40, "TIER_1"), (70, "TIER_1"),
    (50, "TIER_2"), (55, "TIER_2"),
])
def test_future_news_lock_intersecting_pending_expiration_is_denied(minutes, tier):
    r = inspect(snapshots=snapshots(event_after_minutes=minutes, tier=tier))
    assert not r.allowed_to_proceed_to_other_gates
    assert "PENDING_WINDOW_OVERLAPS_OFFICIAL_EVENT" in r.reasons


def test_prelock_starts_after_expiry_and_margin_is_eligible():
    # TIER_1 at +73m -> prelock +43m; expiry +40m +1m margin clear.
    assert inspect(snapshots=snapshots(event_after_minutes=73)).allowed_to_proceed_to_other_gates


@pytest.mark.parametrize("change", [
    {"session_verified_through_utc": None},
    {"session_verified_through_utc": NOW + timedelta(minutes=40)},
    {"expires_utc": NOW},
    {"expires_utc": NOW + timedelta(minutes=61)},
    {"shock_locked": True},
    {"normalized": None},
    {"snapshots": ()},
    {"snapshots": snapshots()[:-1]},
])
def test_unverified_pending_window_never_advances(change):
    r = inspect(**change)
    assert not r.allowed_to_proceed_to_other_gates


def test_stale_agency_revision_conflict_and_cancelled_future():
    s = snapshots()
    bad = tuple(replace(item, revision_conflicts_absent=False) for item in s)
    assert not inspect(snapshots=bad).allowed_to_proceed_to_other_gates
    stale = tuple(replace(item, valid_through_utc=NOW-timedelta(seconds=1)) for item in s)
    assert not inspect(snapshots=stale).allowed_to_proceed_to_other_gates
    canceled = tuple(replace(
        item, events=(ProtectedEvent(
            f"{item.agency}-event", NOW+timedelta(minutes=32),
            "TIER_1", status="CANCELLED"
        ),)
    ) for item in s)
    # Cancelled independently verified by official source can be ignored;
    # missing/unknown source never can.
    assert inspect(snapshots=canceled).allowed_to_proceed_to_other_gates


def test_clock_timezone_and_session_near_close_fails_closed():
    assert not inspect(now=NOW.replace(tzinfo=None)).allowed_to_proceed_to_other_gates
    assert not inspect(
        session_verified_through_utc=(NOW+timedelta(minutes=40,seconds=50))
    ).allowed_to_proceed_to_other_gates
