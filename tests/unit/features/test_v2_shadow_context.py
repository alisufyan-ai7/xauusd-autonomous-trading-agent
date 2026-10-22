from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from xauusd_agent.features.setups import Direction, SetupCandidate, SetupFamily, SetupState
from xauusd_agent.features.v2_market_context import (
    ContextBar,
    ContextStatus,
    ContextTimeframe,
    review_market_context,
)
from xauusd_agent.features.v2_shadow_selector import (
    ChampionPolicy,
    ShadowDisposition,
    select_shadow_champion,
)
from xauusd_agent.market.models import Quote

NOW = datetime(2026, 10, 22, 12, tzinfo=UTC)
PRICE = Decimal("3000")
TICK = Decimal("0.001")


def sample_bars() -> dict[ContextTimeframe, tuple[ContextBar, ...]]:
    return {
        timeframe: tuple(
            ContextBar(
                timeframe=timeframe,
                open_time=NOW - timeframe.duration * (count - index),
                open=PRICE, high=PRICE + Decimal("1"), low=PRICE - Decimal("1"),
                close=PRICE, tick_volume=100,
            )
            for index in range(count)
        )
        for timeframe, count in {
            ContextTimeframe.W1: 3,
            ContextTimeframe.D1: 6,
            ContextTimeframe.H4: 9,
            ContextTimeframe.H1: 13,
            ContextTimeframe.M15: 13,
            ContextTimeframe.M5: 13,
            ContextTimeframe.M1: 16,
        }.items()
    }


def quote() -> Quote:
    return Quote(
        symbol="XAUUSD",
        broker_time=NOW - timedelta(seconds=1),
        received_time=NOW,
        bid=PRICE, ask=PRICE + Decimal("0.010"),
        tick_size=TICK, sequence=1,
    )


def review(**changes):
    inputs = {
        "bars": sample_bars(), "quote": quote(), "observed_at": NOW,
        "session_clear": True, "event_clear": True, "shock_clear": True,
        "broker_health_clear": True,
    }
    inputs.update(changes)
    return review_market_context(**inputs)


def candidate(family: SetupFamily = SetupFamily.TPB) -> SetupCandidate:
    return SetupCandidate(
        setup_id="a" * 64, family=family, direction=Direction.LONG,
        decision_time=NOW, state=SetupState.PROPOSED, reasons=(),
        entry=PRICE, stop=PRICE - Decimal("1"),
        tp1=PRICE + Decimal("1.5"), final_target=PRICE + Decimal("2"),
        expiry_bars=4,
    )


def test_seven_completed_timeframes_are_context_ready_but_not_execution() -> None:
    result = review()
    assert result.status is ContextStatus.CONTEXT_READY
    assert not result.reasons
    assert len(result.required_timeframes) == 7
    assert result.execution_permitted is False


def test_missing_early_timeframe_fails_closed() -> None:
    bars = sample_bars()
    del bars[ContextTimeframe.W1]
    result = review(bars=bars)
    assert result.status is ContextStatus.NO_TRADE
    assert "TIMEFRAME_SET_INCOMPLETE" in result.reasons


def test_uncompleted_future_bar_and_missing_history_fail_closed() -> None:
    bars = sample_bars()
    future = replace(bars[ContextTimeframe.M15][-1], open_time=NOW)
    bars[ContextTimeframe.M15] = (*bars[ContextTimeframe.M15][:-1], future)
    assert "M15_INCOMPLETE_FUTURE_BAR" in review(bars=bars).reasons
    short = sample_bars()
    short[ContextTimeframe.M1] = short[ContextTimeframe.M1][-2:]
    assert "M1_INSUFFICIENT_BARS" in review(bars=short).reasons


def test_stale_or_future_quote_fails_closed() -> None:
    assert "QUOTE_STALE_OR_CLOCK_CONFLICT" in review(
        quote=replace(quote(), broker_time=NOW - timedelta(seconds=20))
    ).reasons
    assert "QUOTE_STALE_OR_CLOCK_CONFLICT" in review(
        quote=replace(quote(), broker_time=NOW + timedelta(seconds=2))
    ).reasons


def test_missing_session_news_or_health_cannot_be_defaulted_clear() -> None:
    result = review(session_clear=None, event_clear=False, broker_health_clear=None)
    assert result.status is ContextStatus.NO_TRADE
    assert "SESSION_UNKNOWN_OR_BLOCKED" in result.reasons
    assert "EVENT_UNKNOWN_OR_BLOCKED" in result.reasons
    assert "BROKER_HEALTH_UNKNOWN_OR_BLOCKED" in result.reasons


def test_missing_microstructure_bar_or_ordering_fails_closed() -> None:
    bars = sample_bars()
    series = list(bars[ContextTimeframe.M5])
    series[-2] = replace(series[-2], open_time=series[-2].open_time - timedelta(minutes=1))
    bars[ContextTimeframe.M5] = tuple(series)
    assert "M5_RECENT_GAP" in review(bars=bars).reasons
    unsorted = sample_bars()
    series2 = list(unsorted[ContextTimeframe.H1])
    series2[-2], series2[-1] = series2[-1], series2[-2]
    unsorted[ContextTimeframe.H1] = tuple(series2)
    assert "H1_UNSORTED_OR_OVERLAPPING" in review(bars=unsorted).reasons


def test_nonfinite_invalid_ohlc_rejected_at_object_boundary() -> None:
    with pytest.raises(ValueError, match="finite"):
        replace(sample_bars()[ContextTimeframe.M1][-1], close=Decimal("NaN"))
    with pytest.raises(ValueError, match="XAUUSD"):
        replace(sample_bars()[ContextTimeframe.H4][-1], symbol="XAUUSDc")


def test_unadmitted_champion_is_no_trade() -> None:
    result = select_shadow_champion(
        context=review(), policy=ChampionPolicy(SetupFamily.TPB, "test-v1"),
        candidates=(candidate(),),
    )
    assert result.disposition is ShadowDisposition.NO_TRADE
    assert result.setup_id is None
    assert result.execution_permitted is False


def test_admitted_champion_emits_shadow_candidate_never_execution() -> None:
    policy = ChampionPolicy(SetupFamily.TPB, "test-v1", research_admitted=True)
    result = select_shadow_champion(
        context=review(), policy=policy, candidates=(candidate(),),
    )
    assert result.disposition is ShadowDisposition.SHADOW_CANDIDATE
    assert result.setup_id == "a" * 64
    assert result.direction is Direction.LONG
    assert result.execution_permitted is False


def test_duplicate_or_competing_candidate_is_no_trade() -> None:
    policy = ChampionPolicy(SetupFamily.TPB, "test-v1", research_admitted=True)
    for inputs in (
        (candidate(), candidate()),
        (candidate(), candidate(SetupFamily.BRT)),
        (candidate(SetupFamily.BRT),),
        (),
    ):
        result = select_shadow_champion(context=review(), policy=policy, candidates=inputs)
        assert result.disposition is ShadowDisposition.NO_TRADE
        assert result.setup_id is None


def test_bad_context_and_wrong_decision_time_block_shadow() -> None:
    policy = ChampionPolicy(SetupFamily.TPB, "test-v1", research_admitted=True)
    result = select_shadow_champion(
        context=review(event_clear=None), policy=policy, candidates=(candidate(),),
    )
    assert result.disposition is ShadowDisposition.NO_TRADE
    stale = replace(candidate(), decision_time=NOW - timedelta(minutes=15))
    result2 = select_shadow_champion(context=review(), policy=policy, candidates=(stale,))
    assert result2.disposition is ShadowDisposition.NO_TRADE


def test_reject_invalid_policy_version_and_immutable_execution_gate() -> None:
    with pytest.raises(ValueError, match="version"):
        ChampionPolicy(SetupFamily.TPB, " ")
    with pytest.raises(ValueError, match="never authorize"):
        replace(review(), execution_permitted=True)
