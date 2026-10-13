"""Pure Decimal implementations of the frozen common feature definitions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from xauusd_agent.market.models import Bar

ZERO = Decimal(0)
HUNDRED = Decimal(100)


@dataclass(frozen=True, slots=True)
class BarGeometry:
    range: Decimal
    body: Decimal
    body_fraction: Decimal | None
    close_location_long: Decimal | None
    close_location_short: Decimal | None


def bar_geometry(bar: Bar) -> BarGeometry:
    width = bar.high - bar.low
    body = abs(bar.close - bar.open)
    if width == ZERO:
        return BarGeometry(ZERO, body, None, None, None)
    return BarGeometry(
        width,
        body,
        body / width,
        (bar.close - bar.low) / width,
        (bar.high - bar.close) / width,
    )


def confirmed_swings(bars: Sequence[Bar]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Return two-left/two-right strictly confirmed swing indexes."""
    highs: list[int] = []
    lows: list[int] = []
    for index in range(2, len(bars) - 2):
        neighbours = (index - 2, index - 1, index + 1, index + 2)
        if all(bars[index].high > bars[other].high for other in neighbours):
            highs.append(index)
        if all(bars[index].low < bars[other].low for other in neighbours):
            lows.append(index)
    return tuple(highs), tuple(lows)


def regression_slope(values: Sequence[Decimal]) -> Decimal | None:
    if len(values) < 2:
        return None
    x_mean = Decimal(len(values) - 1) / Decimal(2)
    y_mean = sum(values, ZERO) / Decimal(len(values))
    denominator = sum(
        ((Decimal(index) - x_mean) ** 2 for index in range(len(values))),
        ZERO,
    )
    numerator = sum(
        ((Decimal(index) - x_mean) * (value - y_mean) for index, value in enumerate(values)),
        ZERO,
    )
    return numerator / denominator


def rejection_bar(bar: Bar, direction: str) -> bool:
    geometry = bar_geometry(bar)
    if geometry.body_fraction is None:
        return False
    if direction == "LONG":
        wick = min(bar.open, bar.close) - bar.low
        assert geometry.close_location_long is not None
        return wick >= geometry.body and geometry.close_location_long >= Decimal("0.65")
    if direction == "SHORT":
        wick = bar.high - max(bar.open, bar.close)
        assert geometry.close_location_short is not None
        return wick >= geometry.body and geometry.close_location_short >= Decimal("0.65")
    raise ValueError("direction must be LONG or SHORT")


def true_ranges(bars: Sequence[Bar]) -> tuple[Decimal, ...]:
    values: list[Decimal] = []
    for index, bar in enumerate(bars):
        if index == 0:
            values.append(bar.high - bar.low)
        else:
            previous = bars[index - 1].close
            values.append(
                max(bar.high - bar.low, abs(bar.high - previous), abs(bar.low - previous))
            )
    return tuple(values)


def wilders(values: Sequence[Decimal], period: int) -> tuple[Decimal | None, ...]:
    if period <= 0:
        raise ValueError("period must be positive")
    result: list[Decimal | None] = [None] * len(values)
    if len(values) < period:
        return tuple(result)
    divisor = Decimal(period)
    current = sum(values[:period], ZERO) / divisor
    result[period - 1] = current
    for index in range(period, len(values)):
        current = (Decimal(period - 1) * current + values[index]) / divisor
        result[index] = current
    return tuple(result)


def atr(bars: Sequence[Bar], period: int = 14) -> tuple[Decimal | None, ...]:
    return wilders(true_ranges(bars), period)


def ema(values: Sequence[Decimal], period: int) -> tuple[Decimal | None, ...]:
    if period <= 0:
        raise ValueError("period must be positive")
    result: list[Decimal | None] = [None] * len(values)
    if len(values) < period:
        return tuple(result)
    divisor = Decimal(period)
    current = sum(values[:period], ZERO) / divisor
    result[period - 1] = current
    alpha = Decimal(2) / Decimal(period + 1)
    for index in range(period, len(values)):
        current = alpha * values[index] + (Decimal(1) - alpha) * current
        result[index] = current
    return tuple(result)


def rsi(bars: Sequence[Bar], period: int = 14) -> tuple[Decimal | None, ...]:
    result: list[Decimal | None] = [None] * len(bars)
    if period <= 0:
        raise ValueError("period must be positive")
    if len(bars) <= period:
        return tuple(result)
    gains = [max(ZERO, bars[i].close - bars[i - 1].close) for i in range(1, len(bars))]
    losses = [max(ZERO, bars[i - 1].close - bars[i].close) for i in range(1, len(bars))]
    average_gains = wilders(gains, period)
    average_losses = wilders(losses, period)
    for offset in range(period - 1, len(gains)):
        gain = average_gains[offset]
        loss = average_losses[offset]
        assert gain is not None and loss is not None
        index = offset + 1
        if gain == ZERO and loss == ZERO:
            result[index] = Decimal(50)
        elif loss == ZERO:
            result[index] = HUNDRED
        else:
            ratio = gain / loss
            result[index] = HUNDRED - HUNDRED / (Decimal(1) + ratio)
    return tuple(result)


def adx(
    bars: Sequence[Bar], period: int = 14
) -> tuple[
    tuple[Decimal | None, ...],
    tuple[Decimal | None, ...],
    tuple[Decimal | None, ...],
]:
    if period <= 0:
        raise ValueError("period must be positive")
    size = len(bars)
    adx_values: list[Decimal | None] = [None] * size
    plus_di: list[Decimal | None] = [None] * size
    minus_di: list[Decimal | None] = [None] * size
    if size <= period:
        return tuple(adx_values), tuple(plus_di), tuple(minus_di)
    tr = true_ranges(bars)[1:]
    plus_dm: list[Decimal] = []
    minus_dm: list[Decimal] = []
    for index in range(1, size):
        upward = bars[index].high - bars[index - 1].high
        downward = bars[index - 1].low - bars[index].low
        plus_dm.append(upward if upward > downward and upward > ZERO else ZERO)
        minus_dm.append(downward if downward > upward and downward > ZERO else ZERO)
    smoothed_tr = wilders(tr, period)
    smoothed_plus = wilders(plus_dm, period)
    smoothed_minus = wilders(minus_dm, period)
    dx: list[Decimal] = []
    indexes: list[int] = []
    for offset in range(period - 1, len(tr)):
        current_tr = smoothed_tr[offset]
        current_plus = smoothed_plus[offset]
        current_minus = smoothed_minus[offset]
        assert current_tr is not None and current_plus is not None and current_minus is not None
        index = offset + 1
        if current_tr == ZERO:
            plus = minus = ZERO
        else:
            plus = HUNDRED * current_plus / current_tr
            minus = HUNDRED * current_minus / current_tr
        plus_di[index], minus_di[index] = plus, minus
        denominator = plus + minus
        dx.append(ZERO if denominator == ZERO else HUNDRED * abs(plus - minus) / denominator)
        indexes.append(index)
    smoothed_dx = wilders(dx, period)
    for offset, value in enumerate(smoothed_dx):
        if value is not None:
            adx_values[indexes[offset]] = value
    return tuple(adx_values), tuple(plus_di), tuple(minus_di)
