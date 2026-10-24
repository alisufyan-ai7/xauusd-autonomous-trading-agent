"""Execution-capable coordinator bridge to ONE existing S2 MT5 sender.

Not a second order implementation. The bridge previews the exact current
STOP proposal using real broker cash/official-session sources, then invokes
DemoMT5Adapter.submit_market_order (the *single* MT5 order_check/order_send
site) which MUST recompute full Policy A at submit time.
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .continuous_coordinator import (
    PendingBrokerAck,
    QualifiedBrokerAck,
    VerifiedProposal,
)
from .envelope import DemoActivationPermit, DemoSafetyError
from .mt5_demo import SUBMISSION_CONFIRMATION, DemoMT5Adapter
from .risk_binding import DemoRiskCalibration
from .s2_full_policy_probe import preview_s2_full_policy_tpb
from .s2_order_sources import S2OrderSources
from .s2_readonly_coordinator_port import ReadOnlyS2CoordinatorPort, TPBReadOnlyPlanSource


class RealDemoOrderSource(Protocol):
    def current_sources(self, now: datetime) -> S2OrderSources:
        """Return the current audited, expiring official/cost/cash data.

        Implementations MUST read actual source receipts, not caller-given
        True flags or placeholder hashes. S2 independently verifies all
        broker/account/cash/cost/stop/session/quote values before submission.
        """
        ...


class QualifiedS2CoordinatorPort(ReadOnlyS2CoordinatorPort):
    """Only when explicitly constructed with activated S2 + audited sources."""

    def __init__(
        self,
        *,
        adapter: DemoMT5Adapter,
        plan_source: TPBReadOnlyPlanSource,
        sources: RealDemoOrderSource,
        activation: DemoActivationPermit,
        risk_calibration: DemoRiskCalibration,
    ) -> None:
        super().__init__(adapter=adapter, plan_source=plan_source)
        self._sources = sources
        self._activation = activation
        self._risk_calibration = risk_calibration

    def one_cycle_proposal(self, now: datetime) -> VerifiedProposal | None:
        # Killed/unknown terminal does not create phantom PREPARING intents.
        self._adapter._identity_guard(require_execution_enabled=True)
        candidate = self.inspect_closed_bar_plan(now)
        if candidate is None:
            return None
        context = self._sources.current_sources(now)
        review = preview_s2_full_policy_tpb(
            self._adapter, candidate.pending_stop_request, now=now,
            cash_journal=context.cash_journal,
            calibrated_costs=context.costs,
            pinned_cost_sha256=context.expected_cost_sha256,
            official_snapshots=context.official_snapshots,
            session_verified_through_utc=context.session_verified_through_utc,
            shock_locked=context.shock_locked,
            normalized=context.normalized,
            source_mode=context.source_mode,
        )
        if not review.mathematics_pass:
            # Risk rejection is a valid NO_TRADE, not a pending broker order.
            return None
        return candidate.proposal

    def submit_qualified(
        self, proposal: VerifiedProposal, now: datetime
    ) -> QualifiedBrokerAck | PendingBrokerAck:
        candidate = self._current
        if candidate is None or candidate.proposal != proposal:
            raise DemoSafetyError("coordinator proposal is not the bound S2 STOP")
        proposal.validate(now)
        context = self._sources.current_sources(now)
        result = self._adapter.submit_market_order(
            candidate.pending_stop_request,
            confirmation_phrase=SUBMISSION_CONFIRMATION,
            activation_permit=self._activation,
            risk_calibration=self._risk_calibration,
            full_policy_sources=context,
            now=now,
        )
        # A pending STOP is NOT FILLED. The existing S2 adapter alone performs
        # the broker order API calls and verifies one exact accepted order.
        ticket = result.get("pending_order_ticket")
        if (
            result.get("status") != "PENDING_ACKNOWLEDGED"
            or type(ticket) is not int
            or ticket <= 0
            or result.get("request_id") != candidate.pending_stop_request.request_id
        ):
            raise DemoSafetyError("S2 failed to return an exact pending STOP receipt")
        req = candidate.pending_stop_request
        if req.entry_stop is None or req.take_profit is None or req.expires_utc is None:
            raise DemoSafetyError("submitted S2 STOP source lost bound levels")
        receipt = PendingBrokerAck(
            setup_key=proposal.setup_key,
            account_fingerprint=self._adapter._identity.account_id_sha256,
            order_ticket=ticket,
            side=proposal.side,
            volume_lots=req.volume_lots,
            entry_stop=req.entry_stop,
            stop_loss=req.stop_loss,
            take_profit=req.take_profit,
            expires_utc=req.expires_utc,
        )
        receipt.validate(
            setup_key=proposal.setup_key,
            account_fingerprint=self._adapter._identity.account_id_sha256,
            side=proposal.side,
            now=now,
        )
        self._current = None
        return receipt
