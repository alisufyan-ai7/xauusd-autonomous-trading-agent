from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from xauusd_agent.features.v2_crossframe_oracle import audit_crossframe_aggregates
from xauusd_agent.features.v2_market_context import ContextBar, ContextTimeframe

START = datetime(2026, 10, 21, tzinfo=UTC)
AS_OF = START + timedelta(days=1)


def make_frames():
    result = {}
    for tf in (
        ContextTimeframe.D1, ContextTimeframe.H4, ContextTimeframe.H1,
        ContextTimeframe.M15, ContextTimeframe.M5, ContextTimeframe.M1,
    ):
        count = int(timedelta(days=1) / tf.duration)
        result[tf] = tuple(
            ContextBar(
                timeframe=tf, open_time=START + i * tf.duration,
                open=Decimal("3000"), high=Decimal("3000"),
                low=Decimal("3000"), close=Decimal("3000"),
                tick_volume=int(tf.duration.total_seconds() / 60),
            )
            for i in range(count)
        )
    return result


def test_complete_six_frame_day_aggregates_consistently():
    result = audit_crossframe_aggregates(frames=make_frames(), as_of=AS_OF)
    assert result.accepted
    assert result.compared_parent_bars > 100
    assert result.execution_permitted is False


def test_actual_m5_child_close_divergence_rejected():
    f = make_frames()
    m1 = list(f[ContextTimeframe.M1])
    m1[0] = replace(
        m1[0], close=Decimal("3001"), high=Decimal("3001")
    )
    f[ContextTimeframe.M1] = tuple(m1)
    result = audit_crossframe_aggregates(frames=f, as_of=AS_OF)
    assert "M5_M1_OHLC_OR_VOLUME_DISAGREEMENT" in result.reasons


def test_one_missing_internal_child_bar_cannot_silently_pass():
    f = make_frames()
    m1 = list(f[ContextTimeframe.M1])
    del m1[12]
    f[ContextTimeframe.M1] = tuple(m1)
    result = audit_crossframe_aggregates(frames=f, as_of=AS_OF)
    assert "M5_M1_MISSING_OR_MISALIGNED_CHILD_BARS" in result.reasons


def test_missing_d1_or_unavailable_overlap_is_not_data_pass():
    f = make_frames()
    del f[ContextTimeframe.D1]
    assert not audit_crossframe_aggregates(frames=f, as_of=AS_OF).accepted
    assert not audit_crossframe_aggregates(frames={}, as_of=AS_OF).accepted


def test_crossframe_never_grants_order_authority():
    r = audit_crossframe_aggregates(frames=make_frames(), as_of=AS_OF)
    with pytest.raises(ValueError, match="cannot authorize"):
        replace(r, execution_permitted=True)
