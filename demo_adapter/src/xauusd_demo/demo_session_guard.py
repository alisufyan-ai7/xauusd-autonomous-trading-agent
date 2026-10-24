"""Experimental DEMO entry may occur at ANY real broker-tradable hour.

The old 10:45–11:30 New York whitelist was an agent-added, artificial
limitation. This module checks only quote/setup-time validity. The independent
MT5 source and sender MUST verify live tick freshness, trade mode, identity,
price grid, margin and stops before submission. Closed market => NO_TRADE.
Not an economic-news calendar: this is a DEMO-only policy, never LIVE.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .envelope import DemoSafetyError


@dataclass(frozen=True, slots=True)
class ExperimentalDemoWindow:
    allowed: bool
    reason: str
    officially_verified: bool = False
    live_permission: bool = False

    def __post_init__(self) -> None:
        if self.officially_verified or self.live_permission:
            raise DemoSafetyError("broker-quote session is not official LIVE calendar")


def assess_experimental_demo_window(
    *, now: datetime, pending_expires_utc: datetime,
) -> ExperimentalDemoWindow:
    if any(x.tzinfo is None or x.utcoffset() != timedelta(0) for x in (
        now, pending_expires_utc,
    )):
        raise DemoSafetyError("DEMO session clock must be UTC")
    # An unfilled STOP setup expires when stale. This is NOT a window in
    # which the service is allowed to seek NEW trades.
    if not now < pending_expires_utc <= now + timedelta(minutes=60):
        return ExperimentalDemoWindow(False, "PENDING_STOP_EXPIRED_OR_TOO_DISTANT")
    return ExperimentalDemoWindow(True, "ANY_FRESH_BROKER_SESSION_DEMO_ONLY")
