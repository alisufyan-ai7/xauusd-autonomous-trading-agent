# ruff: noqa: I001
"""Durable official-source Event Guard revision/health supervisor.

Uses the *existing* pure admission and event_guard. VerifiedOfficialSnapshot
objects must come from an independently audited multiagency capture/parser,
NOT from a model or caller-supplied "news clear" Boolean. A disappearing
future event permanently quarantines until human P1 review. Moved schedules
retain the original lock window. No network or order APIs in this module.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from xauusd_agent.guards.event_guard import (
    EventObservation, ProtectedEvent, evaluate_event_guard,
)
from xauusd_agent.guards.v2_official_source_gate import (
    VerifiedOfficialSnapshot, admit_official_calendar,
)

from .envelope import DemoSafetyError


@dataclass(frozen=True, slots=True)
class CalendarCycle:
    state: str
    reasons: tuple[str, ...]
    blocking_event_ids: tuple[str, ...]
    execution_permitted: bool = False

    @property
    def new_entry_clear(self) -> bool:
        return self.state == "EVENT_CLEAR"

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("a calendar heartbeat never grants MT5 execution")


class DurableOfficialCalendarSupervisor:
    """One-writer SQLite UTC source revision latch, KILLED on unknown."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, isolation_level=None)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS event_guard_control (
                id INTEGER PRIMARY KEY CHECK(id=1),
                last_utc TEXT, quarantined INTEGER NOT NULL,
                reason TEXT NOT NULL
            ) STRICT"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS event_schedule_ledger (
                event_id TEXT PRIMARY KEY, scheduled_utc TEXT NOT NULL,
                tier TEXT NOT NULL, status TEXT NOT NULL
            ) STRICT"""
        )
        self.conn.execute(
            "INSERT OR IGNORE INTO event_guard_control VALUES(1,NULL,0,'INITIAL')"
        )

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> DurableOfficialCalendarSupervisor:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _latch(self, reason: str) -> CalendarCycle:
        self.conn.execute(
            "UPDATE event_guard_control SET quarantined=1,reason=? WHERE id=1",
            (reason[:150],),
        )
        return CalendarCycle("QUARANTINED", (reason,), ())

    def observe(
        self,
        *,
        observed_at: datetime,
        snapshots: tuple[VerifiedOfficialSnapshot, ...],
        shock_locked: bool | None,
        normalized: bool | None,
    ) -> CalendarCycle:
        if observed_at.tzinfo is None or observed_at.utcoffset() != timedelta(0):
            raise DemoSafetyError("official calendar cycle requires exact UTC")
        row = self.conn.execute(
            "SELECT last_utc, quarantined FROM event_guard_control WHERE id=1"
        ).fetchone()
        if row is None or row[1]:
            return CalendarCycle("QUARANTINED", ("EVENT_REVISION_LATCHED",), ())
        if row[0] is not None and observed_at < datetime.fromisoformat(row[0]):
            return self._latch("EVENT_CLOCK_ROLLBACK")
        try:
            admission = admit_official_calendar(
                observed_at=observed_at, snapshots=snapshots,
                shock_locked=shock_locked, normalized=normalized,
            )
        except (ValueError, TypeError):
            return CalendarCycle("NO_TRADE", ("SOURCE_SCHEMA_INVALID",), ())
        # The normalized Event Guard may prohibit an entry while the sources
        # are otherwise healthy. Still retain authoritative observations to
        # compare revisions, but no incomplete source may rewrite the ledger.
        if any(
            x in admission.reasons
            for x in (
                "OFFICIAL_AGENCY_COVERAGE_INCOMPLETE", "DUPLICATE_AGENCY_SNAPSHOT",
            )
        ):
            return CalendarCycle("NO_TRADE", admission.reasons, ())
        if admission.observation.source_healthy is not True:
            return CalendarCycle("NO_TRADE", admission.reasons, ())
        events = admission.observation.events
        if events is None:
            return CalendarCycle("NO_TRADE", admission.reasons, ())
        current = {e.event_id: e for e in events}
        prior_rows = self.conn.execute(
            "SELECT event_id,scheduled_utc,tier,status FROM event_schedule_ledger"
        ).fetchall()
        old = {
            str(r[0]): ProtectedEvent(
                str(r[0]), datetime.fromisoformat(r[1]), str(r[2]), str(r[3])
            )
            for r in prior_rows
        }
        # A missing future agency event is NOT an implied cancellation.
        for ident, previous in old.items():
            if (
                ident not in current
                and previous.status != "CANCELLED"
                and previous.scheduled_utc >= observed_at
            ):
                return self._latch("FUTURE_OFFICIAL_EVENT_DISAPPEARED")
        locks = list(events)
        for ident, previous in old.items():
            replacement = current.get(ident)
            if (
                replacement is not None
                and previous.scheduled_utc != replacement.scheduled_utc
                and previous.status != "CANCELLED"
                and observed_at < previous.scheduled_utc + timedelta(minutes=30)
            ):
                locks.append(ProtectedEvent(
                    "PREVIOUS_LOCK_" + ident, previous.scheduled_utc,
                    previous.tier, previous.status,
                ))
        observation = EventObservation(
            observed_utc=observed_at, events=tuple(locks),
            source_healthy=True, sources_agree=True, coverage_complete=True,
            shock_locked=shock_locked, normalized=normalized,
        )
        decision = evaluate_event_guard(observation)
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            for event in events:
                self.conn.execute(
                    """INSERT INTO event_schedule_ledger VALUES(?,?,?,?)
                    ON CONFLICT(event_id) DO UPDATE SET
                    scheduled_utc=excluded.scheduled_utc, tier=excluded.tier,
                    status=excluded.status""",
                    (
                        event.event_id, event.scheduled_utc.astimezone(UTC).isoformat(),
                        event.tier, event.status,
                    ),
                )
            self.conn.execute(
                "UPDATE event_guard_control SET last_utc=? WHERE id=1",
                (observed_at.astimezone(UTC).isoformat(),),
            )
            self.conn.execute("COMMIT")
        except Exception:
            if self.conn.in_transaction:
                self.conn.execute("ROLLBACK")
            raise
        if not admission.admitted or not decision.entry_allowed:
            return CalendarCycle(
                "NO_TRADE", tuple(admission.reasons) + decision.reasons,
                decision.blocking_event_ids,
            )
        return CalendarCycle("EVENT_CLEAR", (), ())
