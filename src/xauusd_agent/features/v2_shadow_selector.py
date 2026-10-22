"""Shadow-only selector for a prospectively admitted single strategy family.

Selection of a setup is NOT an execution/risk/broker admission and this module
has no order, model-network, position-management or MT5 capabilities.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from xauusd_agent.features.setups import (
    Direction,
    SetupCandidate,
    SetupFamily,
    SetupState,
)
from xauusd_agent.features.v2_market_context import (
    ContextStatus,
    MarketContextReview,
)


class ShadowDisposition(StrEnum):
    NO_TRADE = "NO_TRADE"
    SHADOW_CANDIDATE = "SHADOW_CANDIDATE"


@dataclass(frozen=True, slots=True)
class ChampionPolicy:
    family: SetupFamily
    strategy_version: str
    # No version is admitted to actual execution through this class.
    research_admitted: bool = False

    def __post_init__(self) -> None:
        if not self.strategy_version.strip():
            raise ValueError("a versioned champion strategy is required")


@dataclass(frozen=True, slots=True)
class ShadowSelection:
    disposition: ShadowDisposition
    reasons: tuple[str, ...]
    setup_id: str | None = None
    direction: Direction | None = None
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("shadow selection can never authorize execution")
        if self.disposition is ShadowDisposition.NO_TRADE and (
            self.setup_id is not None or self.direction is not None
        ):
            raise ValueError("NO_TRADE must not contain an actionable candidate")
        if self.disposition is ShadowDisposition.SHADOW_CANDIDATE and (
            not self.setup_id or self.direction is None or self.reasons
        ):
            raise ValueError("shadow proposal must identify one unambiguous setup")


def select_shadow_champion(
    *,
    context: MarketContextReview,
    policy: ChampionPolicy,
    candidates: Sequence[SetupCandidate],
) -> ShadowSelection:
    """Choose only one already-validated setup; never invent missing predicates.

    The champion policy is a *research* acceptance flag and cannot be a real
    broker execution permit. Later work must validate raw family predicates,
    news source health, broker monetary risk, live state and activation.
    """
    if context.status is not ContextStatus.CONTEXT_READY:
        return ShadowSelection(
            ShadowDisposition.NO_TRADE,
            ("MARKET_CONTEXT_NOT_READY", *context.reasons),
        )
    if not policy.research_admitted:
        return ShadowSelection(ShadowDisposition.NO_TRADE, ("CHAMPION_NOT_RESEARCH_ADMITTED",))
    selected = [
        c for c in candidates
        if c.state is SetupState.PROPOSED
        and c.family is policy.family
        and c.decision_time == context.observed_at
    ]
    # Any other simultaneously proposed setup represents an unresolved conflict
    # even if it belongs to a nonchampion family. An upstream strategy may
    # not silently ignore a competing broker-eligible proposal.
    proposed = [c for c in candidates if c.state is SetupState.PROPOSED]
    if len(selected) != 1 or len(proposed) != 1:
        return ShadowSelection(ShadowDisposition.NO_TRADE, ("MISSING_OR_COMPETING_SETUP",))
    champion = selected[0]
    if not champion.setup_id or champion.entry is None or champion.stop is None:
        return ShadowSelection(ShadowDisposition.NO_TRADE, ("INCOMPLETE_SETUP",))
    return ShadowSelection(
        ShadowDisposition.SHADOW_CANDIDATE,
        (),
        setup_id=champion.setup_id,
        direction=champion.direction,
    )
