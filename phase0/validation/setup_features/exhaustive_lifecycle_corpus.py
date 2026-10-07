"""Full-count synthetic OHLC and advisory lifecycle corpus for Gate 0.

This module is deliberately offline and immutable-by-construction.  It builds
300 completed H4, 500 completed H1 and 1,000 completed M15 bars for each of the
five setup families in both directions, binds each golden candidate's raw bars
into those histories, and enumerates every frozen cancellation condition plus
the non-trading FILLED terminal observation.  It cannot place or manage an
order and it makes no historical-performance claim.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from feature_oracle import Bar, completed_bars, validate_series
from registered_family_corpus import _long_passes, mirror_inputs


FAMILIES = ("TPB", "BRT", "FBR", "RSR", "MOC")
DIRECTIONS = ("LONG", "SHORT")
COUNTS = {"H4": 300, "H1": 500, "M15": 1000}
PERIODS = {"H4": 14_400, "H1": 3_600, "M15": 900}
DECISION_TIME = 20_000_000
CANCELLATION_CONDITIONS = (
    "COMMON_FILTER_FAILED",
    "REGIME_LOST",
    "STRUCTURE_INVALIDATED",
    "PENDING_EXPIRED",
    "EVENT_LOCK",
    "PRICE_ALREADY_REACHED_TARGET",
    "QUOTE_STALE",
    "SPREAD_BLOCKED",
)
TERMINAL_EVENTS = CANCELLATION_CONDITIONS + ("FILLED",)


@dataclass(frozen=True)
class FullHistoryFixture:
    fixture_id: str
    family: str
    direction: str
    decision_time: int
    h4: tuple[Bar, ...]
    h1: tuple[Bar, ...]
    m15: tuple[Bar, ...]
    evaluator: Callable[..., Any]
    evaluator_inputs: dict[str, Any]


@dataclass(frozen=True)
class AdvisoryLifecycle:
    fixture_id: str
    state: str = "OBSERVED"
    last_event_time: int = -1
    terminal_reason: str | None = None


@dataclass(frozen=True)
class LifecyclePath:
    path_id: str
    fixture_id: str
    family: str
    direction: str
    terminal_event: str
    expected_state: str
    expected_reason: str


def _base_series(count: int, period: int, direction: str) -> list[Bar]:
    sign = 1.0 if direction == "LONG" else -1.0
    start = DECISION_TIME - count * period
    bars: list[Bar] = []
    for index in range(count):
        centre = 110.0 + sign * index * 0.01
        open_price = centre - sign * 0.05
        close = centre + sign * 0.05
        bars.append(Bar(start + index * period, open_price,
                        max(open_price, close) + 0.20,
                        min(open_price, close) - 0.20, close, 100 + index % 17))
    return bars


def _rebase_tail(history: list[Bar], source: Sequence[Bar], period: int) -> tuple[list[Bar], list[Bar]]:
    if not source or len(source) > len(history):
        raise ValueError("tail length")
    start = history[-len(source)].time
    rebound = [Bar(start + index * period, bar.open, bar.high, bar.low,
                   bar.close, bar.tick_volume)
               for index, bar in enumerate(source)]
    return history[:-len(source)] + rebound, rebound


def _bind_candidate(family: str, direction: str) -> FullHistoryFixture:
    evaluator, original = _long_passes()[family]
    inputs = deepcopy(original if direction == "LONG" else mirror_inputs(original))
    h4 = _base_series(COUNTS["H4"], PERIODS["H4"], direction)
    h1 = _base_series(COUNTS["H1"], PERIODS["H1"], direction)
    m15 = _base_series(COUNTS["M15"], PERIODS["M15"], direction)

    if family == "TPB":
        m15, rebound = _rebase_tail(m15, [inputs["rejection"], *inputs["following"]], PERIODS["M15"])
        inputs["rejection"], inputs["following"] = rebound[0], rebound[1:]
    elif family == "BRT":
        h1, rebound_h1 = _rebase_tail(h1, [inputs["breakout"], *inputs["retest_h1"]], PERIODS["H1"])
        inputs["breakout"], inputs["retest_h1"] = rebound_h1[0], rebound_h1[1:]
        m15, rebound_m15 = _rebase_tail(m15, [inputs["rejection"], *inputs["following"]], PERIODS["M15"])
        inputs["rejection"], inputs["following"] = rebound_m15[0], rebound_m15[1:]
    elif family == "FBR":
        source = [*inputs["prior_twenty"], *inputs["breach_to_reclaim"], *inputs["following"]]
        m15, rebound = _rebase_tail(m15, source, PERIODS["M15"])
        p, b = len(inputs["prior_twenty"]), len(inputs["breach_to_reclaim"])
        inputs["prior_twenty"] = rebound[:p]
        inputs["breach_to_reclaim"] = rebound[p:p + b]
        inputs["following"] = rebound[p + b:]
    elif family == "RSR":
        h1, rebound_h1 = _rebase_tail(h1, inputs["h1_bars"], PERIODS["H1"])
        inputs["h1_bars"] = h1
        m15, rebound_m15 = _rebase_tail(m15, [inputs["rejection"], *inputs["following"]], PERIODS["M15"])
        inputs["rejection"], inputs["following"] = rebound_m15[0], rebound_m15[1:]
        if tuple(rebound_h1) != tuple(h1[-len(rebound_h1):]):
            raise AssertionError("RSR binding")
    elif family == "MOC":
        source = [*inputs["prior_twenty"], *inputs["compression"], inputs["trigger"]]
        m15, rebound = _rebase_tail(m15, source, PERIODS["M15"])
        p, c = len(inputs["prior_twenty"]), len(inputs["compression"])
        inputs["prior_twenty"] = rebound[:p]
        inputs["compression"] = rebound[p:p + c]
        inputs["trigger"] = rebound[-1]
    else:
        raise ValueError("family")

    return FullHistoryFixture(
        f"{family}-FULL-{direction}", family, direction, DECISION_TIME,
        tuple(h4), tuple(h1), tuple(m15), evaluator, inputs,
    )


def build_fixtures() -> tuple[FullHistoryFixture, ...]:
    return tuple(_bind_candidate(family, direction)
                 for family in FAMILIES for direction in DIRECTIONS)


def advance_lifecycle(state: AdvisoryLifecycle, event: str, event_time: int) -> AdvisoryLifecycle:
    if event_time <= state.last_event_time:
        raise ValueError("non-monotonic lifecycle event")
    if state.state in {"CANCELLED", "EXPIRED", "CONSUMED"}:
        raise ValueError("terminal lifecycle cannot reactivate")
    if event == "PROPOSE" and state.state == "OBSERVED":
        return AdvisoryLifecycle(state.fixture_id, "PROPOSED", event_time)
    if event == "RESERVE" and state.state == "PROPOSED":
        return AdvisoryLifecycle(state.fixture_id, "PENDING", event_time)
    if event in CANCELLATION_CONDITIONS and state.state in {"PROPOSED", "PENDING"}:
        terminal = "EXPIRED" if event == "PENDING_EXPIRED" else "CANCELLED"
        return AdvisoryLifecycle(state.fixture_id, terminal, event_time, event)
    if event == "FILLED" and state.state == "PENDING":
        return AdvisoryLifecycle(state.fixture_id, "CONSUMED", event_time, "FILLED")
    raise ValueError("invalid lifecycle transition")


def lifecycle_paths(fixtures: Sequence[FullHistoryFixture]) -> tuple[LifecyclePath, ...]:
    paths: list[LifecyclePath] = []
    for fixture in fixtures:
        for event in TERMINAL_EVENTS:
            paths.append(LifecyclePath(
                f"{fixture.fixture_id}-{event}", fixture.fixture_id,
                fixture.family, fixture.direction, event,
                "EXPIRED" if event == "PENDING_EXPIRED" else "CONSUMED" if event == "FILLED" else "CANCELLED",
                event,
            ))
    return tuple(paths)


def run_path(path: LifecyclePath) -> AdvisoryLifecycle:
    state = AdvisoryLifecycle(path.fixture_id)
    state = advance_lifecycle(state, "PROPOSE", 1)
    state = advance_lifecycle(state, "RESERVE", 2)
    return advance_lifecycle(state, path.terminal_event, 3)


def fixture_reasons(fixture: FullHistoryFixture) -> tuple[str, ...]:
    reasons: list[str] = []
    for name, bars in (("H4", fixture.h4), ("H1", fixture.h1), ("M15", fixture.m15)):
        if len(bars) != COUNTS[name]:
            reasons.append(f"{name}_COUNT_INVALID")
        clear, reason = validate_series(
            bars, decision_time=fixture.decision_time,
            period_seconds=PERIODS[name], minimum=COUNTS[name],
        )
        if not clear:
            reasons.append(f"{name}_{reason}")
        if len(completed_bars(bars, fixture.decision_time, PERIODS[name])) != COUNTS[name]:
            reasons.append(f"{name}_INCOMPLETE")
    candidate = fixture.evaluator(**deepcopy(fixture.evaluator_inputs))
    if (candidate.state, candidate.reason) != ("PROPOSED", "GOLDEN_SLICE_PASS"):
        reasons.append("CANDIDATE_NOT_PROPOSED")
    return tuple(dict.fromkeys(reasons))


def fixture_digest(fixture: FullHistoryFixture) -> str:
    def rows(bars: Sequence[Bar]) -> list[list[Any]]:
        return [[bar.time, bar.open, bar.high, bar.low, bar.close, bar.tick_volume]
                for bar in bars]
    body = {
        "fixture_id": fixture.fixture_id,
        "family": fixture.family,
        "direction": fixture.direction,
        "decision_time": fixture.decision_time,
        "h4": rows(fixture.h4), "h1": rows(fixture.h1), "m15": rows(fixture.m15),
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


FIXTURES = build_fixtures()
LIFECYCLE_PATHS = lifecycle_paths(FIXTURES)
