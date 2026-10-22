"""Read-only seven-timeframe Exness XAUUSD observer; never a trading adapter.

Builds on existing MT5ReadOnlyAdapter guard. copy_rates_from_pos asks
for closed bars (start_pos=1), then validates closure against a pinned
UTC observation instant. Does not change terminal settings, switch accounts,
check orders, transmit orders or fetch news.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from types import MappingProxyType
from typing import Any

from xauusd_agent.broker.mt5_readonly import (
    MT5ReadOnlyAdapter,
    MT5ReadOnlyError,
    _decimal,
    _utc_from_epoch,
)
from xauusd_agent.features.v2_market_context import (
    ContextBar,
    ContextTimeframe,
    from_existing_core_bar,
)
from xauusd_agent.market.models import Timeframe, _require_utc


class MT5ExtendedReadOnlyAdapter(MT5ReadOnlyAdapter):
    """Seven-frame read-only bar data with explicit closure/identity checks."""

    def __init__(
        self,
        *,
        admitted_fingerprint_sha256: str,
        admitted_server: str,
        admitted_company: str,
        module: Any | None = None,
    ) -> None:
        super().__init__(module)
        if (
            len(admitted_fingerprint_sha256) != 64
            or any(c not in "0123456789abcdef" for c in admitted_fingerprint_sha256)
            or not admitted_server
            or not admitted_company
        ):
            raise ValueError("exact sanitized admitted DEMO identity is required")
        self._admitted_fingerprint = admitted_fingerprint_sha256
        self._admitted_server = admitted_server
        self._admitted_company = admitted_company

    def _guard_demo_identity(self) -> None:
        self._guard()
        account = self.observe_account()
        fp = account.fingerprint
        # Existing read-only DTO uses str(value or ""), which maps the
        # valid MT5 DEMO enum 0 to empty string; recheck the raw enum
        # explicitly instead of silently downgrading account-type binding.
        raw_mode = self._account().get("trade_mode")
        mode_is_demo = (
            type(raw_mode) is int and raw_mode == 0
        ) or raw_mode == "DEMO"
        if (
            fp.account_id_sha256 != self._admitted_fingerprint
            or fp.server != self._admitted_server
            or fp.broker != self._admitted_company
            or fp.currency != "USD"
            or not mode_is_demo
        ):
            raise MT5ReadOnlyError("DEMO account identity mismatch; fail closed")

    _additional: Mapping[ContextTimeframe, str] = MappingProxyType(
        {
            ContextTimeframe.W1: "TIMEFRAME_W1",
            ContextTimeframe.D1: "TIMEFRAME_D1",
            ContextTimeframe.M5: "TIMEFRAME_M5",
            ContextTimeframe.M1: "TIMEFRAME_M1",
        }
    )
    _existing: Mapping[ContextTimeframe, Timeframe] = MappingProxyType(
        {
            ContextTimeframe.H4: Timeframe.H4,
            ContextTimeframe.H1: Timeframe.H1,
            ContextTimeframe.M15: Timeframe.M15,
        }
    )

    def read_context_bars(
        self, *, timeframe: ContextTimeframe, as_of: datetime, limit: int
    ) -> tuple[ContextBar, ...]:
        _require_utc(as_of, "as_of")
        if limit < 1 or limit > 20_000:
            raise MT5ReadOnlyError("context bar limit outside fixed safe range")
        self._guard_demo_identity()  # Account + API protection rechecked.
        if timeframe in self._existing:
            converted = tuple(
                from_existing_core_bar(bar)
                for bar in self.read_completed_bars(
                    symbol="XAUUSD",
                    timeframe=self._existing[timeframe],
                    as_of=as_of,
                    limit=limit,
                )
            )
        else:
            name = self._additional.get(timeframe)
            if name is None:
                raise MT5ReadOnlyError("unsupported context timeframe")
            api = self._mt5
            if api is None:
                raise MT5ReadOnlyError("MT5 is not initialized")
            const = getattr(api, name, None)
            if const is None:
                raise MT5ReadOnlyError(f"{name} unsupported by current MT5 terminal")
            rows: Any = api.copy_rates_from_pos("XAUUSD", const, 1, limit)
            if rows is None:
                raise MT5ReadOnlyError(
                    f"read-only {timeframe.value} rates failed: {api.last_error()}"
                )
            converted = tuple(
                ContextBar(
                    symbol="XAUUSD",
                    timeframe=timeframe,
                    open_time=_utc_from_epoch(row["time"]),
                    open=_decimal(row["open"], "bar open"),
                    high=_decimal(row["high"], "bar high"),
                    low=_decimal(row["low"], "bar low"),
                    close=_decimal(row["close"], "bar close"),
                    tick_volume=int(row["tick_volume"]),
                )
                for row in rows
            )
        # Account can change externally during read. The second guard verifies
        # disabled trading again; identity binding requires a separate check.
        self._guard_demo_identity()
        if any(bar.close_time > as_of for bar in converted):
            raise MT5ReadOnlyError("context data contains incomplete or future candles")
        if any(a.open_time >= z.open_time for a, z in zip(
            converted, converted[1:], strict=False
        )):
            raise MT5ReadOnlyError("context data not monotonically ordered")
        return converted

    def read_seven_frames(
        self, *, as_of: datetime, limits: Mapping[ContextTimeframe, int]
    ) -> Mapping[ContextTimeframe, Sequence[ContextBar]]:
        _require_utc(as_of, "as_of")
        if set(limits) != set(ContextTimeframe):
            raise MT5ReadOnlyError("all seven context timeframes must be requested")
        batch = {
            timeframe: self.read_context_bars(
                timeframe=timeframe, as_of=as_of, limit=limits[timeframe]
            )
            for timeframe in ContextTimeframe
        }
        self._guard_demo_identity()
        return MappingProxyType(batch)
