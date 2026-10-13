"""UTC wall-clock plus monotonic process-time observations."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from .errors import ValidationError


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


def format_utc(value: datetime) -> str:
    return ensure_utc(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValidationError("UTC timestamp must end in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValidationError("invalid UTC timestamp") from exc
    return ensure_utc(parsed)


@dataclass(frozen=True, slots=True)
class TimeObservation:
    utc: datetime
    monotonic_ns: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "utc", ensure_utc(self.utc))
        if (
            isinstance(self.monotonic_ns, bool)
            or not isinstance(self.monotonic_ns, int)
            or self.monotonic_ns < 0
        ):
            raise ValidationError("monotonic_ns must be a non-negative integer")

    @property
    def utc_text(self) -> str:
        return format_utc(self.utc)


class Clock(Protocol):
    def observe(self) -> TimeObservation: ...


class SystemClock:
    def observe(self) -> TimeObservation:
        return TimeObservation(datetime.now(UTC), time.monotonic_ns())
