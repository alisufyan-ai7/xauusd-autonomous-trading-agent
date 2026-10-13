"""Immutable health records suitable for durable audit serialization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class HealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    component: str
    status: HealthStatus
    observed_at: datetime
    code: str
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.component.strip() or not self.code.strip():
            raise ValueError("component and code must be non-empty")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        object.__setattr__(self, "observed_at", self.observed_at.astimezone(UTC))


@dataclass(frozen=True, slots=True)
class HealthRecord:
    status: HealthStatus
    observed_at: datetime
    components: tuple[ComponentHealth, ...]
    execution_enabled: bool = False
    broker_action_count: int = 0

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        object.__setattr__(self, "observed_at", self.observed_at.astimezone(UTC))
        if self.execution_enabled:
            raise ValueError("production-candidate health cannot report execution enabled")
        if self.broker_action_count != 0:
            raise ValueError("production-candidate broker action count must remain zero")


def aggregate_health(
    components: tuple[ComponentHealth, ...], *, observed_at: datetime
) -> HealthRecord:
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")
    if not components:
        status = HealthStatus.UNHEALTHY
    else:
        rank = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.DEGRADED: 1,
            HealthStatus.UNHEALTHY: 2,
            HealthStatus.QUARANTINED: 3,
        }
        status = max((item.status for item in components), key=rank.__getitem__)
    return HealthRecord(status, observed_at, components)
