"""Alert interfaces.  The default sink records intent without external delivery."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from threading import Lock
from types import MappingProxyType
from typing import Any, Protocol


class AlertSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class AlertEvent:
    event_id: str
    occurred_at: datetime
    severity: AlertSeverity
    kind: str
    message: str
    correlation_id: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("event_id", "kind", "message", "correlation_id"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must be non-empty")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        object.__setattr__(self, "occurred_at", self.occurred_at.astimezone(UTC))
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))


@dataclass(frozen=True, slots=True)
class AlertReceipt:
    event_id: str
    recorded_at: datetime
    sink: str
    delivered: bool
    status: str


class AlertSink(Protocol):
    def emit(self, event: AlertEvent) -> AlertReceipt: ...


class AuditOnlyAlertSink:
    """Thread-safe in-memory audit sink; performs no network or message action."""

    def __init__(self) -> None:
        self._events: list[AlertEvent] = []
        self._lock = Lock()

    def emit(self, event: AlertEvent) -> AlertReceipt:
        with self._lock:
            self._events.append(event)
        return AlertReceipt(
            event_id=event.event_id,
            recorded_at=datetime.now(UTC),
            sink="audit-only",
            delivered=False,
            status="RECORDED_NOT_DELIVERED",
        )

    def snapshot(self) -> tuple[AlertEvent, ...]:
        with self._lock:
            return tuple(self._events)
