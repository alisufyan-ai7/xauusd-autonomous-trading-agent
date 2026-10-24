"""Frozen TPB Zone A/B first-touch/confirmation research state (NO TRADING).

An explicit impulse must be sourced from completed H1/H4 features. This
state machine cannot certify the impulse, broker costs, news or an OOS edge.
Zone B never recovers the loss of Zone A; exposure blocks simultaneous zones.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum

from xauusd_agent.features.v2_market_context import ContextBar, ContextTimeframe


class ZoneState(StrEnum):
    WAIT_TOUCH = "WAIT_TOUCH"
    WAIT_CONFIRMATION = "WAIT_CONFIRMATION"
    PENDING_EXPIRES = "PENDING_EXPIRES"
    CLOSED = "CLOSED"


@dataclass(frozen=True, slots=True)
class TPBZone:
    name: str
    direction: str
    origin: Decimal
    extreme: Decimal
    atr_m15: Decimal
    tick_size: Decimal
    confluence_verified: bool
    state: ZoneState = ZoneState.WAIT_TOUCH
    touched_at_bar: int | None = None
    rejection_at_bar: int | None = None
    rejection_extreme: Decimal | None = None
    entry_at_bar: int | None = None
    reason: str = "RESEARCH_ONLY"
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if (
            self.execution_permitted
            or self.name not in {"A", "B"}
            or self.direction not in {"LONG", "SHORT"}
            or not all(v.is_finite() and v > 0 for v in (
                self.origin, self.extreme, self.atr_m15, self.tick_size,
            ))
            or self.origin == self.extreme
        ):
            raise ValueError("invalid nonexecuting TPB zone")
        if (
            (self.direction == "LONG" and self.origin >= self.extreme)
            or (self.direction == "SHORT" and self.origin <= self.extreme)
        ):
            raise ValueError("TPB impulse direction inconsistent")

    @property
    def bounds(self) -> tuple[Decimal, Decimal]:
        ratio1, ratio2 = (
            (Decimal("0.382"), Decimal("0.500"))
            if self.name == "A"
            else (Decimal("0.500"), Decimal("0.618"))
        )
        distance = self.extreme - self.origin
        a = self.extreme - distance * ratio1
        b = self.extreme - distance * ratio2
        return min(a, b), max(a, b)


def next_tpb_zone(
    zone: TPBZone,
    *,
    completed_m15: ContextBar,
    ordinal: int,
    h1_origin_breached: bool | None,
    regime_eligible: bool | None,
    broker_session_healthy: bool | None,
    official_event_clear: bool | None,
    broker_spread_and_cost_clear: bool | None,
    same_impulse_prior_zone_exposure: bool,
) -> TPBZone:
    """Advance on one completed M15 candle (external caller fences ordinals).

    First zone touch must precede a rejection; rejection then confirms within
    two M15 closes and no later than eight closes after first touch. A formed
    entry is *paper pending* and expires after four closes. No resend/reopen.
    """
    if ordinal < 0 or completed_m15.timeframe is not ContextTimeframe.M15:
        raise ValueError("one numbered completed M15 bar required")
    if zone.state is ZoneState.CLOSED:
        return zone
    if (
        not zone.confluence_verified
        or h1_origin_breached is not False
        or regime_eligible is not True
        or broker_session_healthy is not True
        or official_event_clear is not True
        or broker_spread_and_cost_clear is not True
        or (zone.name == "B" and same_impulse_prior_zone_exposure)
    ):
        return replace(zone, state=ZoneState.CLOSED, reason="TPB_SAFETY_ORIGIN_EVENT_COST_BLOCK")
    lower, upper = zone.bounds
    direction = zone.direction
    far = lower if direction == "LONG" else upper
    close = completed_m15.close
    if (
        (direction == "LONG" and close < far - zone.atr_m15 * Decimal("0.15"))
        or (direction == "SHORT" and close > far + zone.atr_m15 * Decimal("0.15"))
    ):
        return replace(zone, state=ZoneState.CLOSED, reason="TPB_ZONE_INVALIDATED")
    if zone.state is ZoneState.PENDING_EXPIRES:
        if zone.entry_at_bar is None or ordinal > zone.entry_at_bar + 4:
            return replace(zone, state=ZoneState.CLOSED, reason="TPB_ENTRY_EXPIRED")
        return zone
    bar_touch = completed_m15.low <= upper and completed_m15.high >= lower
    if zone.state is ZoneState.WAIT_TOUCH and not bar_touch:
        return zone
    touched = zone.touched_at_bar if zone.touched_at_bar is not None else ordinal
    if ordinal > touched + 8:
        return replace(zone, state=ZoneState.CLOSED, reason="TPB_CONFIRMATION_EXPIRED")
    if zone.state is ZoneState.WAIT_TOUCH:
        return replace(
            zone, state=ZoneState.WAIT_CONFIRMATION,
            touched_at_bar=touched, reason="TPB_ZONE_FIRST_TOUCH",
        )
    if zone.rejection_at_bar is None:
        rng = completed_m15.high - completed_m15.low
        body = abs(completed_m15.close - completed_m15.open)
        if rng <= 0:
            return zone
        if direction == "LONG":
            wick = min(completed_m15.close, completed_m15.open) - completed_m15.low
            close_fraction = (close - completed_m15.low) / rng
            trend_extreme = completed_m15.high
        else:
            wick = completed_m15.high - max(completed_m15.close, completed_m15.open)
            close_fraction = (completed_m15.high - close) / rng
            trend_extreme = completed_m15.low
        if (
            not bar_touch
            or wick < body
            or close_fraction < Decimal("0.65")
            or not (
                lower <= close <= upper
                or (direction == "LONG" and close > upper)
                or (direction == "SHORT" and close < lower)
            )
        ):
            return zone
        return replace(
            zone, rejection_at_bar=ordinal,
            rejection_extreme=trend_extreme, reason="TPB_REJECTION_CONFIRMED",
        )
    if ordinal > zone.rejection_at_bar + 2:
        return replace(zone, state=ZoneState.CLOSED, reason="TPB_TRIGGER_WINDOW_EXPIRED")
    extreme = zone.rejection_extreme
    assert extreme is not None
    confirmed = (
        close >= extreme + zone.tick_size if direction == "LONG"
        else close <= extreme - zone.tick_size
    )
    if not confirmed:
        return zone
    return replace(
        zone, state=ZoneState.PENDING_EXPIRES,
        entry_at_bar=ordinal, reason="TPB_SHADOW_STOP_PROPOSAL_ONLY",
    )
