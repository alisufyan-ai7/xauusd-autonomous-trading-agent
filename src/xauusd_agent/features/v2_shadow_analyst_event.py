"""Connect frozen Event Guard and frozen strict Analyst in shadow-only mode.

The event source collector must independently attest official source health.
Default AnalystClient transport is DISABLED. A synthetic fake may exercise the
contract offline; no production OpenAI call or broker operation is possible.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from xauusd_agent.analyst.client import AnalystClient
from xauusd_agent.analyst.schema import AnalystDecision, AnalystRequest
from xauusd_agent.features.v2_market_context import (
    ContextStatus,
    MarketContextReview,
)
from xauusd_agent.features.v2_tpb_research import (
    TPBResearchFinding,
    TPBResearchStatus,
)
from xauusd_agent.guards.event_guard import (
    EventObservation,
    evaluate_event_guard,
)


class ShadowAIState(StrEnum):
    NO_TRADE = "NO_TRADE"
    RESEARCH_SETUP = "RESEARCH_SETUP"


@dataclass(frozen=True, slots=True)
class ShadowAIVerdict:
    status: ShadowAIState
    reason_codes: tuple[str, ...]
    hypothesis_id: str | None = None
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("AI shadow verdict cannot grant broker execution")
        if self.status is ShadowAIState.NO_TRADE and self.hypothesis_id is not None:
            raise ValueError("NO_TRADE may not contain an actionable hypothesis")


def evaluate_shadow_tpb_ai(
    *,
    context: MarketContextReview,
    finding: TPBResearchFinding,
    event_observation: EventObservation | None,
    analyst: AnalystClient | None = None,
    versioned_policy_sha256: str,
) -> ShadowAIVerdict:
    def blocked(reason: str) -> ShadowAIVerdict:
        return ShadowAIVerdict(ShadowAIState.NO_TRADE, (reason,))

    if context.status is not ContextStatus.CONTEXT_READY:
        return blocked("MARKET_CONTEXT_NOT_READY")
    if finding.status is not TPBResearchStatus.TECHNICAL_HYPOTHESIS:
        return blocked(f"TECHNICAL_SETUP_REJECTED:{finding.reason}")
    if event_observation is None:
        return blocked("OFFICIAL_EVENT_SOURCE_MISSING")
    if event_observation.observed_utc != context.observed_at:
        return blocked("EVENT_SNAPSHOT_EPOCH_MISMATCH")
    event = evaluate_event_guard(event_observation)
    if not event.entry_allowed:
        return blocked(f"EVENT_GUARD:{event.state.value}")
    if finding.hypothesis_id is None or finding.direction is None:
        return blocked("RESEARCH_IDENTITY_MISSING")
    if (
        len(versioned_policy_sha256) != 64
        or any(c not in "0123456789abcdef" for c in versioned_policy_sha256)
    ):
        return blocked("POLICY_HASH_NOT_ADMITTED")
    # No account fingerprints, order identifiers, margin or raw broker data
    # may enter the strict model payload; only derived research descriptors.
    feature_hash = hashlib.sha256(
        f"{finding.hypothesis_id}|{finding.direction}|v2-tpb-research".encode("ascii")
    ).hexdigest()
    request_id = hashlib.sha256(
        f"v2-shadow-ai|{feature_hash}|{context.observed_at.isoformat()}".encode("ascii")
    ).hexdigest()
    request = AnalystRequest(
        request_id=request_id,
        observed_at=context.observed_at,
        deadline=context.observed_at + timedelta(seconds=2),
        symbol="XAUUSD",
        state_hash=feature_hash,
        feature_hash=feature_hash,
        policy_hash=versioned_policy_sha256,
        derived_inputs={
            "experimental_strategy": "TPB_ZONE_A_UNQUALIFIED",
            "direction": finding.direction,
            "market_timeframes": "W1,D1,H4,H1,M15,M5,M1",
            "event_guard": event.state.value,
            "risk_and_broker_admission": "NOT_EVALUATED",
        },
    )
    response = (analyst or AnalystClient()).evaluate(request, now=context.observed_at)
    if not response.admissible or response.decision is not AnalystDecision.SETUP:
        return ShadowAIVerdict(
            ShadowAIState.NO_TRADE,
            ("ANALYST_REJECT_OR_UNAVAILABLE", *response.reason_codes),
        )
    return ShadowAIVerdict(
        ShadowAIState.RESEARCH_SETUP,
        ("SHADOW_RESEARCH_ONLY_NOT_RISK_OR_BROKER_ADMITTED",),
        hypothesis_id=finding.hypothesis_id,
    )
