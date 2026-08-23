"""Registered synthetic raw-OHLC cases for the five frozen setup families."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

from family_golden_oracle import (
    SafetyState, evaluate_brt, evaluate_fbr, evaluate_moc, evaluate_rsr,
    evaluate_tpb,
)
from feature_oracle import Bar, mirror_bars


@dataclass(frozen=True)
class RegisteredCase:
    case_id: str
    family: str
    direction: str
    category: str
    evaluator: Callable[..., Any]
    inputs: dict[str, Any]
    expected_state: str
    expected_reason: str


def raw_h1_range(cycles: int = 4) -> list[Bar]:
    pattern = [110, 115, 119, 115, 110, 105, 101, 105]
    return [Bar(i * 3600, c, c + 1, c - 1, c, 10)
            for i, c in enumerate(pattern * cycles)]


def _long_passes() -> dict[str, tuple[Callable[..., Any], dict[str, Any]]]:
    prior = [Bar(i * 900, 112, 114, 110, 112) for i in range(20)]
    compression = [Bar((20 + i) * 900, 117.5, 118.5, 116.8 + .1 * i, 117.8)
                   for i in range(3)]
    return {
        "TPB": (evaluate_tpb, dict(
            direction="LONG", regime="UP_TREND", impulse_start=100, impulse_end=120,
            location_level=111, level_tol=.1,
            rejection=Bar(0, 111, 112.2, 110, 111.8),
            following=[Bar(900, 111.8, 112.5, 111, 112.3)],
            tick_size=.1, stop_buffer=.2, tp1=120, final=125,
        )),
        "BRT": (evaluate_brt, dict(
            direction="LONG", regime="UP_TREND", boundary=100, atr_h1=10,
            level_tol=.25, breakout=Bar(0, 98.5, 102.5, 98, 102),
            prior_bodies=[1] * 20, adx_now=20, adx_five_bars_ago=22,
            retest_h1=[Bar(3600, 101, 102, 99.8, 100.5)],
            rejection=Bar(4500, 100.5, 102, 99, 101.5),
            following=[Bar(5400, 101.5, 103, 101, 102.2)],
            tick_size=.1, stop_buffer=.5, tp1=112, final=115,
        )),
        "FBR": (evaluate_fbr, dict(
            direction="LONG", regime="RANGE", boundary=100, atr_h1=10, atr_m15=2,
            tick_size=.1,
            prior_twenty=[Bar(i * 900, 100, 101, 99, 100.5) for i in range(20)],
            breach_to_reclaim=[Bar(20 * 900, 100, 100.2, 98, 99),
                               Bar(21 * 900, 99, 101, 98.5, 100.6)],
            following=[Bar(22 * 900, 100.5, 102, 100, 101.2)],
            stop_buffer=.5, tp1=110, final=115,
        )),
        "RSR": (evaluate_rsr, dict(
            direction="LONG", h1_bars=raw_h1_range(), atr_h1=10, level_tol=.5,
            rejection=Bar(32 * 3600, 101, 102, 100, 101.8),
            following=[Bar(32 * 3600 + 900, 101.8, 102.5, 101, 102.2)],
            tick_size=.1, stop_buffer=.2,
        )),
        "MOC": (evaluate_moc, dict(
            direction="LONG", regime="UP_TREND", impulse_start=100, impulse_end=120,
            atr_h1=10, atr_m15=2, prior_twenty=prior, compression=compression,
            trigger=Bar(23 * 900, 118, 120, 117.8, 119.8), rsi14=55,
            quote_price=119.9, stop_buffer=.2, tp1=125, final=130,
        )),
    }


PRICE_FIELDS = {"impulse_start", "impulse_end", "location_level", "boundary",
                "quote_price", "tp1", "final"}
BAR_FIELDS = {"breakout", "rejection", "trigger"}
BAR_LIST_FIELDS = {"following", "retest_h1", "prior_twenty", "breach_to_reclaim",
                   "h1_bars", "compression"}


def mirror_inputs(inputs: dict[str, Any], axis: float = 110) -> dict[str, Any]:
    mirrored = deepcopy(inputs)
    mirrored["direction"] = "SHORT"
    if mirrored.get("regime") == "UP_TREND":
        mirrored["regime"] = "DOWN_TREND"
    for field in PRICE_FIELDS & mirrored.keys():
        mirrored[field] = 2 * axis - mirrored[field]
    for field in BAR_FIELDS & mirrored.keys():
        mirrored[field] = mirror_bars([mirrored[field]], axis)[0]
    for field in BAR_LIST_FIELDS & mirrored.keys():
        mirrored[field] = mirror_bars(mirrored[field], axis)
    if "rsi14" in mirrored:
        mirrored["rsi14"] = 100 - mirrored["rsi14"]
    return mirrored


def _case(case_id: str, family: str, category: str, evaluator: Callable[..., Any],
          inputs: dict[str, Any], state: str = "PROPOSED",
          reason: str = "GOLDEN_SLICE_PASS") -> RegisteredCase:
    return RegisteredCase(case_id, family, inputs["direction"], category, evaluator,
                          inputs, state, reason)


def registered_cases() -> tuple[RegisteredCase, ...]:
    """Return the immutable case registry: 10 passes and 25 negatives."""
    cases: list[RegisteredCase] = []
    passes = _long_passes()
    for family, (evaluator, inputs) in passes.items():
        cases.append(_case(f"{family}-RAW-PASS-L", family, "PASS", evaluator, inputs))
        cases.append(_case(f"{family}-RAW-PASS-S", family, "MIRROR_PASS", evaluator,
                           mirror_inputs(inputs)))

    mutations: dict[str, tuple[tuple[str, dict[str, Any], str], ...]] = {
        "TPB": (
            ("REGIME", {"regime": "DOWN_TREND"}, "REGIME_MISMATCH"),
            ("ZONE", {"location_level": 999}, "ZONE_OR_LOCATION_INVALID"),
            ("CONFIRM", {"following": []}, "CONFIRMATION_MISSING"),
            ("RR", {"tp1": 115, "final": 119}, "INSUFFICIENT_RR"),
            ("SAFETY", {"safety": SafetyState(event_clear=False)}, "EVENT_BLOCKED"),
        ),
        "BRT": (
            ("REGIME", {"regime": "DOWN_TREND"}, "REGIME_MISMATCH"),
            ("BREAKOUT", {"adx_now": 18.999, "adx_five_bars_ago": 22}, "BREAKOUT_INVALID"),
            ("RETEST", {"retest_h1": [Bar(i * 3600, 101, 102, 99.8, 100.5) for i in range(13)]}, "RETEST_INVALID"),
            ("CONFIRM", {"following": []}, "CONFIRMATION_MISSING"),
            ("SAFETY", {"safety": SafetyState(spread_clear=False)}, "SPREAD_BLOCKED"),
        ),
        "FBR": (
            ("REGIME", {"regime": "UNCLASSIFIED"}, "REGIME_MISMATCH"),
            ("RECLAIM", {"breach_to_reclaim": [Bar(20 * 900, 100, 100.2, 98, 99.9)]}, "RECLAIM_INVALID"),
            ("HOLD", {"following": [Bar(22 * 900, 100, 101.3, 99, 99.89)]}, "HOLD_OR_CONFIRMATION_INVALID"),
            ("RR", {"tp1": 105, "final": 108}, "INSUFFICIENT_RR"),
            ("SAFETY", {"safety": SafetyState(volatility_clear=False)}, "VOLATILITY_BLOCKED"),
        ),
        "RSR": (
            ("RANGE", {"h1_bars": raw_h1_range(2)}, "RANGE_OR_LOCATION_INVALID"),
            ("LOCATION", {"rejection": Bar(32 * 3600, 110, 111, 109, 110)}, "RANGE_OR_LOCATION_INVALID"),
            ("CONFIRM", {"following": []}, "CONFIRMATION_MISSING"),
            ("RR", {"stop_buffer": 20}, "INSUFFICIENT_RR"),
            ("SAFETY", {"safety": SafetyState(exposure_clear=False)}, "EXPOSURE_BLOCKED"),
        ),
        "MOC": (
            ("REGIME", {"regime": "DOWN_TREND"}, "REGIME_MISMATCH"),
            ("COMPRESSION", {"compression": [Bar(i, 117, 118, 116, 117) for i in range(2)]}, "COMPRESSION_INVALID"),
            ("TRIGGER", {"rsi14": 54.999}, "TRIGGER_INVALID"),
            ("CHASE", {"quote_price": 120.101}, "QUOTE_CHASE_BLOCKED"),
            ("SAFETY", {"safety": SafetyState(session_clear=False)}, "SESSION_BLOCKED"),
        ),
    }
    for family, family_mutations in mutations.items():
        evaluator, base = passes[family]
        for suffix, changes, reason in family_mutations:
            inputs = deepcopy(base)
            inputs.update(changes)
            cases.append(_case(f"{family}-RAW-NO-{suffix}", family, "NEGATIVE", evaluator,
                               inputs, "NO_TRADE", reason))
    return tuple(cases)


CASES = registered_cases()
