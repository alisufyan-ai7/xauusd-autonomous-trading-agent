from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from xauusd_agent.market import (
    AdmissionState,
    Bar,
    Quote,
    Timeframe,
    admit_market_snapshot,
    collect_snapshot,
)

DECISION = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
COUNTS = {Timeframe.H4: 300, Timeframe.H1: 500, Timeframe.M15: 1_000}


def series(timeframe: Timeframe, count: int) -> tuple[Bar, ...]:
    start = DECISION - count * timeframe.duration
    return tuple(
        Bar(
            symbol="XAUUSD",
            timeframe=timeframe,
            open_time=start + index * timeframe.duration,
            open=Decimal("2700.0") + Decimal(index) / Decimal(100),
            high=Decimal("2700.3") + Decimal(index) / Decimal(100),
            low=Decimal("2699.8") + Decimal(index) / Decimal(100),
            close=Decimal("2700.1") + Decimal(index) / Decimal(100),
            tick_volume=100 + index,
        )
        for index in range(count)
    )


class FixturePort:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def read_latest_quote(self, *, symbol: str, as_of: datetime) -> Quote:
        self.calls.append(("quote", symbol, as_of))
        return Quote(
            symbol="XAUUSD",
            broker_time=as_of,
            received_time=as_of,
            bid=Decimal("2700.100"),
            ask=Decimal("2700.120"),
            tick_size=Decimal("0.001"),
            sequence=7,
        )

    def read_completed_bars(
        self, *, symbol: str, timeframe: Timeframe, as_of: datetime, limit: int
    ) -> tuple[Bar, ...]:
        self.calls.append(("bars", symbol, timeframe, as_of, limit))
        return series(timeframe, limit)


def valid_snapshot():
    port = FixturePort()
    snapshot = collect_snapshot(
        port,
        decision_time=DECISION,
        account_symbol_known=True,
        precision_known=True,
        session_state_known=True,
    )
    return port, snapshot


def test_read_only_port_collects_exact_frozen_minima_and_admits() -> None:
    port, snapshot = valid_snapshot()
    decision = admit_market_snapshot(snapshot)
    assert decision.state is AdmissionState.READY
    assert [call[-1] for call in port.calls[1:]] == [300, 500, 1_000]
    with pytest.raises((FrozenInstanceError, AttributeError)):
        snapshot.quote.bid = Decimal("1")  # type: ignore[misc,union-attr]


def test_missing_and_stale_observations_fail_closed() -> None:
    _, snapshot = valid_snapshot()
    missing = replace(snapshot, quote=None, session_state_known=None)
    decision = admit_market_snapshot(missing)
    assert decision.state is AdmissionState.UNKNOWN
    assert decision.reasons == ("SESSION_STATE_UNKNOWN", "QUOTE_MISSING")

    assert snapshot.quote is not None
    stale_quote = replace(
        snapshot.quote,
        received_time=DECISION.replace(second=0) - Timeframe.M15.duration,
    )
    locked = admit_market_snapshot(replace(snapshot, quote=stale_quote))
    assert locked.state is AdmissionState.LOCK
    assert "QUOTE_STALE" in locked.reasons


def test_forming_or_missing_latest_completed_bar_is_never_admitted() -> None:
    _, snapshot = valid_snapshot()
    m15 = list(snapshot.bars[Timeframe.M15])
    m15[-1] = replace(m15[-1], open_time=DECISION)
    decision = admit_market_snapshot(
        replace(snapshot, bars={**snapshot.bars, Timeframe.M15: tuple(m15)})
    )
    assert decision.state is AdmissionState.LOCK
    assert "M15_FORMING_BAR_PRESENT" in decision.reasons
    assert "M15_LATEST_COMPLETED_BAR_MISSING" in decision.reasons


def test_non_boundary_decision_is_outside_frozen_m15_evaluation_window() -> None:
    _, snapshot = valid_snapshot()
    late = replace(snapshot, decision_time=DECISION.replace(minute=10))
    decision = admit_market_snapshot(late)
    assert decision.state is AdmissionState.LOCK
    assert "M15_DECISION_WINDOW_MISSED" in decision.reasons


def test_models_reject_non_utc_and_crossed_quote() -> None:
    with pytest.raises(ValueError, match="UTC"):
        Quote(
            "XAUUSD",
            datetime(2026, 1, 1),
            datetime(2026, 1, 1),
            Decimal("2"),
            Decimal("3"),
            Decimal("0.1"),
            0,
        )
    with pytest.raises(ValueError, match="incoherent"):
        Quote("XAUUSD", DECISION, DECISION, Decimal("3"), Decimal("2"), Decimal("0.1"), 0)
