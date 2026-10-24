"""Frozen admission envelope for bounded Exness demo execution."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

MAX_VOLUME_LOTS = Decimal("0.01")
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")


class DemoSafetyError(RuntimeError):
    """Raised whenever the demo-only safety envelope cannot be proven."""


class DemoSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True, slots=True)
class DemoIdentity:
    broker: str
    server: str
    account_id_sha256: str
    currency: str

    def validate(self) -> None:
        if not self.broker.strip():
            raise DemoSafetyError("demo broker identity is empty")
        if not self.server.strip():
            raise DemoSafetyError("demo server identity is empty")
        if not _HEX_64.fullmatch(self.account_id_sha256):
            raise DemoSafetyError("demo account fingerprint must be lowercase SHA-256")
        if not self.currency.strip():
            raise DemoSafetyError("demo account currency is empty")


@dataclass(frozen=True, slots=True)
class DemoPolicy:
    max_daily_submissions: int
    risk_calibration_sha256: str | None = None
    max_deviation_points: int = 20

    def validate(self) -> None:
        if self.max_daily_submissions < 1 or self.max_daily_submissions > 20:
            raise DemoSafetyError("max_daily_submissions must be within 1..20")
        if (
            self.risk_calibration_sha256 is not None
            and _HEX_64.fullmatch(self.risk_calibration_sha256) is None
        ):
            raise DemoSafetyError("risk_calibration_sha256 must be lowercase SHA-256")
        if self.max_deviation_points < 0 or self.max_deviation_points > 100:
            raise DemoSafetyError("max_deviation_points must be within 0..100")


@dataclass(frozen=True, slots=True)
class DemoActivationPermit:
    activation_id: str
    account_id_sha256: str
    server: str
    max_daily_submissions: int
    not_before_utc: datetime
    expires_utc: datetime

    def validate(self, *, now: datetime) -> None:
        if not self.activation_id.strip() or len(self.activation_id) > 128:
            raise DemoSafetyError("activation_id must contain 1..128 characters")
        if _HEX_64.fullmatch(self.account_id_sha256) is None:
            raise DemoSafetyError("activation account fingerprint must be lowercase SHA-256")
        if not self.server.strip():
            raise DemoSafetyError("activation server is empty")
        if self.max_daily_submissions < 1 or self.max_daily_submissions > 20:
            raise DemoSafetyError("activation daily submission budget must be within 1..20")
        for label, value in (
            ("not_before_utc", self.not_before_utc),
            ("expires_utc", self.expires_utc),
            ("now", now),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise DemoSafetyError(f"{label} must be timezone-aware")
        start = self.not_before_utc.astimezone(UTC)
        end = self.expires_utc.astimezone(UTC)
        observed = now.astimezone(UTC)
        if end <= start:
            raise DemoSafetyError("activation expiry must be after activation start")
        if observed < start or observed >= end:
            raise DemoSafetyError("demo activation permit is not currently valid")


@dataclass(frozen=True, slots=True)
class DemoOrderRequest:
    request_id: str
    symbol: str
    side: DemoSide
    volume_lots: Decimal
    stop_loss: Decimal
    # STOP-only TPB fields; all existing S2 Policy A submission denial remains.
    entry_stop: Decimal | None = None
    take_profit: Decimal | None = None
    expires_utc: datetime | None = None

    @property
    def is_tpb_stop(self) -> bool:
        return self.entry_stop is not None

    def validate(self) -> None:
        try:
            uuid.UUID(self.request_id)
        except (TypeError, ValueError, AttributeError) as exc:
            raise DemoSafetyError("request_id must be a UUID") from exc
        if self.symbol != "XAUUSD":
            raise DemoSafetyError("demo adapter is bound to XAUUSD")
        if not isinstance(self.side, DemoSide):
            raise DemoSafetyError("unsupported demo order side")
        if not isinstance(self.volume_lots, Decimal) or not self.volume_lots.is_finite():
            raise DemoSafetyError("volume_lots must be a finite Decimal")
        if self.volume_lots <= 0 or self.volume_lots > MAX_VOLUME_LOTS:
            raise DemoSafetyError("demo volume must be >0 and <=0.01 lot")
        if not isinstance(self.stop_loss, Decimal) or not self.stop_loss.is_finite():
            raise DemoSafetyError("protective stop must be a finite Decimal")
        if self.stop_loss <= 0:
            raise DemoSafetyError("protective stop is required")
        levels = (self.entry_stop, self.take_profit, self.expires_utc)
        if any(x is not None for x in levels):
            if any(x is None for x in levels):
                raise DemoSafetyError("TPB STOP requires entry, TP and expiry")
            assert self.entry_stop is not None
            assert self.take_profit is not None
            assert self.expires_utc is not None
            if (
                type(self.entry_stop) is not Decimal
                or type(self.take_profit) is not Decimal
                or not self.entry_stop.is_finite()
                or not self.take_profit.is_finite()
                or self.entry_stop <= 0 or self.take_profit <= 0
                or self.expires_utc.tzinfo is None
                or self.expires_utc.utcoffset() != timedelta(0)
            ):
                raise DemoSafetyError("incomplete TPB STOP prices or UTC expiry")
            if (
                (self.side is DemoSide.BUY and not (
                    self.stop_loss < self.entry_stop < self.take_profit
                ))
                or (self.side is DemoSide.SELL and not (
                    self.take_profit < self.entry_stop < self.stop_loss
                ))
            ):
                raise DemoSafetyError("TPB STOP levels not ordered safely")

