"""Pure cross-timeframe aggregation oracle using genuinely overlapping bars.

Do not compare MT5 W1 to seven D1 bars without proving the broker's
Sunday-boundary session conventions. Parent/child OHLC and tick volume must
agree when a complete set of child bars is causally available.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from xauusd_agent.features.v2_market_context import ContextBar, ContextTimeframe
from xauusd_agent.market.models import _require_utc

_PAIRS = (
    (ContextTimeframe.D1, ContextTimeframe.H4),
    (ContextTimeframe.H4, ContextTimeframe.H1),
    (ContextTimeframe.H1, ContextTimeframe.M15),
    (ContextTimeframe.M15, ContextTimeframe.M5),
    (ContextTimeframe.M5, ContextTimeframe.M1),
)


@dataclass(frozen=True, slots=True)
class CrossframeResult:
    accepted: bool
    reasons: tuple[str, ...]
    compared_parent_bars: int
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("crossframe check cannot authorize trading")


def audit_crossframe_aggregates(
    *, frames: Mapping[ContextTimeframe, Sequence[ContextBar]], as_of: datetime
) -> CrossframeResult:
    _require_utc(as_of, "as_of")
    reasons: set[str] = set()
    checked = 0
    for parent_tf, child_tf in _PAIRS:
        parent_bars = frames.get(parent_tf, ())
        child_bars = frames.get(child_tf, ())
        name = f"{parent_tf.value}_{child_tf.value}"
        if not parent_bars or not child_bars:
            reasons.add(f"{name}_NOT_OBSERVED")
            continue
        expected = int(parent_tf.duration / child_tf.duration)
        if child_tf.duration * expected != parent_tf.duration:
            reasons.add(f"{name}_DURATION_NOT_INTEGRAL")
            continue
        left_limit, right_limit = child_bars[0].open_time, child_bars[-1].close_time
        pair_count = 0
        for parent in parent_bars:
            if parent.open_time < left_limit or parent.close_time > right_limit:
                continue
            if parent.close_time > as_of:
                reasons.add(f"{name}_PARENT_FORMING")
                continue
            parts = [
                x for x in child_bars
                if parent.open_time <= x.open_time < parent.close_time
            ]
            if len(parts) != expected or any(
                x.open_time != parent.open_time + i * child_tf.duration
                for i, x in enumerate(parts)
            ):
                reasons.add(f"{name}_MISSING_OR_MISALIGNED_CHILD_BARS")
                continue
            checked += 1
            pair_count += 1
            if (
                parent.open != parts[0].open
                or parent.close != parts[-1].close
                or parent.high != max(p.high for p in parts)
                or parent.low != min(p.low for p in parts)
                or parent.tick_volume != sum(x.tick_volume for x in parts)
            ):
                reasons.add(f"{name}_OHLC_OR_VOLUME_DISAGREEMENT")
        if pair_count == 0:
            reasons.add(f"{name}_NO_COMPLETE_OVERLAPPING_PARENT")
    return CrossframeResult(not reasons, tuple(sorted(reasons)), checked)
