from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from fractions import Fraction

from xauusd_agent.features import (
    adx,
    atr,
    bar_geometry,
    confirmed_swings,
    ema,
    regression_slope,
    rejection_bar,
    rsi,
    wilders,
)
from xauusd_agent.market import Bar, Timeframe

START = datetime(2026, 1, 1, tzinfo=UTC)


def bars(closes: list[Decimal]) -> tuple[Bar, ...]:
    result = []
    for index, close in enumerate(closes):
        wobble = Decimal(index % 5) / Decimal(100)
        opening = close - Decimal("0.08") + wobble
        result.append(
            Bar(
                "XAUUSD",
                Timeframe.M15,
                START + index * timedelta(minutes=15),
                opening,
                max(opening, close) + Decimal("0.20") + wobble,
                min(opening, close) - Decimal("0.17") - wobble,
                close,
                10 + index,
            )
        )
    return tuple(result)


def mirror(source: tuple[Bar, ...], axis: Decimal = Decimal("3000")) -> tuple[Bar, ...]:
    return tuple(
        Bar(
            bar.symbol,
            bar.timeframe,
            bar.open_time,
            2 * axis - bar.open,
            2 * axis - bar.low,
            2 * axis - bar.high,
            2 * axis - bar.close,
            bar.tick_volume,
        )
        for bar in source
    )


def test_ema_uses_arithmetic_seed_and_frozen_alpha() -> None:
    values = tuple(Decimal(value) for value in range(1, 9))
    assert ema(values, 3) == (
        None,
        None,
        Decimal(2),
        Decimal(3),
        Decimal(4),
        Decimal(5),
        Decimal(6),
        Decimal(7),
    )


def test_wilders_matches_independent_fraction_reference() -> None:
    values = tuple(Decimal(value) / Decimal(10) for value in (3, 8, 2, 7, 9, 4, 6, 1, 5))
    actual = wilders(values, 4)
    fraction_values = [Fraction(value) for value in values]
    current = sum(fraction_values[:4]) / 4
    expected: list[Fraction | None] = [None, None, None, current]
    for value in fraction_values[4:]:
        current = (3 * current + value) / 4
        expected.append(current)
    for left, right in zip(actual, expected, strict=True):
        if right is None:
            assert left is None
        else:
            assert left is not None
            reference = Decimal(right.numerator) / Decimal(right.denominator)
            assert abs(left - reference) < Decimal("1e-24")


def test_mirror_properties_hold_across_deterministic_fixtures() -> None:
    for seed in range(1, 16):
        closes = [
            Decimal("2700")
            + Decimal(index) * Decimal("0.11")
            + Decimal(((index * seed) % 9) - 4) * Decimal("0.03")
            for index in range(80)
        ]
        original = bars(closes)
        reflected = mirror(original)
        assert atr(original) == atr(reflected)
        original_rsi, reflected_rsi = rsi(original), rsi(reflected)
        for left, right in zip(original_rsi, reflected_rsi, strict=True):
            if left is not None and right is not None:
                assert abs(left + right - Decimal(100)) < Decimal("1e-22")
        _, plus, minus = adx(original)
        _, reflected_plus, reflected_minus = adx(reflected)
        for p, m, rp, rm in zip(plus, minus, reflected_plus, reflected_minus, strict=True):
            if p is not None:
                assert p == rm
                assert m == rp


def test_monotonic_rsi_reaches_one_hundred_without_division_error() -> None:
    source = bars([Decimal("2700") + Decimal(index) for index in range(30)])
    assert rsi(source)[-1] == Decimal(100)


def test_geometry_slope_and_confirmed_swings_are_objective() -> None:
    source = bars([Decimal(value) for value in (10, 11, 12, 14, 12, 11, 10)])
    highs, _ = confirmed_swings(source)
    assert highs == (3,)
    values = tuple(Decimal(value) for value in (1, 2, 3, 4))
    assert regression_slope(values) == Decimal(1)
    assert bar_geometry(source[0]).range > 0

    rejection = Bar(
        "XAUUSD",
        Timeframe.M15,
        START,
        Decimal("10.5"),
        Decimal("10.7"),
        Decimal("9.0"),
        Decimal("10.6"),
        1,
    )
    assert rejection_bar(rejection, "LONG")
