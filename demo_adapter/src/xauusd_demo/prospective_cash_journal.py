"""Prospective EXNESS DEMO-only cash baseline and high-water journal.

This module *cannot* send orders. It does not infer historical equity from a
today-only account snapshot. It admits a new campaign only if all broker
history is complete, there are no historical trading deals, zero exposure,
and the opening cash balance agrees with equity. Existing campaigns require
broker balance to reconcile to every observed deal on each evaluation.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Final

from .envelope import DemoSafetyError

MAGIC: Final = 260101
CURRENCY: Final = "USD"
DEAL_TRADES: Final = frozenset({"BUY", "SELL"})
DEAL_BALANCE: Final = frozenset({"BALANCE", "CREDIT"})


@dataclass(frozen=True)
class CashDeal:
    deal_id: str
    time_utc: datetime
    kind: str
    amount: Decimal
    magic: int

    def __post_init__(self) -> None:
        if (
            not self.deal_id or self.time_utc.tzinfo is None
            or self.time_utc.utcoffset() is None
            or not self.amount.is_finite()
        ):
            raise DemoSafetyError("incomplete broker deal evidence")


@dataclass(frozen=True)
class CashObservation:
    observed_utc: datetime
    balance: Decimal
    equity: Decimal
    account_currency: str
    account_fingerprint: str
    broker_history_complete: bool
    positions_count: int
    orders_count: int
    broker_deals: tuple[CashDeal, ...]

    def __post_init__(self) -> None:
        if self.observed_utc.tzinfo is None or self.observed_utc.utcoffset() is None:
            raise DemoSafetyError("cash observation must have UTC timestamp")
        offset = self.observed_utc.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise DemoSafetyError("cash observation not UTC")
        if not self.balance.is_finite() or not self.equity.is_finite():
            raise DemoSafetyError("nonfinite account cash")


@dataclass(frozen=True)
class CashRiskBaseline:
    admitted: bool
    reason: str
    initial_equity: Decimal | None = None
    day_start_equity: Decimal | None = None
    week_start_equity: Decimal | None = None
    normalized_high_water: Decimal | None = None
    observed_day_loss: Decimal | None = None
    observed_week_loss: Decimal | None = None
    observed_drawdown: Decimal | None = None
    loss_equivalent_streak: Decimal | None = None
    no_order_authority: bool = True


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _digest(deals: tuple[CashDeal, ...]) -> str:
    payload = [
        [d.deal_id, _utc(d.time_utc), d.kind, str(d.amount), d.magic]
        for d in sorted(deals, key=lambda x: x.deal_id)
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _week_key(t: datetime) -> str:
    year, week, _day = t.isocalendar()
    return f"{year:04d}-W{week:02d}"


def _loss_equivalent_streak(deals: tuple[CashDeal, ...]) -> Decimal:
    """Conservative durable consecutive negative broker-deal cash proxy.

    Exit/trade grouping is a future improvement. This never rewrites account
    P/L or overrides the Full Policy A streak/day/week/drawdown gates. A
    non-trading deposit/credit never resets a losing trading streak.
    """
    streak = 0
    for deal in sorted(deals, key=lambda d: (d.time_utc, d.deal_id)):
        if deal.kind not in DEAL_TRADES:
            continue
        if deal.amount < 0:
            streak += 1
        elif deal.amount > 0:
            streak = 0
    return Decimal(streak)


class ProspectiveDemoCashJournal:
    """Single-writer, conservative DEMO campaign cash journal.

    A past deal at inception is a permanent nonadmission; no account's
    historical drawdown is silently reset to an artificial zero.
    """

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, isolation_level=None)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("PRAGMA busy_timeout=250")
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS cash_campaign (
             id INTEGER PRIMARY KEY CHECK(id=1),
             fingerprint TEXT NOT NULL, initial_balance TEXT NOT NULL,
             initial_equity TEXT NOT NULL, start_utc TEXT NOT NULL,
             last_utc TEXT NOT NULL, last_balance TEXT NOT NULL,
             high_water TEXT NOT NULL, day_key TEXT NOT NULL,
             day_start TEXT NOT NULL, week_key TEXT NOT NULL,
             week_start TEXT NOT NULL, deal_digest TEXT NOT NULL,
             trade_count INTEGER NOT NULL, paused INTEGER NOT NULL
            ) STRICT"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS seen_cash_deals (
             deal_id TEXT PRIMARY KEY, time_utc TEXT NOT NULL,
             kind TEXT NOT NULL, amount TEXT NOT NULL, magic INTEGER NOT NULL
            ) STRICT"""
        )

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> ProspectiveDemoCashJournal:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _check(self, o: CashObservation) -> None:
        if (
            o.account_currency != CURRENCY or len(o.account_fingerprint) != 64
            or o.broker_history_complete is not True
            or o.balance <= 0 or o.equity <= 0
            or o.positions_count != 0 or o.orders_count != 0
        ):
            raise DemoSafetyError("broker flat USD history cannot be proven")
        identifiers = [d.deal_id for d in o.broker_deals]
        if len(set(identifiers)) != len(identifiers):
            raise DemoSafetyError("duplicate broker deal identifiers")
        if any(d.time_utc > o.observed_utc for d in o.broker_deals):
            raise DemoSafetyError("future broker deal timestamp")

    def observe(self, o: CashObservation) -> CashRiskBaseline:
        """Returns cash baseline only; NEVER order execution permission."""
        self._check(o)
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute(
                "SELECT * FROM cash_campaign WHERE id=1"
            ).fetchone()
            if row is None:
                # No previous trading deals means baseline inception was not
                # obscured by an earlier trading drawdown.
                if any(d.kind in DEAL_TRADES for d in o.broker_deals):
                    raise DemoSafetyError("prior account trading history not admitted")
                if any(d.kind not in DEAL_BALANCE for d in o.broker_deals):
                    raise DemoSafetyError("unclassified historical cash event")
                if o.balance != o.equity:
                    raise DemoSafetyError("nonflat unrealized cash baseline")
                self.conn.execute(
                    """INSERT INTO cash_campaign VALUES (
                       1,?,?,?,?,?,?,?,?,?,?,?,?,0,0)""",
                    (
                        o.account_fingerprint, str(o.balance), str(o.equity),
                        _utc(o.observed_utc), _utc(o.observed_utc),
                        str(o.balance), str(o.equity),
                        o.observed_utc.date().isoformat(), str(o.equity),
                        _week_key(o.observed_utc), str(o.equity),
                        _digest(o.broker_deals),
                    ),
                )
                for d in o.broker_deals:
                    self.conn.execute(
                        "INSERT INTO seen_cash_deals VALUES (?,?,?,?,?)",
                        (d.deal_id, _utc(d.time_utc), d.kind, str(d.amount), d.magic),
                    )
                self.conn.execute("COMMIT")
                return CashRiskBaseline(
                    admitted=True, reason="NEW_PROSPECTIVE_CLEAN_DEMO_CAMPAIGN",
                    initial_equity=o.equity, day_start_equity=o.equity,
                    week_start_equity=o.equity,
                    normalized_high_water=o.equity,
                    observed_day_loss=Decimal(0),
                    observed_week_loss=Decimal(0),
                    observed_drawdown=Decimal(0),
                    loss_equivalent_streak=Decimal(0),
                )
            (
                _id, fingerprint, _initial_balance, initial_equity, _start_utc,
                last_utc, last_balance, high_water, day_key, day_start,
                week_key, week_start, old_digest, prior_count, paused
            ) = row
            if fingerprint != o.account_fingerprint or paused:
                raise DemoSafetyError("account changed or campaign quarantined")
            if o.observed_utc < datetime.fromisoformat(last_utc):
                raise DemoSafetyError("broker cash clock rollback")
            seen = {
                d_id: (when, kind, amount, magic)
                for d_id, when, kind, amount, magic in self.conn.execute(
                    "SELECT deal_id,time_utc,kind,amount,magic FROM seen_cash_deals"
                )
            }
            fresh: list[CashDeal] = []
            for d in o.broker_deals:
                if d.deal_id in seen:
                    if seen[d.deal_id] != (_utc(d.time_utc), d.kind, str(d.amount), d.magic):
                        raise DemoSafetyError("broker history deal mutated")
                else:
                    fresh.append(d)
            if not fresh and _digest(o.broker_deals) != old_digest:
                raise DemoSafetyError("broker cash history digest changed")
            if len(o.broker_deals) != len(seen) + len(fresh):
                raise DemoSafetyError("previously seen broker deal disappeared")
            if any(d.kind not in DEAL_TRADES for d in fresh):
                raise DemoSafetyError("unexpected new funding, fees, or cashflow")
            if any(d.magic != MAGIC for d in fresh):
                raise DemoSafetyError("unowned trading deal in account history")
            expected_balance = Decimal(last_balance) + sum(
                (d.amount for d in fresh), Decimal(0)
            )
            if abs(expected_balance - o.balance) > Decimal("0.02"):
                raise DemoSafetyError("broker cash balance does not reconcile")
            ntrades = int(prior_count) + len(fresh)
            newday = o.observed_utc.date().isoformat()
            newweek = _week_key(o.observed_utc)
            day_base = o.equity if newday != day_key else Decimal(day_start)
            week_base = o.equity if newweek != week_key else Decimal(week_start)
            high = max(Decimal(high_water), o.equity)
            # Ordinary trading losses are recorded; Full Policy A applies
            # the bounded loss-streak, daily/weekly and drawdown limits on
            # every subsequent order instead of an arbitrary first-loss kill.
            for d in fresh:
                self.conn.execute(
                    "INSERT INTO seen_cash_deals VALUES (?,?,?,?,?)",
                    (d.deal_id, _utc(d.time_utc), d.kind, str(d.amount), d.magic),
                )
            self.conn.execute(
                """UPDATE cash_campaign SET last_utc=?, last_balance=?,
                 high_water=?, day_key=?, day_start=?, week_key=?,
                 week_start=?, deal_digest=?, trade_count=? WHERE id=1""",
                (_utc(o.observed_utc), str(o.balance), str(high), newday,
                 str(day_base), newweek, str(week_base),
                 _digest(o.broker_deals), ntrades),
            )
            self.conn.execute("COMMIT")
            return CashRiskBaseline(
                admitted=True, reason="BROKER_CASH_RECONCILED_NO_ORDER_AUTHORITY",
                initial_equity=Decimal(initial_equity),
                day_start_equity=day_base, week_start_equity=week_base,
                normalized_high_water=high,
                observed_day_loss=max(Decimal(0), day_base - o.equity),
                observed_week_loss=max(Decimal(0), week_base - o.equity),
                observed_drawdown=max(Decimal(0), high - o.equity),
                loss_equivalent_streak=_loss_equivalent_streak(o.broker_deals),
            )
        except Exception:
            if self.conn.in_transaction:
                self.conn.execute("ROLLBACK")
            raise
