"""Independent OHLC-derived feature oracle for Gate 0.

This module is deliberately pure: it has no broker, filesystem, network, model,
or order API. Bars are chronological (oldest first); incomplete bars are never
eligible inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from math import sqrt
from statistics import median
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Bar:
    time: int
    open: float
    high: float
    low: float
    close: float
    tick_volume: int = 1


def completed_bars(bars: Sequence[Bar], decision_time: int, period_seconds: int) -> list[Bar]:
    return [bar for bar in bars if bar.time + period_seconds <= decision_time]


def validate_series(
    bars: Sequence[Bar], *, decision_time: int, period_seconds: int, minimum: int,
    known_breaks: Iterable[tuple[int, int]] = (),
) -> tuple[bool, str]:
    eligible = completed_bars(bars, decision_time, period_seconds)
    if len(eligible) < minimum:
        return False, "WARMUP_MISSING"
    allowed = set(known_breaks)
    for i, bar in enumerate(eligible):
        if bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close) or bar.high < bar.low:
            return False, "OHLC_INVALID"
        if i:
            prior = eligible[i - 1]
            if bar.time <= prior.time:
                return False, "TIMESTAMP_DUPLICATE_OR_NONMONOTONIC"
            if bar.time - prior.time != period_seconds and (prior.time + period_seconds, bar.time) not in allowed:
                return False, "UNEXPLAINED_GAP"
    return True, "CLEAR"


def true_ranges(bars: Sequence[Bar]) -> list[float]:
    out: list[float] = []
    for i, bar in enumerate(bars):
        if i == 0:
            out.append(bar.high - bar.low)
        else:
            prior_close = bars[i - 1].close
            out.append(max(bar.high - bar.low, abs(bar.high - prior_close), abs(bar.low - prior_close)))
    return out


def wilders(values: Sequence[float], n: int) -> list[float | None]:
    if n <= 0:
        raise ValueError("n must be positive")
    result: list[float | None] = [None] * len(values)
    if len(values) < n:
        return result
    current = sum(values[:n]) / n
    result[n - 1] = current
    for i in range(n, len(values)):
        current = ((n - 1) * current + values[i]) / n
        result[i] = current
    return result


def atr(bars: Sequence[Bar], n: int = 14) -> list[float | None]:
    return wilders(true_ranges(bars), n)


def ema(values: Sequence[float], n: int) -> list[float | None]:
    if n <= 0:
        raise ValueError("n must be positive")
    result: list[float | None] = [None] * len(values)
    if len(values) < n:
        return result
    current = sum(values[:n]) / n
    result[n - 1] = current
    alpha = 2 / (n + 1)
    for i in range(n, len(values)):
        current = alpha * values[i] + (1 - alpha) * current
        result[i] = current
    return result


def rsi(bars: Sequence[Bar], n: int = 14) -> list[float | None]:
    result: list[float | None] = [None] * len(bars)
    if len(bars) <= n:
        return result
    gains = [max(0.0, bars[i].close - bars[i - 1].close) for i in range(1, len(bars))]
    losses = [max(0.0, bars[i - 1].close - bars[i].close) for i in range(1, len(bars))]
    avg_gains = wilders(gains, n)
    avg_losses = wilders(losses, n)
    for j in range(n - 1, len(gains)):
        gain, loss = avg_gains[j], avg_losses[j]
        assert gain is not None and loss is not None
        i = j + 1
        if gain == 0 and loss == 0:
            result[i] = 50.0
        elif loss == 0:
            result[i] = 100.0
        else:
            rs = gain / loss
            result[i] = 100 - 100 / (1 + rs)
    return result


def adx(bars: Sequence[Bar], n: int = 14) -> tuple[list[float | None], list[float | None], list[float | None]]:
    size = len(bars)
    plus_di: list[float | None] = [None] * size
    minus_di: list[float | None] = [None] * size
    adx_values: list[float | None] = [None] * size
    if size <= n:
        return adx_values, plus_di, minus_di
    trs = true_ranges(bars)[1:]
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for i in range(1, size):
        up = bars[i].high - bars[i - 1].high
        down = bars[i - 1].low - bars[i].low
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
    sm_tr, sm_plus, sm_minus = wilders(trs, n), wilders(plus_dm, n), wilders(minus_dm, n)
    dx: list[float] = []
    dx_indexes: list[int] = []
    for j in range(n - 1, len(trs)):
        tr = sm_tr[j]
        assert tr is not None and sm_plus[j] is not None and sm_minus[j] is not None
        i = j + 1
        if tr == 0:
            p = m = 0.0
        else:
            p, m = 100 * sm_plus[j] / tr, 100 * sm_minus[j] / tr
        plus_di[i], minus_di[i] = p, m
        denom = p + m
        dx.append(0.0 if denom == 0 else 100 * abs(p - m) / denom)
        dx_indexes.append(i)
    sm_dx = wilders(dx, n)
    for j, value in enumerate(sm_dx):
        if value is not None:
            adx_values[dx_indexes[j]] = value
    return adx_values, plus_di, minus_di


def confirmed_swings(bars: Sequence[Bar]) -> tuple[list[int], list[int]]:
    highs: list[int] = []
    lows: list[int] = []
    for i in range(2, len(bars) - 2):
        if all(bars[i].high > bars[j].high for j in (i - 2, i - 1, i + 1, i + 2)):
            highs.append(i)
        if all(bars[i].low < bars[j].low for j in (i - 2, i - 1, i + 1, i + 2)):
            lows.append(i)
    return highs, lows


def regression_slope(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    x_mean = (len(values) - 1) / 2
    y_mean = sum(values) / len(values)
    denom = sum((i - x_mean) ** 2 for i in range(len(values)))
    return sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values)) / denom


def bar_geometry(bar: Bar) -> dict[str, float | None]:
    width = bar.high - bar.low
    body = abs(bar.close - bar.open)
    if width == 0:
        return {"range": 0.0, "body": body, "body_fraction": None, "close_long": None, "close_short": None}
    return {
        "range": width,
        "body": body,
        "body_fraction": body / width,
        "close_long": (bar.close - bar.low) / width,
        "close_short": (bar.high - bar.close) / width,
    }


def rejection_bar(bar: Bar, direction: str) -> bool:
    g = bar_geometry(bar)
    if g["range"] == 0:
        return False
    body = float(g["body"])
    if direction == "LONG":
        wick = min(bar.open, bar.close) - bar.low
        return wick >= body and float(g["close_long"]) >= 0.65
    if direction == "SHORT":
        wick = bar.high - max(bar.open, bar.close)
        return wick >= body and float(g["close_short"]) >= 0.65
    raise ValueError("direction")


def tpb_zones(impulse_start: float, impulse_end: float, direction: str) -> dict[str, tuple[float, float]]:
    distance = abs(impulse_end - impulse_start)
    if distance == 0:
        raise ValueError("zero impulse")
    if direction == "LONG" and impulse_end > impulse_start:
        return {"A": (impulse_end - 0.500 * distance, impulse_end - 0.382 * distance),
                "B": (impulse_end - 0.618 * distance, impulse_end - 0.500 * distance)}
    if direction == "SHORT" and impulse_end < impulse_start:
        return {"A": (impulse_end + 0.382 * distance, impulse_end + 0.500 * distance),
                "B": (impulse_end + 0.500 * distance, impulse_end + 0.618 * distance)}
    raise ValueError("impulse direction")


def confirmation_sequence(rejection: Bar, following: Sequence[Bar], direction: str, tick_size: float) -> bool:
    if not rejection_bar(rejection, direction) or not 1 <= len(following) <= 2:
        return False
    if direction == "LONG":
        return any(bar.close >= rejection.high + tick_size for bar in following)
    if direction == "SHORT":
        return any(bar.close <= rejection.low - tick_size for bar in following)
    raise ValueError("direction")


def breakout_bar(
    bar: Bar, *, direction: str, level: float, atr_h1: float,
    prior_bodies: Sequence[float], adx_now: float, adx_five_bars_ago: float,
) -> bool:
    g = bar_geometry(bar)
    if not prior_bodies or g["body_fraction"] is None:
        return False
    body_large = float(g["body"]) >= 1.20 * median(prior_bodies)
    adx_ok = adx_now >= adx_five_bars_ago - 3.0
    if direction == "LONG":
        return (bar.close >= level + 0.10 * atr_h1 and float(g["body_fraction"]) >= 0.60
                and body_large and float(g["close_long"]) >= 0.80 and adx_ok)
    if direction == "SHORT":
        return (bar.close <= level - 0.10 * atr_h1 and float(g["body_fraction"]) >= 0.60
                and body_large and float(g["close_short"]) >= 0.80 and adx_ok)
    raise ValueError("direction")


def brt_retest(bars: Sequence[Bar], *, direction: str, boundary: float, level_tol: float, atr_h1: float) -> bool:
    if not 1 <= len(bars) <= 12:
        return False
    touched = any(bar.low <= boundary + level_tol and bar.high >= boundary - level_tol for bar in bars)
    if direction == "LONG":
        accepted_back_inside = any(bar.close < boundary - 0.15 * atr_h1 for bar in bars)
    elif direction == "SHORT":
        accepted_back_inside = any(bar.close > boundary + 0.15 * atr_h1 for bar in bars)
    else:
        raise ValueError("direction")
    return touched and not accepted_back_inside


def fbr_reclaim(
    bars: Sequence[Bar], *, direction: str, boundary: float, atr_h1: float,
    tick_size: float, median_body_20: float,
) -> bool:
    """Evaluate breach + reclaim only; hold/follow-through remains a separate stage."""
    if not 1 <= len(bars) <= 4:
        return False
    if direction == "LONG":
        excursion = boundary - min(b.low for b in bars)
        reclaim = bars[-1]
        g = bar_geometry(reclaim)
        lower_wick = min(reclaim.open, reclaim.close) - reclaim.low
        return (0.10 * atr_h1 <= excursion <= 0.60 * atr_h1
                and reclaim.close >= boundary + tick_size
                and g["close_long"] is not None and float(g["close_long"]) >= 0.65
                and (lower_wick >= float(g["body"]) or float(g["body"]) >= 1.20 * median_body_20))
    if direction == "SHORT":
        excursion = max(b.high for b in bars) - boundary
        reclaim = bars[-1]
        g = bar_geometry(reclaim)
        upper_wick = reclaim.high - max(reclaim.open, reclaim.close)
        return (0.10 * atr_h1 <= excursion <= 0.60 * atr_h1
                and reclaim.close <= boundary - tick_size
                and g["close_short"] is not None and float(g["close_short"]) >= 0.65
                and (upper_wick >= float(g["body"]) or float(g["body"]) >= 1.20 * median_body_20))
    raise ValueError("direction")


def fbr_hold_and_confirm(
    reclaim: Bar, following: Sequence[Bar], *, direction: str, boundary: float,
    atr_m15: float, tick_size: float,
) -> bool:
    if not 1 <= len(following) <= 3:
        return False
    if direction == "LONG":
        held = all(bar.close >= boundary - 0.05 * atr_m15 for bar in following)
        confirmed = any(bar.close >= reclaim.high + tick_size for bar in following)
    elif direction == "SHORT":
        held = all(bar.close <= boundary + 0.05 * atr_m15 for bar in following)
        confirmed = any(bar.close <= reclaim.low - tick_size for bar in following)
    else:
        raise ValueError("direction")
    return held and confirmed


def rsr_location(price: float, lower: float, upper: float, direction: str) -> bool:
    if upper <= lower:
        return False
    width = upper - lower
    if direction == "LONG":
        return lower <= price <= lower + 0.15 * width
    if direction == "SHORT":
        return upper - 0.15 * width <= price <= upper
    raise ValueError("direction")


def moc_compression(
    compression: Sequence[Bar], prior_twenty: Sequence[Bar], *, direction: str,
    impulse_start: float, impulse_end: float, atr_h1: float, atr_m15: float,
) -> bool:
    if not 3 <= len(compression) <= 8 or len(prior_twenty) < 20:
        return False
    total_range = max(b.high for b in compression) - min(b.low for b in compression)
    if total_range > 0.75 * atr_h1:
        return False
    current_ranges = [b.high - b.low for b in compression]
    prior_ranges = [b.high - b.low for b in prior_twenty[-20:]]
    if median(current_ranges) > 0.70 * median(prior_ranges):
        return False
    distance = abs(impulse_end - impulse_start)
    if distance == 0:
        return False
    midpoint = (impulse_start + impulse_end) / 2
    if direction == "LONG" and impulse_end > impulse_start:
        closes_hold = all(b.close >= midpoint for b in compression)
        retracement = impulse_end - min(b.low for b in compression)
        slope = regression_slope([b.low for b in compression])
        slope_ok = slope is not None and slope >= -0.05 * atr_m15
    elif direction == "SHORT" and impulse_end < impulse_start:
        closes_hold = all(b.close <= midpoint for b in compression)
        retracement = max(b.high for b in compression) - impulse_end
        slope = regression_slope([b.high for b in compression])
        slope_ok = slope is not None and slope <= 0.05 * atr_m15
    else:
        raise ValueError("impulse direction")
    return closes_hold and retracement <= 0.382 * distance and slope_ok


def moc_trigger(
    compression: Sequence[Bar], trigger: Bar, *, direction: str, atr_m15: float,
    median_body_20: float, rsi14: float,
) -> bool:
    if not 3 <= len(compression) <= 8:
        return False
    g = bar_geometry(trigger)
    if g["body_fraction"] is None:
        return False
    if direction == "LONG":
        boundary = max(b.high for b in compression)
        return (trigger.close >= boundary + 0.05 * atr_m15
                and float(g["body_fraction"]) >= 0.60
                and float(g["body"]) >= 1.20 * median_body_20
                and float(g["close_long"]) >= 0.80 and 55 <= rsi14 <= 78)
    if direction == "SHORT":
        boundary = min(b.low for b in compression)
        return (trigger.close <= boundary - 0.05 * atr_m15
                and float(g["body_fraction"]) >= 0.60
                and float(g["body"]) >= 1.20 * median_body_20
                and float(g["close_short"]) >= 0.80 and 22 <= rsi14 <= 45)
    raise ValueError("direction")


def normalize_price(value: str | Decimal, tick: str | Decimal, mode: str) -> Decimal:
    value_d, tick_d = Decimal(value), Decimal(tick)
    if tick_d <= 0:
        raise ValueError("tick")
    units = value_d / tick_d
    rounding = ROUND_FLOOR if mode in {"DOWN", "BUY_STOP", "BUY_TARGET", "SELL_ENTRY"} else ROUND_CEILING
    return units.to_integral_value(rounding=rounding) * tick_d


def reward_risk(entry: Decimal, stop: Decimal, target: Decimal, direction: str) -> Decimal | None:
    if direction == "LONG":
        risk, reward = entry - stop, target - entry
    elif direction == "SHORT":
        risk, reward = stop - entry, entry - target
    else:
        raise ValueError("direction")
    return None if risk <= 0 or reward <= 0 else reward / risk


def mirror_bars(bars: Sequence[Bar], axis: float) -> list[Bar]:
    return [Bar(b.time, 2 * axis - b.open, 2 * axis - b.low, 2 * axis - b.high,
                2 * axis - b.close, b.tick_volume) for b in bars]


def correlation(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        raise ValueError("series")
    am, bm = sum(a) / len(a), sum(b) / len(b)
    numerator = sum((x - am) * (y - bm) for x, y in zip(a, b))
    denominator = sqrt(sum((x - am) ** 2 for x in a) * sum((y - bm) ** 2 for y in b))
    return 0.0 if denominator == 0 else numerator / denominator
