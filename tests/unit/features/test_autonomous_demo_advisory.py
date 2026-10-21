from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from xauusd_agent.features.autonomous_demo_advisory import (
    AdvisoryDisposition,
    AdvisorySide,
    advise_h1_m15,
)
from xauusd_agent.market.models import Bar, Timeframe

AT = datetime(2026, 10, 21, 14, tzinfo=UTC)
TICK = Decimal("0.001")


def bars(tf: Timeframe, n: int, *, long: bool = True) -> list[Bar]:
    duration = tf.duration
    output = []
    for idx in range(n):
        factor = Decimal(idx) * (Decimal("0.08") if tf is Timeframe.H1 else Decimal("0.10"))
        level = Decimal("3000") + factor if long else Decimal("3010") - factor
        if long:
            op, hi, lo, cl = (
                level - Decimal("0.20"), level + Decimal("0.02"),
                level - Decimal("0.23"), level,
            )
        else:
            op, hi, lo, cl = (
                level + Decimal("0.20"), level + Decimal("0.23"),
                level - Decimal("0.02"), level,
            )
        output.append(Bar(
            symbol="XAUUSD", timeframe=tf,
            open_time=AT - duration * (n - idx),
            open=op, high=hi, low=lo, close=cl, tick_volume=100,
        ))
    return output


def test_closed_bar_long_candidate_never_permits_execution() -> None:
    result = advise_h1_m15(h1=bars(Timeframe.H1, 60), m15=bars(Timeframe.M15, 48),
                           observed_at=AT, tick_size=TICK)
    assert result.disposition is AdvisoryDisposition.CANDIDATE
    assert result.side is AdvisorySide.LONG
    assert not result.execution_permitted
    assert result.reference_entry is not None and result.reference_stop is not None
    assert result.reference_entry > result.reference_stop
    assert result.signal_id is not None and len(result.signal_id) == 64
    assert result == advise_h1_m15(h1=bars(Timeframe.H1, 60), m15=bars(Timeframe.M15, 48),
                                   observed_at=AT, tick_size=TICK)


def test_closed_bar_short_candidate() -> None:
    result = advise_h1_m15(h1=bars(Timeframe.H1, 60, long=False),
                           m15=bars(Timeframe.M15, 48, long=False),
                           observed_at=AT, tick_size=TICK)
    assert result.disposition is AdvisoryDisposition.CANDIDATE
    assert result.side is AdvisorySide.SHORT
    assert not result.execution_permitted
    assert result.reference_stop is not None and result.reference_entry is not None
    assert result.reference_stop > result.reference_entry


def test_future_bar_and_expired_tick_are_no_trade() -> None:
    m15 = bars(Timeframe.M15, 48)
    future = [*m15[:-1], replace(m15[-1], open_time=AT)]
    assert advise_h1_m15(h1=bars(Timeframe.H1, 60), m15=future, observed_at=AT,
                         tick_size=TICK).disposition is AdvisoryDisposition.NO_TRADE
    assert advise_h1_m15(h1=bars(Timeframe.H1, 60), m15=m15,
                         observed_at=AT + timedelta(hours=2),
                         tick_size=TICK).disposition is AdvisoryDisposition.NO_TRADE


def test_wrong_symbol_and_gap_are_no_trade() -> None:
    m15 = bars(Timeframe.M15, 48)
    wrong = [*m15[:-1], replace(m15[-1], symbol="EURUSD")]
    assert advise_h1_m15(h1=bars(Timeframe.H1, 60), m15=wrong, observed_at=AT,
                         tick_size=TICK).disposition is AdvisoryDisposition.NO_TRADE
    gap = [*m15[:-2], replace(m15[-1], open_time=AT - timedelta(minutes=1))]
    assert advise_h1_m15(h1=bars(Timeframe.H1, 60), m15=gap, observed_at=AT,
                         tick_size=TICK).disposition is AdvisoryDisposition.NO_TRADE


def test_mismatch_trend_and_m15_direction_are_no_trade() -> None:
    result = advise_h1_m15(h1=bars(Timeframe.H1, 60),
                           m15=bars(Timeframe.M15, 48, long=False),
                           observed_at=AT, tick_size=TICK)
    assert result.disposition is AdvisoryDisposition.NO_TRADE


def test_inadequate_history_is_no_trade() -> None:
    result = advise_h1_m15(h1=bars(Timeframe.H1, 20),
                           m15=bars(Timeframe.M15, 24),
                           observed_at=AT, tick_size=TICK)
    assert result.disposition is AdvisoryDisposition.NO_TRADE
