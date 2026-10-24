# ruff: noqa: I001
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from xauusd_agent.guards.event_guard import ProtectedEvent
from xauusd_agent.guards.v2_official_source_gate import VerifiedOfficialSnapshot

from xauusd_demo.envelope import DemoSafetyError
from xauusd_demo.official_calendar_supervisor import DurableOfficialCalendarSupervisor

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)
AGENCIES = {
    "BLS": "bls.gov", "BEA": "bea.gov", "FED": "federalreserve.gov",
    "CENSUS": "census.gov", "DOL": "dol.gov",
}


def snapshots(now=NOW, *, offset=timedelta(days=3)):
    return tuple(
        VerifiedOfficialSnapshot(
            agency=a, source_host=host, raw_sha256=chr(97 + i) * 64,
            parser_version="FIXTURE-PARSER-V1",
            captured_utc=NOW - timedelta(minutes=5),
            valid_through_utc=NOW + timedelta(hours=6),
            event_horizon_utc=NOW + timedelta(days=7),
            rights_for_local_processing_verified=True,
            parser_schema_verified=True,
            authoritative_release_coverage_verified=True,
            revision_conflicts_absent=True,
            events=(ProtectedEvent(
                f"{a}-release", NOW + offset, "TIER_1"
            ),),
        )
        for i, (a, host) in enumerate(AGENCIES.items())
    )


def observe(path, *, now=NOW, sources=None, shock=False, normalized=True):
    with DurableOfficialCalendarSupervisor(path) as supervisor:
        return supervisor.observe(
            observed_at=now,
            snapshots=snapshots() if sources is None else sources,
            shock_locked=shock, normalized=normalized,
        )


def test_complete_fresh_sources_mark_calendar_clear_but_not_order_authority(
    tmp_path: Path,
):
    r = observe(tmp_path / "calendar.sqlite")
    assert r.new_entry_clear
    assert r.execution_permitted is False
    assert r.blocking_event_ids == ()


def test_missing_stale_unknown_shock_and_event_lock_veto(
    tmp_path: Path,
):
    cases = [
        {"sources": snapshots()[:-1]},
        {"sources": tuple(replace(s, valid_through_utc=NOW - timedelta(seconds=1))
                          for s in snapshots())},
        {"sources": tuple(replace(s, event_horizon_utc=NOW + timedelta(hours=1))
                          for s in snapshots())},
        {"sources": tuple(replace(s, parser_schema_verified=False)
                          for s in snapshots())},
        {"shock": None},
        {"normalized": None},
        {"shock": True},
        {"sources": snapshots(offset=timedelta(minutes=10))},
    ]
    for i, kw in enumerate(cases):
        result = observe(tmp_path / f"missing_{i}.sqlite", **kw)
        assert not result.new_entry_clear


def test_official_future_event_disappearance_latches_persistently(
    tmp_path: Path,
):
    path = tmp_path / "disappeared.sqlite"
    assert observe(path).new_entry_clear
    originals = snapshots()
    changed = (replace(originals[0], events=()), *originals[1:])
    result = observe(path, now=NOW + timedelta(minutes=1), sources=changed)
    assert result.state == "QUARANTINED"
    assert not observe(path, now=NOW + timedelta(minutes=2)).new_entry_clear


def test_moved_event_keeps_old_pre_lock_window(
    tmp_path: Path,
):
    path = tmp_path / "moved.sqlite"
    originals = snapshots(offset=timedelta(hours=1))
    assert observe(path, sources=originals).new_entry_clear
    future = NOW + timedelta(minutes=45)
    # Update all original records to keep complete fresh source coverage.
    moved = (
        replace(originals[0], events=(ProtectedEvent(
            "BLS-release", NOW + timedelta(days=3), "TIER_1"
        ),)),
        *originals[1:],
    )
    result = observe(path, now=future, sources=moved)
    assert not result.new_entry_clear
    assert "PREVIOUS_LOCK_BLS-release" in result.blocking_event_ids


def test_control_rollback_and_restart_cannot_clear_latch(tmp_path: Path):
    path = tmp_path / "rollback.sqlite"
    assert observe(path, now=NOW).new_entry_clear
    result = observe(path, now=NOW - timedelta(seconds=1))
    assert result.state == "QUARANTINED"
    assert observe(path).state == "QUARANTINED"


def test_no_snapshots_never_create_event_clear(tmp_path: Path):
    result = observe(tmp_path / "missing.sqlite", sources=())
    assert not result.new_entry_clear


def test_naive_utc_rejected(tmp_path: Path):
    path = tmp_path / "timezone.sqlite"
    with DurableOfficialCalendarSupervisor(path) as supervisor:
        with pytest.raises(DemoSafetyError):
            supervisor.observe(
                observed_at=NOW.replace(tzinfo=None),
                snapshots=snapshots(), shock_locked=False, normalized=True,
            )
