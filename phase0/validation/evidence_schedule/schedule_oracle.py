"""Deterministic schedule builder for read-only Gate 0 evidence captures.

The oracle creates plans only. It has no clock scheduler, network, MT5, process,
message, filesystem-write or trading capability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta, timezone
import hashlib
import json
from typing import Iterable


EVENT_SOURCES = ("BLS_ICS", "BEA_JSON", "FED_CALENDAR", "DOL_UI")
EVENT_ROUTINE_HOURS_UTC = (0, 6, 12, 18)
SESSION_SOURCES = (
    "https://get.exness.help/hc/en-us/articles/4405235684498-Instrument-trading-hours",
    "https://get.exness.help/hc/en-us/articles/17923046759836-Holiday-trading-hours",
)
ALLOWED_CAPABILITIES = {"READ_ONLY_HTTPS_GET", "READ_ONLY_MT5_OBSERVATION"}


@dataclass(frozen=True)
class ScheduledEvent:
    event_id: str
    source: str
    release_utc: datetime


@dataclass(frozen=True)
class SessionBoundary:
    boundary_id: str
    close_utc: datetime
    reopen_utc: datetime
    holiday: bool


@dataclass(frozen=True)
class CaptureTask:
    task_id: str
    due_utc: datetime
    evidence_class: str
    target: str
    phase: str
    capability: str
    external_python_trading_disabled: bool
    deliberate_disruption: bool
    sends_message: bool
    trading_action: bool


@dataclass(frozen=True)
class ScheduleResult:
    status: str
    reason_codes: tuple[str, ...]
    tasks: tuple[CaptureTask, ...]
    schedule_sha256: str | None


def _aware_utc(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() == timedelta(0)


def schedule_hash(tasks: Iterable[CaptureTask]) -> str:
    values = []
    for task in tasks:
        value = asdict(task)
        value["due_utc"] = task.due_utc.isoformat().replace("+00:00", "Z")
        values.append(value)
    body = json.dumps(values, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _task(
    task_id: str, due: datetime, evidence_class: str, target: str, phase: str,
    capability: str = "READ_ONLY_HTTPS_GET",
) -> CaptureTask:
    return CaptureTask(task_id, due, evidence_class, target, phase, capability,
                       True, False, False, False)


def build_schedule(
    start_utc: datetime,
    end_utc: datetime,
    events: tuple[ScheduledEvent, ...],
    boundaries: tuple[SessionBoundary, ...],
) -> ScheduleResult:
    reasons: list[str] = []
    if not _aware_utc(start_utc) or not _aware_utc(end_utc) or start_utc >= end_utc:
        return ScheduleResult("FAIL_CLOSED", ("HORIZON_INVALID",), (), None)
    tasks: list[CaptureTask] = []

    # Four routine reads per day retain adjacent before/after bodies for natural
    # revisions and failures. This never creates a deliberate outage.
    day = start_utc.date()
    while datetime.combine(day, time.min, timezone.utc) < end_utc:
        for hour in EVENT_ROUTINE_HOURS_UTC:
            due = datetime.combine(day, time(hour), timezone.utc) + timedelta(minutes=15)
            if start_utc <= due < end_utc:
                for source in EVENT_SOURCES:
                    tasks.append(_task(
                        f"EG-ROUTINE-{source}-{due:%Y%m%dT%H%MZ}", due,
                        "EVENT_GUARD_TRANSITION", source, "ROUTINE_PAIRABLE",
                    ))
        # Daily official broker-page refresh provides a six-day safety margin
        # against the verifier's seven-day maximum age.
        due = datetime.combine(day, time(1), timezone.utc)
        if start_utc <= due < end_utc:
            for index, source in enumerate(SESSION_SOURCES):
                tasks.append(_task(
                    f"SESSION-SOURCE-{index}-{due:%Y%m%dT%H%MZ}", due,
                    "SESSION_SOURCE_REFRESH", source, "DAILY_REFRESH",
                ))
        day += timedelta(days=1)

    event_offsets = (
        (timedelta(hours=-24), "T_MINUS_24H"),
        (timedelta(hours=-6), "T_MINUS_6H"),
        (timedelta(hours=-1), "T_MINUS_1H"),
        (timedelta(minutes=15), "T_PLUS_15M"),
        (timedelta(hours=2), "T_PLUS_2H"),
    )
    seen_event_ids: set[str] = set()
    for event in events:
        if (not event.event_id or event.event_id in seen_event_ids
                or event.source not in EVENT_SOURCES or not _aware_utc(event.release_utc)):
            reasons.append("EVENT_INVALID")
            continue
        seen_event_ids.add(event.event_id)
        for offset, phase in event_offsets:
            due = event.release_utc + offset
            if start_utc <= due < end_utc:
                tasks.append(_task(
                    f"EG-EVENT-{event.event_id}-{phase}", due,
                    "EVENT_GUARD_TRANSITION", event.source, phase,
                ))

    boundary_ids: set[str] = set()
    for boundary in boundaries:
        if (not boundary.boundary_id or boundary.boundary_id in boundary_ids
                or not _aware_utc(boundary.close_utc) or not _aware_utc(boundary.reopen_utc)
                or boundary.close_utc >= boundary.reopen_utc):
            reasons.append("BOUNDARY_INVALID")
            continue
        boundary_ids.add(boundary.boundary_id)
        source_offsets = [timedelta(days=-14), timedelta(days=-7), timedelta(days=-1),
                          timedelta(hours=-1)] if boundary.holiday else [timedelta(days=-1),
                                                                        timedelta(hours=-1)]
        for index, offset in enumerate(source_offsets):
            due = boundary.close_utc + offset
            if start_utc <= due < end_utc:
                for source_index, source in enumerate(SESSION_SOURCES):
                    tasks.append(_task(
                        f"SESSION-PRE-{boundary.boundary_id}-{index}-{source_index}", due,
                        "SESSION_SOURCE_REFRESH", source, "PRE_BOUNDARY",
                    ))
        midpoint = boundary.close_utc + (boundary.reopen_utc - boundary.close_utc) / 2
        checkpoints = (
            (boundary.close_utc - timedelta(minutes=5), "BEFORE"),
            (midpoint, "INSIDE"),
            (boundary.reopen_utc + timedelta(minutes=5), "AFTER"),
        )
        for due, phase in checkpoints:
            if start_utc <= due < end_utc:
                tasks.append(_task(
                    f"SESSION-MT5-{boundary.boundary_id}-{phase}", due,
                    "SESSION_BOUNDARY_OBSERVATION", "XAUUSD", phase,
                    "READ_ONLY_MT5_OBSERVATION",
                ))

    tasks.sort(key=lambda item: (item.due_utc, item.task_id))
    ids = [task.task_id for task in tasks]
    if len(ids) != len(set(ids)):
        reasons.append("TASK_ID_COLLISION")
    if any(task.capability not in ALLOWED_CAPABILITIES
           or task.external_python_trading_disabled is not True
           or task.deliberate_disruption or task.sends_message or task.trading_action
           for task in tasks):
        reasons.append("CAPABILITY_BOUNDARY_VIOLATION")
    unique = tuple(dict.fromkeys(reasons))
    return ScheduleResult("PLANNED_READ_ONLY" if not unique else "FAIL_CLOSED", unique,
                          tuple(tasks), schedule_hash(tasks) if not unique else None)


def verify_transition_coverage(
    tasks: tuple[CaptureTask, ...], *, expected_boundary_ids: tuple[str, ...] = (),
    expected_event_ids: tuple[str, ...] = (),
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    task_ids = [task.task_id for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        reasons.append("DUPLICATE_CAPTURE_TASK")
    routine = [task for task in tasks if task.phase == "ROUTINE_PAIRABLE"]
    for source in EVENT_SOURCES:
        source_tasks = [task for task in routine if task.target == source]
        if len(source_tasks) < 2:
            reasons.append(f"{source}_NO_ADJACENT_TRANSITION_PAIR")
        if any(right.due_utc - left.due_utc > timedelta(hours=6)
               for left, right in zip(source_tasks, source_tasks[1:])):
            reasons.append(f"{source}_ROUTINE_GAP_EXCEEDS_6H")
    boundary_groups: dict[str, set[str]] = {}
    for task in tasks:
        if task.task_id.startswith("SESSION-MT5-"):
            boundary = task.task_id.removeprefix("SESSION-MT5-").rsplit("-", 1)[0]
            boundary_groups.setdefault(boundary, set()).add(task.phase)
    if any(phases != {"BEFORE", "INSIDE", "AFTER"}
           for phases in boundary_groups.values()):
        reasons.append("SESSION_BOUNDARY_PHASE_INCOMPLETE")
    for boundary_id in expected_boundary_ids:
        if boundary_groups.get(boundary_id) != {"BEFORE", "INSIDE", "AFTER"}:
            reasons.append(f"{boundary_id}_EXPECTED_BOUNDARY_INCOMPLETE")

    dense_phases = {"T_MINUS_24H", "T_MINUS_6H", "T_MINUS_1H", "T_PLUS_15M", "T_PLUS_2H"}
    event_groups: dict[str, set[str]] = {}
    for task in tasks:
        if task.task_id.startswith("EG-EVENT-") and task.phase in dense_phases:
            suffix = f"-{task.phase}"
            if task.task_id.endswith(suffix):
                event_id = task.task_id.removeprefix("EG-EVENT-")[:-len(suffix)]
                event_groups.setdefault(event_id, set()).add(task.phase)
    for event_id in expected_event_ids:
        if event_groups.get(event_id) != dense_phases:
            reasons.append(f"{event_id}_EXPECTED_EVENT_INCOMPLETE")
    return not reasons, tuple(reasons)
