from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from xauusd_agent.guards.event_guard import ProtectedEvent
from xauusd_agent.guards.v2_official_source_gate import (
    VerifiedOfficialSnapshot,
    admit_official_calendar,
    checked_new_york_release_time,
)

NOW = datetime(2026, 10, 22, 12, tzinfo=UTC)
HOSTS = {
    "BLS": "www.bls.gov", "BEA": "www.bea.gov",
    "FED": "www.federalreserve.gov", "CENSUS": "www.census.gov",
    "DOL": "www.dol.gov",
}


def snapshot(agency, events=()):
    return VerifiedOfficialSnapshot(
        agency=agency, source_host=HOSTS[agency],
        raw_sha256="a" * 64,
        parser_version="synthetic-unit-test",
        captured_utc=NOW - timedelta(hours=1),
        valid_through_utc=NOW + timedelta(hours=6),
        event_horizon_utc=NOW + timedelta(days=7),
        rights_for_local_processing_verified=True,
        parser_schema_verified=True,
        authoritative_release_coverage_verified=True,
        revision_conflicts_absent=True,
        events=tuple(events),
    )


def all_snapshots():
    return tuple(snapshot(k) for k in HOSTS)


def check(snapshots=None, shock=False, normalized=True):
    return admit_official_calendar(
        observed_at=NOW,
        snapshots=all_snapshots() if snapshots is None else snapshots,
        shock_locked=shock, normalized=normalized,
    )


def test_five_synthetic_sources_without_events_can_only_pass_gate_not_trade():
    r = check()
    assert r.admitted
    assert r.observation.source_healthy is True
    assert r.execution_permitted is False


def test_missing_agency_unknown_rights_or_stale_snapshot_deny():
    assert "OFFICIAL_AGENCY_COVERAGE_INCOMPLETE" in check(
        all_snapshots()[:-1]
    ).reasons
    for changed in (
        {"rights_for_local_processing_verified": False},
        {"parser_schema_verified": False},
        {"authoritative_release_coverage_verified": False},
        {"revision_conflicts_absent": False},
        {"valid_through_utc": NOW - timedelta(seconds=1),
         "captured_utc": NOW - timedelta(hours=2)},
    ):
        s = list(all_snapshots())
        s[0] = replace(s[0], **changed)
        assert not check(tuple(s)).admitted


def test_tier_one_fomc_event_blocks_in_pre_window():
    event = ProtectedEvent("FOMC-TEST", NOW + timedelta(minutes=10), "TIER_1")
    snaps = list(all_snapshots())
    snaps[2] = snapshot("FED", (event,))
    result = check(tuple(snaps))
    assert not result.admitted
    assert any("PRE_LOCK" in c for c in result.reasons)


def test_unknown_shock_and_normalization_fail_closed():
    assert not check(shock=None).admitted
    assert not check(normalized=None).admitted


def test_domain_spoofing_fails_even_when_url_looks_official():
    with pytest.raises(ValueError, match="official"):
        replace(snapshot("BLS"), source_host="www.bls.gov.example.com")


def test_dst_local_release_conversion_is_explicit():
    assert checked_new_york_release_time(
        datetime(2026, 10, 22, 8, 30)
    ) == datetime(2026, 10, 22, 12, 30, tzinfo=UTC)
    with pytest.raises(ValueError, match="DST"):
        checked_new_york_release_time(datetime(2026, 11, 1, 1, 30))
    with pytest.raises(ValueError, match="DST"):
        checked_new_york_release_time(datetime(2026, 3, 8, 2, 30))
