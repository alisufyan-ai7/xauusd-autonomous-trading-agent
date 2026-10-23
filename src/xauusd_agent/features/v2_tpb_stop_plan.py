"""Frozen TPB Zone-A STOP-entry level compiler (execution disabled).

Only consumes a causally established TPBZone first-touch and 2-bar-confirmed
state. Converts the closed confirming bar into tick-grid STOP entry, initial
protective SL and structural TP. This pure technical contract NEVER places
orders, selects a trading account, or permits S2 to bypass Policy A.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from xauusd_agent.features.v2_market_context import ContextBar, ContextTimeframe
from xauusd_agent.features.v2_tpb_zone_tracker import TPBZone, ZoneState


@dataclass(frozen=True, slots=True)
class TPBStopPlan:
    setup_key: str
    side: str
    entry_stop: Decimal
    protective_stop: Decimal
    take_profit: Decimal
    tp1_informational: Decimal
    confirmed_bar_utc: datetime
    expires_utc: datetime
    proposal_expires_utc: datetime
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("a TPB technical plan cannot authorize execution")


def _grid(value: Decimal, tick: Decimal, *, up: bool) -> Decimal:
    return (value / tick).to_integral_value(
        rounding=ROUND_CEILING if up else ROUND_FLOOR
    ) * tick


def compile_tpb_zone_a_stop(
    *,
    zone: TPBZone,
    rejection: ContextBar,
    confirmation: ContextBar,
    confirmation_ordinal: int,
    observed_utc: datetime,
    account_fingerprint: str,
    risk_and_spread_price_buffer: Decimal,
) -> TPBStopPlan | None:
    """Return a deterministic *non-ordering* TPB Zone-A candidate or None.

    Requires prior durable zone-state tracking to prevent replaying first
    touches. Position authorization / source & cash checks remain external.
    """
    if (
        zone.name != "A" or zone.state is not ZoneState.PENDING_EXPIRES
        or zone.confluence_verified is not True
        or zone.entry_at_bar != confirmation_ordinal
        or zone.rejection_at_bar is None
        or zone.touched_at_bar is None
        or not (zone.touched_at_bar < zone.rejection_at_bar
                < zone.entry_at_bar <= zone.rejection_at_bar + 2)
        or zone.entry_at_bar > zone.touched_at_bar + 8
        or zone.rejection_extreme is None
        or rejection.timeframe is not ContextTimeframe.M15
        or confirmation.timeframe is not ContextTimeframe.M15
        or rejection.close_time > confirmation.open_time
        or observed_utc.tzinfo is None
        or observed_utc.utcoffset() != timedelta(0)
        or confirmation.close_time > observed_utc
        or observed_utc - confirmation.close_time > timedelta(seconds=30)
        or len(account_fingerprint) != 64
        or any(c not in "0123456789abcdef" for c in account_fingerprint)
        or type(risk_and_spread_price_buffer) is not Decimal
        or not risk_and_spread_price_buffer.is_finite()
        or risk_and_spread_price_buffer < 0
    ):
        return None
    tick = zone.tick_size
    lower, upper = zone.bounds
    stop_buffer = max(3 * tick, Decimal("0.10") * zone.atr_m15)
    long = zone.direction == "LONG"
    rejection_extreme = rejection.high if long else rejection.low
    if abs(rejection_extreme - zone.rejection_extreme) > tick / 2:
        return None
    if long:
        if confirmation.close < rejection.high + tick:
            return None
        entry = _grid(max(confirmation.high, confirmation.close) + tick, tick, up=True)
        stop = _grid(min(rejection.low, lower) - stop_buffer, tick, up=False)
        tp1 = _grid(zone.extreme, tick, up=False)
        final_unrounded = zone.origin + (
            zone.extreme - zone.origin
        ) * Decimal("1.272")
        target = _grid(final_unrounded, tick, up=False)
        r = entry - stop
        net_tp1 = tp1 - entry - risk_and_spread_price_buffer
        net_final = target - entry - risk_and_spread_price_buffer
        side = "BUY"
    else:
        if confirmation.close > rejection.low - tick:
            return None
        entry = _grid(min(confirmation.low, confirmation.close) - tick, tick, up=False)
        stop = _grid(max(rejection.high, upper) + stop_buffer, tick, up=True)
        tp1 = _grid(zone.extreme, tick, up=True)
        final_unrounded = zone.origin + (
            zone.extreme - zone.origin
        ) * Decimal("1.272")
        target = _grid(final_unrounded, tick, up=True)
        r = stop - entry
        net_tp1 = entry - tp1 - risk_and_spread_price_buffer
        net_final = entry - target - risk_and_spread_price_buffer
        side = "SELL"
    if (
        r <= 0 or net_tp1 < Decimal("1.5") * (r + risk_and_spread_price_buffer)
        or net_final < Decimal(2) * (r + risk_and_spread_price_buffer)
    ):
        return None
    if not (
        (long and stop < entry < target)
        or (not long and target < entry < stop)
    ):
        return None
    # Key includes the actual closed M15 trigger, impulse anchors and scope.
    payload = (
        "P0-SETUPS-001|TPB|ZoneA|"
        f"{account_fingerprint}|XAUUSD|{side}|"
        f"{zone.origin}|{zone.extreme}|{zone.touched_at_bar}|"
        f"{confirmation.open_time.astimezone(UTC).isoformat()}|"
        f"{entry}|{stop}|{target}"
    )
    key = hashlib.sha256(payload.encode("ascii")).hexdigest()
    return TPBStopPlan(
        setup_key=key, side=side, entry_stop=entry,
        protective_stop=stop, take_profit=target,
        tp1_informational=tp1,
        confirmed_bar_utc=confirmation.close_time,
        expires_utc=confirmation.close_time + timedelta(minutes=60),
        proposal_expires_utc=confirmation.close_time + timedelta(seconds=30),
    )
