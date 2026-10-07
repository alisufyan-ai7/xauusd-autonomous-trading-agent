"""Immutable, broker-neutral XAUUSD market observations.

These objects are data only.  They deliberately expose no broker connection,
terminal mutation, or order operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum


class Timeframe(StrEnum):
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"

    @property
    def duration(self) -> timedelta:
        return {
            Timeframe.M15: timedelta(minutes=15),
            Timeframe.H1: timedelta(hours=1),
            Timeframe.H4: timedelta(hours=4),
        }[self]


def _require_utc(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field} must be timezone-aware UTC")


@dataclass(frozen=True, slots=True)
class Quote:
    symbol: str
    broker_time: datetime
    received_time: datetime
    bid: Decimal
    ask: Decimal
    tick_size: Decimal
    sequence: int

    def __post_init__(self) -> None:
        _require_utc(self.broker_time, "broker_time")
        _require_utc(self.received_time, "received_time")
        if self.symbol != "XAUUSD":
            raise ValueError("quote must be XAUUSD")
        if self.bid <= 0 or self.ask <= 0 or self.ask < self.bid:
            raise ValueError("quote prices are incoherent")
        if self.tick_size <= 0:
            raise ValueError("tick_size must be positive")
        if self.bid % self.tick_size != 0 or self.ask % self.tick_size != 0:
            raise ValueError("quote prices are not aligned to tick_size")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid

    @property
    def midpoint(self) -> Decimal:
        return (self.ask + self.bid) / Decimal(2)


@dataclass(frozen=True, slots=True)
class Bar:
    symbol: str
    timeframe: Timeframe
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    tick_volume: int

    def __post_init__(self) -> None:
        _require_utc(self.open_time, "open_time")
        if self.symbol != "XAUUSD":
            raise ValueError("bar must be XAUUSD")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("bar prices must be positive")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("OHLC identity is invalid")
        if self.high < self.low:
            raise ValueError("high is below low")
        if self.tick_volume < 0:
            raise ValueError("tick_volume must be non-negative")

    @property
    def close_time(self) -> datetime:
        return self.open_time + self.timeframe.duration

    def is_completed_at(self, decision_time: datetime) -> bool:
        _require_utc(decision_time, "decision_time")
        return self.close_time <= decision_time


UTC_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
