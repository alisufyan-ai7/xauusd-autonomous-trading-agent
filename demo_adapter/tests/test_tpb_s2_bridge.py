# ruff: noqa: I001
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from xauusd_agent.features.v2_tpb_stop_plan import TPBStopPlan

from xauusd_demo.envelope import DemoSafetyError, DemoSide
from xauusd_demo.tpb_s2_bridge import translate_tpb_into_existing_s2

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)


def plan(side="BUY"):
    return TPBStopPlan(
        setup_key="a" * 64, side=side,
        entry_stop=D("2701") if side == "BUY" else D("2699"),
        protective_stop=D("2691") if side == "BUY" else D("2709"),
        take_profit=D("2725") if side == "BUY" else D("2675"),
        tp1_informational=D("2718") if side == "BUY" else D("2682"),
        confirmed_bar_utc=NOW,
        proposal_expires_utc=NOW + timedelta(seconds=30),
        expires_utc=NOW + timedelta(minutes=60),
    )


@pytest.mark.parametrize("side", ["BUY", "SELL"])
def test_same_objective_tpb_levels_flow_to_existing_s2_request(side):
    a = translate_tpb_into_existing_s2(
        plan(side), now=NOW + timedelta(seconds=8),
    )
    b = translate_tpb_into_existing_s2(
        plan(side), now=NOW + timedelta(seconds=8),
    )
    assert a.proposal.side == side
    assert a.pending_stop_request.side == DemoSide(side)
    assert a.pending_stop_request.entry_stop == plan(side).entry_stop
    assert a.pending_stop_request.stop_loss == plan(side).protective_stop
    assert a.pending_stop_request.take_profit == plan(side).take_profit
    assert a.pending_stop_request.expires_utc == plan(side).expires_utc
    assert a.pending_stop_request.request_id == b.pending_stop_request.request_id
    assert a.proposal.expires_utc == plan(side).proposal_expires_utc
    assert not a.broker_execution_permitted
    assert not hasattr(a, "order_send")


@pytest.mark.parametrize("bad", [
    "expired", "pending_too_long", "proposal_too_long", "wrong_side",
    "invalid_stop", "future_confirmation", "wrong_hash",
])
def test_no_order_from_invalid_or_expired_tpb_plan(bad):
    p = plan()
    when = NOW + timedelta(seconds=8)
    if bad == "expired":
        when = NOW + timedelta(seconds=31)
    elif bad == "pending_too_long":
        p = replace(p, expires_utc=NOW + timedelta(hours=2))
    elif bad == "proposal_too_long":
        p = replace(p, proposal_expires_utc=NOW + timedelta(minutes=1))
    elif bad == "wrong_side":
        p = replace(p, side="LIVE")
    elif bad == "invalid_stop":
        p = replace(p, protective_stop=D("2702"))
    elif bad == "future_confirmation":
        when = NOW - timedelta(seconds=1)
    else:
        p = replace(p, setup_key="impossible")
    with pytest.raises(DemoSafetyError):
        translate_tpb_into_existing_s2(p, now=when)
