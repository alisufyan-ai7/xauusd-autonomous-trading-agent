"""One account-bound, read-only MT5 coordinator port; no parallel sender.

This is an integration bridge for the *existing* S2 adapter, not a second
broker execution path. It combines deterministic TPB proposals with
authoritative per-order and per-position reconciliation. It deliberately
refuses submit_qualified even if all synthetic tests are green: the existing
S2 hard Policy A blocker stays in force until independently admitted real
broker source, official calendar, calibrated costs and release authorization.
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from xauusd_agent.features.v2_tpb_stop_plan import TPBStopPlan

from .continuous_coordinator import (
    PendingBrokerAck,
    PendingOrderObservation,
    QualifiedBrokerAck,
    VerifiedProposal,
)
from .envelope import DemoSafetyError
from .known_position_reconciliation import (
    KnownMT5PositionPort,
    KnownPositionBinding,
)
from .mt5_demo import DemoMT5Adapter
from .pending_mt5_reconciliation import ReadOnlyPendingMT5Port
from .tpb_s2_bridge import BoundedTPBSubmission, translate_tpb_into_existing_s2


class TPBReadOnlyPlanSource(Protocol):
    def observe_closed_bar_plan(self, now: datetime) -> TPBStopPlan | None:
        """Read already independently established completed-bar TPB context.

        This source is not sufficient for execution permission. No model BUY/
        SELL recommendation or hand-crafted plan proves authoritative data.
        """


class ReadOnlyS2CoordinatorPort:
    """Implements the four coordinator port methods but refuses every order.

    For actual trading after admission, replace only the submit_qualified
    denial by a verified call through the *existing* S2 sender, never create
    another place which invokes MT5 order_send.
    """

    def __init__(
        self, *, adapter: DemoMT5Adapter, plan_source: TPBReadOnlyPlanSource
    ) -> None:
        self._adapter = adapter
        self._plan_source = plan_source
        self._current: BoundedTPBSubmission | None = None

    def _bound_mt5(self) -> object:
        # The read-only guard deliberately operates with external Python
        # trading DISABLED. Any account swap (including LIVE) is refused.
        self._adapter._identity_guard(require_execution_enabled=False)
        if self._adapter._mt5 is None:
            raise DemoSafetyError("MT5 coordinator source not initialized")
        return self._adapter._mt5

    def one_cycle_proposal(self, now: datetime) -> VerifiedProposal | None:
        self._current = None
        self._bound_mt5()
        plan = self._plan_source.observe_closed_bar_plan(now)
        if plan is None:
            return None
        candidate = translate_tpb_into_existing_s2(plan, now=now)
        # Validate the exact pending STOP envelope with the same S2 builder.
        # Quotes and session eligibility for real submission are separately
        # source-bound, and this preview can never authorize an order.
        self._adapter._build_request(
            candidate.pending_stop_request, now=now,
        )
        self._current = candidate
        return candidate.proposal

    def submit_qualified(
        self, proposal: VerifiedProposal, now: datetime
    ) -> QualifiedBrokerAck | PendingBrokerAck:
        self._bound_mt5()
        candidate = self._current
        if (
            candidate is None
            or candidate.proposal != proposal
            or candidate.pending_stop_request.entry_stop is None
            or candidate.pending_stop_request.take_profit is None
        ):
            raise DemoSafetyError("unbound or substituted TPB S2 proposal")
        proposal.validate(now)
        # NO broker check/send, NO spoofed risk Boolean, NO fabricated receipt:
        # no source has admitted v1.1 actual adverse costs and complete Policy A.
        raise DemoSafetyError(
            "FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED"
        )

    def known_position_state(
        self, receipt: QualifiedBrokerAck, now: datetime
    ) -> str:
        mt5 = self._bound_mt5()
        receipt.validate(
            setup_key=receipt.setup_key,
            account_fingerprint=self._adapter._identity.account_id_sha256,
            side=receipt.side,
        )
        # Reconstruct every position binding field from the durable exact
        # coordinator receipt (not volatile memory or guessed ticket).
        binding = KnownPositionBinding(
            position_id=receipt.position_id,
            entry_order=receipt.order_ticket,
            entry_deal=receipt.entry_deal_ticket,
            account_fingerprint=receipt.account_fingerprint,
            side=receipt.side,
            volume=receipt.volume_lots,
            protective_sl=receipt.stop_loss,
            protective_tp=receipt.take_profit,
            tick_size=receipt.tick_size,
        )
        return KnownMT5PositionPort(
            mt5, binding=binding
        ).known_position_state(receipt, now)

    def known_pending_state(
        self, receipt: PendingBrokerAck, now: datetime
    ) -> PendingOrderObservation:
        mt5 = self._bound_mt5()
        receipt.validate(
            setup_key=receipt.setup_key,
            account_fingerprint=self._adapter._identity.account_id_sha256,
            side=receipt.side,
        )
        return ReadOnlyPendingMT5Port(mt5).known_pending_state(receipt, now)
