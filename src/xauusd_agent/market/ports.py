"""Narrow read-only market-data port.

The protocol intentionally cannot mutate MT5, submit orders, inspect accounts,
or change broker state.  Concrete adapters live outside the production core
and are not included in this execution-disabled package.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from .admission import DEFAULT_ADMISSION_POLICY, AdmissionPolicy, MarketSnapshot
from .models import Bar, Quote, Timeframe, _require_utc


@runtime_checkable
class ReadOnlyMarketDataPort(Protocol):
    """Only capabilities needed to observe XAUUSD at one decision instant."""

    def read_latest_quote(self, *, symbol: str, as_of: datetime) -> Quote | None: ...

    def read_completed_bars(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        as_of: datetime,
        limit: int,
    ) -> Sequence[Bar]: ...


def collect_snapshot(
    port: ReadOnlyMarketDataPort,
    *,
    decision_time: datetime,
    account_symbol_known: bool | None,
    precision_known: bool | None,
    session_state_known: bool | None,
    known_breaks: Mapping[Timeframe, frozenset[tuple[datetime, datetime]]] | None = None,
    policy: AdmissionPolicy = DEFAULT_ADMISSION_POLICY,
) -> MarketSnapshot:
    """Collect and freeze one information set through the read-only port."""
    _require_utc(decision_time, "decision_time")
    assert policy.minima is not None
    quote = port.read_latest_quote(symbol="XAUUSD", as_of=decision_time)
    ordered_timeframes = (Timeframe.H4, Timeframe.H1, Timeframe.M15)
    bars = {
        timeframe: tuple(
            port.read_completed_bars(
                symbol="XAUUSD",
                timeframe=timeframe,
                as_of=decision_time,
                limit=policy.minima[timeframe],
            )
        )
        for timeframe in ordered_timeframes
    }
    return MarketSnapshot(
        decision_time=decision_time,
        quote=quote,
        bars=bars,
        known_breaks=known_breaks or {},
        account_symbol_known=account_symbol_known,
        precision_known=precision_known,
        session_state_known=session_state_known,
    )
