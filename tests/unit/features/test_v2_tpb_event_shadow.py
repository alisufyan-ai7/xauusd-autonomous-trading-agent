"""No broker, model network or data-source calls in these tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from xauusd_agent.analyst.client import AnalystVerdict
from xauusd_agent.analyst.schema import AnalystDecision
from xauusd_agent.features.v2_market_context import (
    ContextStatus,
    ContextTimeframe,
    MarketContextReview,
)
from xauusd_agent.features.v2_shadow_analyst_event import (
    ShadowAIState,
    evaluate_shadow_tpb_ai,
)
from xauusd_agent.features.v2_tpb_research import (
    TPBResearchFinding,
    TPBResearchStatus,
    detect_tpb_research,
)
from xauusd_agent.guards.event_guard import EventObservation, ProtectedEvent

NOW = datetime(2026, 10, 22, 12, tzinfo=UTC)
POLICY = "f" * 64


def context() -> MarketContextReview:
    return MarketContextReview(
        ContextStatus.CONTEXT_READY, NOW, (), tuple(ContextTimeframe)
    )


def finding() -> TPBResearchFinding:
    return TPBResearchFinding(
        status=TPBResearchStatus.TECHNICAL_HYPOTHESIS,
        reason="SYNTHETIC_RESEARCH_ONLY",
        direction="LONG",
        entry=Decimal("3010"), stop=Decimal("3000"),
        tp1=Decimal("3025"), target=Decimal("3035"),
        hypothesis_id="a" * 64,
    )


def event_obs(**changes):
    fields = {
        "observed_utc": NOW,
        "events": (ProtectedEvent("synthetic-far-event", NOW + timedelta(days=7),
                                  "TIER_1"),),
        "source_healthy": True,
        "sources_agree": True,
        "coverage_complete": True,
        "shock_locked": False,
        "normalized": True,
    }
    fields.update(changes)
    return EventObservation(**fields)


class SyntheticApprovedAnalyst:
    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, request, *, now=None):
        payload = request.to_payload()
        assert payload["tools"] == [] and payload["store"] is False
        assert "login" not in str(payload) and "account" not in payload
        self.calls += 1
        return AnalystVerdict(AnalystDecision.SETUP, True, ("SYNTHETIC",))


def check(*, ctx=None, hypothesis=None, event=None, analyst=None, policy=POLICY):
    return evaluate_shadow_tpb_ai(
        context=ctx or context(),
        finding=hypothesis or finding(),
        event_observation=event,
        analyst=analyst,
        versioned_policy_sha256=policy,
    )


def test_unqualified_tpb_requires_frozen_warmup_and_never_executes() -> None:
    result = detect_tpb_research(context=context(), frames={}, tick_size=Decimal("0.001"))
    assert result.status is TPBResearchStatus.NO_TRADE
    assert result.reason == "FROZEN_STRATEGY_WARMUP_INSUFFICIENT"
    assert result.execution_permitted is False
    assert result.entry is None


def test_event_inventory_absent_makes_no_model_call() -> None:
    fake = SyntheticApprovedAnalyst()
    result = check(analyst=fake, event=None)
    assert result.status is ShadowAIState.NO_TRADE
    assert fake.calls == 0


def test_event_lock_and_missing_source_health_prevent_ai_use() -> None:
    fake = SyntheticApprovedAnalyst()
    for event in (
        event_obs(events=(ProtectedEvent("synthetic-now", NOW, "TIER_1"),)),
        event_obs(source_healthy=None),
        event_obs(shock_locked=True),
    ):
        result = check(event=event, analyst=fake)
        assert result.status is ShadowAIState.NO_TRADE
        assert fake.calls == 0


def test_event_epoch_mismatch_fails_closed() -> None:
    fake = SyntheticApprovedAnalyst()
    result = check(
        event=event_obs(observed_utc=NOW - timedelta(seconds=1)), analyst=fake
    )
    assert result.status is ShadowAIState.NO_TRADE
    assert fake.calls == 0


def test_default_analyst_is_disabled_even_with_healthy_event() -> None:
    result = check(event=event_obs())
    assert result.status is ShadowAIState.NO_TRADE
    assert "ANALYST_REJECT_OR_UNAVAILABLE" in result.reason_codes
    assert not result.execution_permitted


def test_synthetic_analyst_proposal_is_only_research() -> None:
    fake = SyntheticApprovedAnalyst()
    result = check(event=event_obs(), analyst=fake)
    assert fake.calls == 1
    assert result.status is ShadowAIState.RESEARCH_SETUP
    assert result.hypothesis_id == "a" * 64
    assert result.execution_permitted is False


def test_rejected_technical_hypothesis_no_cloud_call() -> None:
    fake = SyntheticApprovedAnalyst()
    rejected = replace(
        finding(), status=TPBResearchStatus.NO_TRADE, direction=None,
        entry=None, stop=None, tp1=None, target=None,
        hypothesis_id=None,
    )
    result = check(event=event_obs(), hypothesis=rejected, analyst=fake)
    assert result.status is ShadowAIState.NO_TRADE
    assert fake.calls == 0


def test_policy_hash_missing_blocks_analyst() -> None:
    fake = SyntheticApprovedAnalyst()
    result = check(event=event_obs(), analyst=fake, policy="not-a-sha")
    assert result.status is ShadowAIState.NO_TRADE
    assert fake.calls == 0


def test_market_context_invalid_no_model_call() -> None:
    fake = SyntheticApprovedAnalyst()
    bad = MarketContextReview(
        ContextStatus.NO_TRADE, NOW, ("M1_STALE",), tuple(ContextTimeframe)
    )
    result = check(ctx=bad, event=event_obs(), analyst=fake)
    assert result.status is ShadowAIState.NO_TRADE
    assert fake.calls == 0
