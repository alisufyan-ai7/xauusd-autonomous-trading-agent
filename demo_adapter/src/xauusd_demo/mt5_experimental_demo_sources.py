"""Actual MT5-quote-based conservative cost inputs for virtual DEMO v0.

No assertion that future gap/slippage or broker commission can be known from
a quote. These nonzero DEMO stress reserves are an EXPLICIT experimental
policy, not validated live-account transaction-cost statistics. Only exact
Exness Pro DEMO XAUUSD source is accepted and LIVE use is prohibited.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal
from typing import Any

from .envelope import DemoSafetyError
from .full_policy_broker_receipt import BoundAdverseCost
from .mt5_demo import _decimal, _record
from .prospective_cash_journal import ProspectiveDemoCashJournal
from .s2_order_sources import S2OrderSources


def _usd_up(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_CEILING)


class ExperimentalDemoCostSources:
    """Reobserve the same terminal on each strategy and pre-submit cycle."""

    def __init__(self, *, mt5: Any, cash_journal: ProspectiveDemoCashJournal) -> None:
        self._mt5 = mt5
        self._cash_journal = cash_journal

    def current_sources(self, now: datetime) -> S2OrderSources:
        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise DemoSafetyError("experimental DEMO source clock not UTC")
        mt5 = self._mt5
        term = _record(mt5.terminal_info(), "terminal")
        account = _record(mt5.account_info(), "account")
        if (
            term.get("connected") is not True
            or account.get("trade_mode") != 0
            or account.get("company") != "Exness Technologies Ltd"
            or account.get("server") != "Exness-MT5Trial15"
            or account.get("currency") != "USD"
            or type(account.get("login")) is not int
        ):
            raise DemoSafetyError("experimental source cannot leave Exness Pro DEMO")
        quote = _record(mt5.symbol_info_tick("XAUUSD"), "tick")
        bid = _decimal(quote.get("bid"), "bid")
        ask = _decimal(quote.get("ask"), "ask")
        msc = quote.get("time_msc")
        if (
            type(msc) is not int or msc <= 0
            or bid <= 0 or ask <= bid
        ):
            raise DemoSafetyError("unqualified DEMO broker spread")
        tick_time = datetime.fromtimestamp(msc / 1000, UTC)
        if tick_time > now + timedelta(seconds=1) or now-tick_time > timedelta(seconds=2):
            raise DemoSafetyError("stale broker spread cannot calibrate risk")
        # Actual 0.01-lot broker USD cash impact of paying the current spread,
        # NOT a guessed gold contract multiplier.
        spread_loss = mt5.order_calc_profit(
            mt5.ORDER_TYPE_BUY, "XAUUSD", 0.01, float(ask), float(bid)
        )
        if spread_loss is None:
            raise DemoSafetyError("broker spread dollar loss unavailable")
        impact = abs(_decimal(spread_loss, "broker spread cash"))
        if impact <= 0 or impact > Decimal("20"):
            raise DemoSafetyError("broker spread price/cash data abnormal")
        # DEMO-only research allowances: at least USD1 commission, USD1
        # overnight reserve, USD1 slippage and USD3 adverse gap. Larger
        # observed spreads scale each stressed component conservatively.
        costs = BoundAdverseCost(
            calibration_id="DEMO_V0_CONSERVATIVE_BROKER_SPREAD_PROXY",
            evidence_sha256=hashlib.sha256(
                f"EXNESS_PRO_DEMO_ONLY|{account['login']}|XAUUSD|{msc}|"
                f"{bid}|{ask}|{impact}".encode("ascii")
            ).hexdigest(),
            commission_roundtrip_usd=_usd_up(max(Decimal("1"), impact * 2)),
            swap_reserve_usd=_usd_up(max(Decimal("1"), impact * 2)),
            slippage_reserve_usd=_usd_up(max(Decimal("1"), impact * 4)),
            gap_reserve_usd=_usd_up(max(Decimal("3"), impact * 8)),
        )
        return S2OrderSources(
            cash_journal=self._cash_journal,
            costs=costs,
            expected_cost_sha256=costs.digest(),
            official_snapshots=(),
            session_verified_through_utc=None,
            shock_locked=False,
            normalized=True,
            source_mode="EXPERIMENTAL_DEMO_NY_PROXY",
        )
