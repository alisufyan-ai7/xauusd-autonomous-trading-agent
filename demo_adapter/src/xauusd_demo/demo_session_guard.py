"""Documented, bounded experimental Exness DEMO session/news proxy.

NOT an authenticated BLS/BEA/Fed/Census economic-calendar replacement.
Only for the restricted, virtual-money, 0.01-lot research pilot. It
deliberately avoids the usual US 08:30, 10:00 and 14:00 ET release windows
by allowing new orders only during a narrow NY late-morning overlap.
Unscheduled economic shocks remain possible: this policy must NEVER be
used as a LIVE or officially authenticated Event Guard admission.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from .envelope import DemoSafetyError

_NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class ExperimentalDemoWindow:
    allowed: bool
    reason: str
    officially_verified: bool = False
    live_permission: bool = False

    def __post_init__(self) -> None:
        if self.officially_verified or self.live_permission:
            raise DemoSafetyError("heuristic DEMO session is NOT official/LIVE admission")


def assess_experimental_demo_window(
    *, now: datetime, pending_expires_utc: datetime,
) -> ExperimentalDemoWindow:
    if any(x.tzinfo is None or x.utcoffset() != timedelta(0) for x in (
        now, pending_expires_utc,
    )):
        raise DemoSafetyError("DEMO session clock not UTC")
    if not now < pending_expires_utc <= now + timedelta(minutes=60):
        return ExperimentalDemoWindow(False, "PENDING_LIFETIME_NOT_ADMITTED")
    local = now.astimezone(_NEW_YORK)
    expiry = pending_expires_utc.astimezone(_NEW_YORK)
    if (
        local.weekday() >= 5 or expiry.weekday() >= 5
        or local.date() != expiry.date()
    ):
        return ExperimentalDemoWindow(False, "WEEKEND_OR_CROSS_DATE")
    # Do not create entries during major common US release hours. This
    # deliberately skips 8:30, 10:00 and 14:00 ET. The final pending order
    # must expire before 12:45 ET. This is a coarse *demo-only* proxy and
    # does not assert the absence of unusual/scheduled events.
    if not (time(10, 45) <= local.time() <= time(11, 30)):
        return ExperimentalDemoWindow(False, "OUTSIDE_RESTRICTED_NY_OVERLAP")
    if not (local.time() < expiry.time() <= time(12, 45)):
        return ExperimentalDemoWindow(False, "PENDING_EXPIRES_OUTSIDE_SAFE_PROXY")
    return ExperimentalDemoWindow(True, "EXPERIMENTAL_DEMO_TIME_PROXY_ONLY")
