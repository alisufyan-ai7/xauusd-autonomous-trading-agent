"""Pure supervisor state machine.

It emits requested actions only.  Process and service mutation belongs to a
separately authorized host adapter and is absent from this production candidate.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class SupervisorState(StrEnum):
    STARTING = "STARTING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    RESTART_REQUESTED = "RESTART_REQUESTED"
    QUARANTINED = "QUARANTINED"


class SupervisorAction(StrEnum):
    NONE = "NONE"
    REQUEST_RESTART = "REQUEST_RESTART"
    ENTER_QUARANTINE = "ENTER_QUARANTINE"


@dataclass(frozen=True, slots=True)
class SupervisorConfig:
    heartbeat_timeout: timedelta = timedelta(seconds=30)
    degraded_grace: timedelta = timedelta(seconds=60)
    restart_window: timedelta = timedelta(minutes=15)
    max_restart_requests: int = 2

    def __post_init__(self) -> None:
        if min(self.heartbeat_timeout, self.degraded_grace, self.restart_window) <= timedelta(0):
            raise ValueError("supervisor durations must be positive")
        if self.max_restart_requests < 0:
            raise ValueError("max_restart_requests cannot be negative")


@dataclass(frozen=True, slots=True)
class SupervisorDecision:
    state: SupervisorState
    action: SupervisorAction
    code: str


class WatchdogSupervisor:
    def __init__(self, config: SupervisorConfig | None = None) -> None:
        self.config = config or SupervisorConfig()
        self.state = SupervisorState.STARTING
        self._degraded_since: datetime | None = None
        self._restart_requests: deque[datetime] = deque()

    def observe(
        self, *, now: datetime, last_heartbeat: datetime | None, fatal: bool = False
    ) -> SupervisorDecision:
        now = self._utc(now)
        if self.state is SupervisorState.QUARANTINED:
            return SupervisorDecision(self.state, SupervisorAction.NONE, "QUARANTINE_LATCHED")
        if fatal:
            return self._quarantine("FATAL_HEALTH_ASSERTION")
        heartbeat = self._utc(last_heartbeat) if last_heartbeat is not None else None
        if heartbeat is not None and heartbeat > now:
            return self._quarantine("HEARTBEAT_FROM_FUTURE")
        fresh = heartbeat is not None and now - heartbeat <= self.config.heartbeat_timeout
        if fresh:
            self.state = SupervisorState.HEALTHY
            self._degraded_since = None
            return SupervisorDecision(self.state, SupervisorAction.NONE, "HEARTBEAT_FRESH")
        if self._degraded_since is None:
            self._degraded_since = now
            self.state = SupervisorState.DEGRADED
            return SupervisorDecision(self.state, SupervisorAction.NONE, "HEARTBEAT_STALE_GRACE")
        if now - self._degraded_since < self.config.degraded_grace:
            return SupervisorDecision(self.state, SupervisorAction.NONE, "HEARTBEAT_STALE_GRACE")
        cutoff = now - self.config.restart_window
        while self._restart_requests and self._restart_requests[0] < cutoff:
            self._restart_requests.popleft()
        if len(self._restart_requests) >= self.config.max_restart_requests:
            return self._quarantine("RESTART_BUDGET_EXHAUSTED")
        self._restart_requests.append(now)
        self._degraded_since = now
        self.state = SupervisorState.RESTART_REQUESTED
        return SupervisorDecision(self.state, SupervisorAction.REQUEST_RESTART, "HEARTBEAT_STALE")

    def acknowledge_restart(self, *, recovered: bool) -> SupervisorDecision:
        if self.state is SupervisorState.QUARANTINED:
            return SupervisorDecision(self.state, SupervisorAction.NONE, "QUARANTINE_LATCHED")
        if recovered:
            self.state = SupervisorState.STARTING
            self._degraded_since = None
            return SupervisorDecision(
                self.state, SupervisorAction.NONE, "RECOVERY_AWAITING_HEARTBEAT"
            )
        return self._quarantine("RESTART_DID_NOT_RECOVER")

    def _quarantine(self, code: str) -> SupervisorDecision:
        self.state = SupervisorState.QUARANTINED
        return SupervisorDecision(self.state, SupervisorAction.ENTER_QUARANTINE, code)

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("supervisor timestamps must be timezone-aware")
        return value.astimezone(UTC)
