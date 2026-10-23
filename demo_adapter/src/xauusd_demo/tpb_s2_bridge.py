"""Pure TPB STOP candidate -> existing S2 DEMO request translation.

No MT5 order APIs. The objective TPB strategy makes the choice of BUY/SELL,
SL, TP; the separately risk-bound S2 adapter must eventually qualify broker
submission. Reuse one order sender instead of creating a competing sender.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from xauusd_agent.features.v2_tpb_stop_plan import TPBStopPlan

from .continuous_coordinator import VerifiedProposal
from .envelope import DemoOrderRequest, DemoSafetyError, DemoSide


@dataclass(frozen=True, slots=True)
class BoundedTPBSubmission:
    proposal: VerifiedProposal
    pending_stop_request: DemoOrderRequest
    broker_execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.broker_execution_permitted:
            raise ValueError("TPB S2 translation is not an order permit")


def translate_tpb_into_existing_s2(
    plan: TPBStopPlan, *, now: datetime
) -> BoundedTPBSubmission:
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise DemoSafetyError("TPB translation requires exact UTC")
    if (
        plan.execution_permitted or plan.side not in ("BUY", "SELL")
        or len(plan.setup_key) != 64
        or any(c not in "0123456789abcdef" for c in plan.setup_key)
        or now < plan.confirmed_bar_utc
        or now >= plan.proposal_expires_utc
        or plan.proposal_expires_utc - plan.confirmed_bar_utc > timedelta(seconds=30)
        or plan.expires_utc - plan.confirmed_bar_utc > timedelta(minutes=60)
    ):
        raise DemoSafetyError("TPB STOP plan stale or not source-confirmed")
    side = DemoSide(plan.side)
    req = DemoOrderRequest(
        request_id=str(uuid.UUID(plan.setup_key[:32])),
        symbol="XAUUSD", side=side, volume_lots=Decimal("0.01"),
        stop_loss=plan.protective_stop, entry_stop=plan.entry_stop,
        take_profit=plan.take_profit, expires_utc=plan.expires_utc,
    )
    req.validate()
    verified = VerifiedProposal(
        setup_key=plan.setup_key, symbol="XAUUSD", side=plan.side,
        confirmed_bar_utc=plan.confirmed_bar_utc,
        expires_utc=plan.proposal_expires_utc,
    )
    verified.validate(now)
    return BoundedTPBSubmission(verified, req)
