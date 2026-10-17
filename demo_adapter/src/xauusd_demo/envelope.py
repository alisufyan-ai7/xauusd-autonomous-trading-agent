"""Frozen admission envelope for bounded Exness demo execution."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
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
    max_deviation_points: int = 20

    def validate(self) -> None:
        if self.max_daily_submissions < 1 or self.max_daily_submissions > 20:
            raise DemoSafetyError("max_daily_submissions must be within 1..20")
        if self.max_deviation_points < 0 or self.max_deviation_points > 100:
            raise DemoSafetyError("max_deviation_points must be within 0..100")


@dataclass(frozen=True, slots=True)
class DemoOrderRequest:
    request_id: str
    symbol: str
    side: DemoSide
    volume_lots: Decimal
    stop_loss: Decimal

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
