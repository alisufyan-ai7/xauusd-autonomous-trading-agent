from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from xauusd_agent.features.v2_market_context import ContextBar, ContextTimeframe
from xauusd_agent.features.v2_tpb_zone_tracker import (
    TPBZone,
    ZoneState,
    next_tpb_zone,
)

BASE = datetime(2026, 10, 22, 12, tzinfo=UTC)


def zone(name="A"):
    return TPBZone(
        name=name, direction="LONG", origin=Decimal("2900"),
        extreme=Decimal("3100"), atr_m15=Decimal("10"),
        tick_size=Decimal("0.001"), confluence_verified=True,
    )


def bar(idx, op, hi, lo, close):
    return ContextBar(
        timeframe=ContextTimeframe.M15,
        open_time=BASE + timedelta(minutes=15 * idx),
        open=Decimal(str(op)), high=Decimal(str(hi)),
        low=Decimal(str(lo)), close=Decimal(str(close)), tick_volume=10,
    )


def advance(state, idx, candle=None, **changes):
    common = {
        "completed_m15": candle or bar(idx, 3010, 3020, 3008, 3011),
        "ordinal": idx, "h1_origin_breached": False,
        "regime_eligible": True, "broker_session_healthy": True,
        "official_event_clear": True,
        "broker_spread_and_cost_clear": True,
        "same_impulse_prior_zone_exposure": False,
    }
    common.update(changes)
    return next_tpb_zone(state, **common)


def test_first_touch_rejection_two_bar_confirmation_never_executes():
    first = advance(zone(), 0)
    assert first.state is ZoneState.WAIT_CONFIRMATION
    rejection = advance(
        first, 1, bar(1, 3006, 3025, 2985, 3020),
    )
    assert rejection.rejection_at_bar == 1
    ready = advance(
        rejection, 2, bar(2, 3020, 3030, 3019, 3027),
    )
    assert ready.state is ZoneState.PENDING_EXPIRES
    assert ready.execution_permitted is False
    assert advance(ready, 7).state is ZoneState.CLOSED


def test_zone_b_blocked_by_a_exposure():
    result = advance(zone("B"), 1, same_impulse_prior_zone_exposure=True)
    assert result.state is ZoneState.CLOSED
    assert result.reason == "TPB_SAFETY_ORIGIN_EVENT_COST_BLOCK"


def test_unknown_event_session_or_cost_cannot_be_assumed_clear():
    for flag in ("official_event_clear", "broker_session_healthy",
                 "broker_spread_and_cost_clear", "regime_eligible"):
        result = advance(zone(), 0, **{flag: None})
        assert result.state is ZoneState.CLOSED


def test_no_reopening_after_expiry_or_invalidation():
    original = advance(zone(), 0)
    invalidated = advance(
        original, 1, bar(1, 2978, 2984, 2970, 2975)
    )
    assert invalidated.state is ZoneState.CLOSED
    assert advance(invalidated, 2).state is ZoneState.CLOSED


def test_nonconfluent_fibonacci_zone_never_accepted():
    z = replace(zone(), confluence_verified=False)
    assert advance(z, 1).state is ZoneState.CLOSED


def test_confirmation_window_expires():
    z = advance(zone(), 0)
    for idx in range(1, 10):
        z = advance(z, idx, bar(idx, 3030, 3031, 3028, 3030))
    assert z.state is ZoneState.CLOSED


def test_reject_invalid_impulse_and_never_authorize_execution():
    with pytest.raises(ValueError, match="direction"):
        replace(zone(), direction="SHORT")
    with pytest.raises(ValueError, match="nonexecuting"):
        replace(zone(), execution_permitted=True)
