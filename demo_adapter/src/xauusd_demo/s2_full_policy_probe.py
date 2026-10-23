"""Source-bound, nonexecuting Policy A review using ONE existing S2 MT5 adapter.

This deliberately sits on the S2 class rather than creating a new broker
sender. It derives the pending STOP request from S2 itself, reads the attached
MT5 account and complete history, applies a prospective durable cash journal,
screens the whole pending lifetime, then checks broker monetary arithmetic.

This is still a REVIEW, never a QualifiedDemoBrokerPort. Cost provenance and
real official source authorization remain separate gates; a mathematical PASS
is NOT a permission to call order_check, order_send or unfreeze S2's hard stop.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from xauusd_agent.guards.v2_official_source_gate import VerifiedOfficialSnapshot
from xauusd_agent.risk.full_policy_a import FullRiskDisposition

from .envelope import DemoOrderRequest, DemoSafetyError
from .full_policy_broker_receipt import (
    BoundAdverseCost,
    BrokerPolicyReceipt,
    BrokerStopProposal,
    preview_broker_full_policy_a,
)
from .mt5_cash_source import read_mt5_pro_demo_cash
from .mt5_demo import DemoMT5Adapter, _decimal
from .pending_entry_window_guard import screen_pending_entry_window
from .prospective_cash_journal import ProspectiveDemoCashJournal


@dataclass(frozen=True, slots=True)
class BoundS2PolicyReview:
    """Risk math and broker input concordance, with irrevocable no-send scope."""
    request_id: str
    broker_order_type: int
    broker_entry: Decimal
    broker_stop: Decimal
    broker_take_profit: Decimal
    broker_expiration_utc: datetime
    risk: BrokerPolicyReceipt
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise DemoSafetyError("risk review cannot grant order authority")

    @property
    def mathematics_pass(self) -> bool:
        return self.risk.decision.disposition is FullRiskDisposition.ALLOW_MATH_ONLY


def preview_s2_full_policy_tpb(
    adapter: DemoMT5Adapter,
    request: DemoOrderRequest,
    *,
    now: datetime,
    cash_journal: ProspectiveDemoCashJournal,
    calibrated_costs: BoundAdverseCost,
    pinned_cost_sha256: str,
    official_snapshots: tuple[VerifiedOfficialSnapshot, ...],
    session_verified_through_utc: datetime | None,
    shock_locked: bool | None,
    normalized: bool | None,
) -> BoundS2PolicyReview:
    """Check one S2 pending STOP without enabling / submitting an order.

    The same MT5 object used by S2 supplies the broker history and actual
    order_calc_profit/margin. This removes caller-supplied Policy A figures.
    The session/source snapshots and calibration still require separate
    provenance admission: they CANNOT authorize orders even when they pass.
    """
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise DemoSafetyError("S2 Policy A review requires exact UTC")
    request.validate()
    if (
        not request.is_tpb_stop
        or request.entry_stop is None
        or request.take_profit is None
        or request.expires_utc is None
    ):
        raise DemoSafetyError("full Policy A review requires exact TPB STOP/SL/TP")
    # This identity check deliberately accepts a trading-disabled terminal:
    # the review must be safe to run against MT5 with Python orders OFF.
    adapter._identity_guard(require_execution_enabled=False)
    mt5 = adapter._mt5
    if mt5 is None:
        raise DemoSafetyError("initialized S2 MT5 source unavailable")

    window = screen_pending_entry_window(
        now=now, expires_utc=request.expires_utc,
        session_verified_through_utc=session_verified_through_utc,
        snapshots=official_snapshots, shock_locked=shock_locked,
        normalized=normalized,
    )
    if not window.allowed_to_proceed_to_other_gates:
        raise DemoSafetyError("STOP lifetime official/session admission denied")

    # The ACTUAL S2 builder must agree with the levels used for Policy A.
    # No separate order-building implementation is introduced.
    payload = adapter._build_request(request, now=now)
    if (
        payload.get("action") != getattr(mt5, "TRADE_ACTION_PENDING", None)
        or payload.get("type") not in (
            getattr(mt5, "ORDER_TYPE_BUY_STOP", None),
            getattr(mt5, "ORDER_TYPE_SELL_STOP", None),
        )
        or payload.get("symbol") != "XAUUSD"
        or payload.get("magic") != 260101
        or payload.get("type_time") != getattr(mt5, "ORDER_TIME_SPECIFIED", None)
        or payload.get("expiration") != int(request.expires_utc.timestamp())
    ):
        raise DemoSafetyError("S2 payload not the approved pending STOP envelope")

    entry = _decimal(payload.get("price"), "S2 STOP price")
    stop = _decimal(payload.get("sl"), "S2 protective stop")
    tp = _decimal(payload.get("tp"), "S2 take profit")
    volume = _decimal(payload.get("volume"), "S2 volume")
    if (
        entry != request.entry_stop or stop != request.stop_loss
        or tp != request.take_profit or volume != Decimal("0.01")
        or payload.get("type") != getattr(
            mt5,
            "ORDER_TYPE_BUY_STOP" if request.side.value == "BUY" else
            "ORDER_TYPE_SELL_STOP",
            None,
        )
    ):
        raise DemoSafetyError("S2 order values disagree with intended risk levels")

    observation = read_mt5_pro_demo_cash(mt5, now=now)
    if (
        observation.positions_count or observation.orders_count
        or observation.observed_utc != now
    ):
        raise DemoSafetyError("S2 cash must be a fresh flat account")
    baseline = cash_journal.observe(observation)

    calculated = preview_broker_full_policy_a(
        mt5, now=now, cash=observation, baseline=baseline,
        proposal=BrokerStopProposal(
            side=request.side.value, entry=entry,
            stop=stop, take_profit=tp,
        ),
        costs=calibrated_costs,
        expected_cost_sha256=pinned_cost_sha256,
        official_guard_pass=window.allowed_to_proceed_to_other_gates,
        session_source_verified=session_verified_through_utc is not None,
    )
    # Post-calculation source-freshness and account fields are separately
    # checked in the monetary calculator. No direct trading authorization.
    if not baseline.no_order_authority or calculated.execution_permitted:
        raise DemoSafetyError("broker cash journal or policy scope mutated")
    if calculated.tick_utc > now + timedelta(seconds=1):
        raise DemoSafetyError("broker quote clock exceeds review epoch")
    # Merely sourcing math from the real broker does NOT validate historical
    # calibration, the agency collector, or the MT5 order-send return path.
    return BoundS2PolicyReview(
        request_id=request.request_id, broker_order_type=int(payload["type"]),
        broker_entry=entry, broker_stop=stop, broker_take_profit=tp,
        broker_expiration_utc=request.expires_utc, risk=calculated,
    )
