"""Broker-observed seven-timeframe experimental TPB Zone-A strategy source.

Uses the repository's V2 research detector (NOT a proven profitable champion)
only after exact closed-bar/context source and independently supplied
official-event/session screening. This produces an *experimental demo
candidate*, never unmediated trading authority; the same S2 sender applies
full broker money/fee/exposure checks at the actual order boundary.

One bar can produce at most one deterministic setup key, and the persistent
coordinator rejects that key on all future cycles, including restarts.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Protocol

from xauusd_agent.features.v2_market_context import (
    ContextStatus,
    review_market_context,
)
from xauusd_agent.features.v2_tpb_research import (
    TPBResearchStatus,
    detect_tpb_research,
)
from xauusd_agent.features.v2_tpb_stop_plan import TPBStopPlan

from .demo_session_guard import assess_experimental_demo_window
from .envelope import DemoSafetyError
from .mt5_sevenframe_source import ReadOnlyMT5SevenFrameSource
from .pending_entry_window_guard import screen_pending_entry_window
from .s2_order_sources import S2OrderSources


class CurrentVerifiedSources(Protocol):
    def current_sources(self, now: datetime) -> S2OrderSources: ...


def _grid(price: Decimal, tick: Decimal, *, up: bool) -> Decimal:
    return (
        (price / tick).to_integral_value(
            rounding=ROUND_CEILING if up else ROUND_FLOOR,
        ) * tick
    )


class MT5ExperimentalTPBPlanSource:
    """Pure strategy output for one source-checked prospective M15 close."""

    def __init__(
        self,
        *,
        broker_bars: ReadOnlyMT5SevenFrameSource,
        sources: CurrentVerifiedSources,
        account_fingerprint: str,
    ) -> None:
        if len(account_fingerprint) != 64:
            raise DemoSafetyError("strategy account fingerprint unbound")
        self._bars = broker_bars
        self._sources = sources
        self._fingerprint = account_fingerprint
        self.last_reason = "NOT_YET_OBSERVED"

    def _no_trade(self, reason: str) -> None:
        self.last_reason = reason
        return None

    def observe_closed_bar_plan(self, now: datetime) -> TPBStopPlan | None:
        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise DemoSafetyError("TPB cycle requires UTC")
        try:
            feed = self._bars.capture(now=now)
        except DemoSafetyError:
            # Market closed, stale quote, bad history or no bars -> NO_TRADE.
            return self._no_trade("MT5_HISTORY_OR_QUOTE_NOT_READY")
        if now - feed.complete_m15_close_utc > timedelta(seconds=30):
            return self._no_trade("WAIT_FOR_NEXT_COMPLETED_M15_BAR")
        # Broker session + authenticated multiagency source must cover the
        # *whole* 45-minute pending lifetime, not merely today's entry time.
        sources = self._sources.current_sources(now)
        expiry = feed.complete_m15_close_utc + timedelta(minutes=45)
        if sources.source_mode == "EXPERIMENTAL_DEMO_NY_PROXY":
            admitted = assess_experimental_demo_window(
                now=now, pending_expires_utc=expiry,
            ).allowed
        elif sources.source_mode == "OFFICIAL_SOURCE":
            admitted = screen_pending_entry_window(
                now=now, expires_utc=expiry,
                session_verified_through_utc=sources.session_verified_through_utc,
                snapshots=sources.official_snapshots,
                shock_locked=sources.shock_locked,
                normalized=sources.normalized,
            ).allowed_to_proceed_to_other_gates
        else:
            raise DemoSafetyError("unknown broker demo source mode")
        if not admitted:
            return self._no_trade("DEMO_SESSION_OR_NEWS_WINDOW_BLOCKED")
        review = review_market_context(
            bars=feed.bars,
            quote=feed.quote,
            observed_at=now,
            session_clear=True,
            event_clear=True,
            shock_clear=(
                sources.source_mode == "EXPERIMENTAL_DEMO_NY_PROXY"
                or (sources.shock_locked is False and sources.normalized is True)
            ),
            broker_health_clear=True,
        )
        if review.status is not ContextStatus.CONTEXT_READY:
            return self._no_trade(
                "MARKET_CONTEXT_" + (
                    review.reasons[0] if review.reasons else "UNKNOWN"
                )
            )
        result = detect_tpb_research(
            context=review, frames=feed.bars, tick_size=feed.tick_size
        )
        if result.status is not TPBResearchStatus.TECHNICAL_HYPOTHESIS:
            return self._no_trade("TPB_" + result.reason)
        if any(x is None for x in (
            result.direction, result.entry, result.stop, result.tp1,
            result.target, result.hypothesis_id,
        )):
            return self._no_trade("TPB_LEVELS_INCOMPLETE")
        assert result.direction is not None
        assert result.entry is not None and result.stop is not None
        assert result.target is not None and result.tp1 is not None
        assert result.hypothesis_id is not None
        buy = result.direction == "LONG"
        entry = _grid(result.entry, feed.tick_size, up=buy)
        stop = _grid(result.stop, feed.tick_size, up=not buy)
        target = _grid(result.target, feed.tick_size, up=not buy)
        tp1 = _grid(result.tp1, feed.tick_size, up=not buy)
        if not (
            (buy and stop < entry < target and entry > feed.quote.ask)
            or (not buy and target < entry < stop and entry < feed.quote.bid)
        ):
            return self._no_trade("TPB_BROKER_ENTRY_GEOMETRY_UNQUALIFIED")
        # The experimental signal is separately cash+fee qualified again
        # by S2 at the actual broker order boundary.
        confirmed = feed.complete_m15_close_utc
        key = hashlib.sha256(
            (
                "XAUUSD-DEMO-EXPERIMENTAL-TPB-V0|"
                + self._fingerprint + "|" + result.hypothesis_id
                + "|" + confirmed.isoformat() + "|" + str(entry)
            ).encode("ascii")
        ).hexdigest()
        self.last_reason = "QUALIFIED_EXPERIMENTAL_TPB_CANDIDATE"
        return TPBStopPlan(
            setup_key=key, side="BUY" if buy else "SELL",
            entry_stop=entry, protective_stop=stop,
            take_profit=target, tp1_informational=tp1,
            confirmed_bar_utc=confirmed,
            expires_utc=confirmed + timedelta(minutes=45),
            proposal_expires_utc=confirmed + timedelta(seconds=30),
        )
