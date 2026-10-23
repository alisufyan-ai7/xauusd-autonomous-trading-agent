# ruff: noqa: I001
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from xauusd_agent.features.v2_market_context import ContextBar, ContextTimeframe
from xauusd_agent.features.v2_tpb_stop_plan import compile_tpb_zone_a_stop
from xauusd_agent.features.v2_tpb_zone_tracker import (
    TPBZone, ZoneState, next_tpb_zone,
)

BASE = datetime(2026, 10, 23, 12, tzinfo=UTC)
FP = "9" * 64


def bar(idx, o, h, low, c):
    return ContextBar(
        ContextTimeframe.M15, BASE + timedelta(minutes=15 * idx),
        D(str(o)), D(str(h)), D(str(low)), D(str(c)), 200,
    )


def ready(direction="LONG"):
    if direction == "LONG":
        z = TPBZone("A", "LONG", D("2900"), D("3100"), D("10"), D("0.01"), True)
        candles = [
            bar(0, 3010, 3020, 3008, 3011),
            bar(1, 3006, 3025, 2985, 3020),
            bar(2, 3020, 3030, 3019, 3027),
        ]
    else:
        z = TPBZone("A", "SHORT", D("3100"), D("2900"), D("10"), D("0.01"), True)
        candles = [
            bar(0, 2990, 2995, 2985, 2990),
            bar(1, 2990, 3010, 2976, 2980),
            bar(2, 2980, 2980, 2970, 2971),
        ]
    for idx, c in enumerate(candles):
        z = next_tpb_zone(
            z, completed_m15=c, ordinal=idx, h1_origin_breached=False,
            regime_eligible=True, broker_session_healthy=True,
            official_event_clear=True, broker_spread_and_cost_clear=True,
            same_impulse_prior_zone_exposure=False,
        )
    assert z.state is ZoneState.PENDING_EXPIRES
    return z, candles


@pytest.mark.parametrize("direction,side", [("LONG", "BUY"), ("SHORT", "SELL")])
def test_one_objective_stop_side_sl_tp_from_confirmed_zone(direction, side):
    zone, candles = ready(direction)
    now = candles[-1].close_time + timedelta(seconds=10)
    proposal = compile_tpb_zone_a_stop(
        zone=zone, rejection=candles[1], confirmation=candles[2],
        confirmation_ordinal=2, observed_utc=now,
        account_fingerprint=FP, risk_and_spread_price_buffer=D("0.1"),
    )
    assert proposal is not None
    assert proposal.side == side
    assert proposal.execution_permitted is False
    assert len(proposal.setup_key) == 64
    if side == "BUY":
        assert proposal.protective_stop < proposal.entry_stop < proposal.take_profit
    else:
        assert proposal.take_profit < proposal.entry_stop < proposal.protective_stop
    assert proposal.expires_utc == candles[2].close_time + timedelta(minutes=60)


@pytest.mark.parametrize("change", [
    "cost", "unknown_fp", "zone_b", "not_pending", "expired",
    "missing_touch", "no_rejection", "wrong_ordinal", "future_bar",
    "wrong_rejection", "confirmation_early", "replay_future",
])
def test_frozen_proposal_rejects_ambiguous_causality(change):
    z, bars = ready()
    now = bars[-1].close_time + timedelta(seconds=10)
    kw = dict(zone=z, rejection=bars[1], confirmation=bars[2],
              confirmation_ordinal=2, observed_utc=now,
              account_fingerprint=FP, risk_and_spread_price_buffer=D("0.1"))
    if change == "cost":
        kw["risk_and_spread_price_buffer"] = D("1000")
    elif change == "unknown_fp":
        kw["account_fingerprint"] = "unverified"
    elif change == "zone_b":
        kw["zone"] = replace(z, name="B")
    elif change == "not_pending":
        kw["zone"] = replace(z, state=ZoneState.WAIT_CONFIRMATION)
    elif change == "expired":
        kw["observed_utc"] += timedelta(minutes=1)
    elif change == "missing_touch":
        kw["zone"] = replace(z, touched_at_bar=None)
    elif change == "no_rejection":
        kw["zone"] = replace(z, rejection_at_bar=None)
    elif change == "wrong_ordinal":
        kw["confirmation_ordinal"] = 3
    elif change == "future_bar":
        kw["observed_utc"] -= timedelta(minutes=15)
    elif change == "wrong_rejection":
        kw["rejection"] = bars[0]
    elif change == "confirmation_early":
        kw["zone"] = replace(z, rejection_at_bar=2)
    else:
        kw["zone"] = replace(z, touched_at_bar=2)
    assert compile_tpb_zone_a_stop(**kw) is None


def test_setup_key_is_deterministic_and_changes_when_account_changes():
    z, bars = ready()
    kw = dict(
        zone=z, rejection=bars[1], confirmation=bars[2],
        confirmation_ordinal=2,
        observed_utc=bars[-1].close_time + timedelta(seconds=10),
        account_fingerprint=FP, risk_and_spread_price_buffer=D("0.1"),
    )
    first = compile_tpb_zone_a_stop(**kw)
    second = compile_tpb_zone_a_stop(**kw)
    other = compile_tpb_zone_a_stop(**(kw | {"account_fingerprint": "e" * 64}))
    assert first is not None and second is not None and other is not None
    assert first.setup_key == second.setup_key
    assert first.setup_key != other.setup_key
