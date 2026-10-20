"""One-entry/one-close, explicitly gated Exness DEMO canary (NO CLI).

The module never imports/starts MT5, logs into any account, or activates
execution by itself. Dependencies are injected; GitHub tests use only fakes.
"""
from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from .canary_policy import CanaryRiskDecision, CanaryRiskEvidence, d, evaluate_canary_risk
from .control import DemoControlStore
from .envelope import DemoActivationPermit, DemoIdentity, DemoOrderRequest, DemoSafetyError

BROKER = "Exness Technologies Ltd"
SERVER = "Exness-MT5Trial15"
CURRENCY = "USD"
ACCOUNT_SHA256 = "9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91"
CANARY_APC_TOKEN = "APC-DEMO-CANARY-ONE-ENTRY-ONE-CLOSE"  # noqa: S105
MAGIC = 261020
MAX_DEVIATION_POINTS = 20


def row(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        raise DemoSafetyError("UNKNOWN_" + name)
    if isinstance(value, dict):
        return value
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    raise DemoSafetyError("INVALID_" + name)


def exact_demo_identity() -> DemoIdentity:
    return DemoIdentity(BROKER, SERVER, ACCOUNT_SHA256, CURRENCY)


class CanaryJournal:
    """Durable single-use ledger; no retry after intent, ambiguous result or close.

    SQLite WAL/FULL. Database creation is VPS mutation: NOT allowed until a
    separately approved execution-off staging/activation step.
    """
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS canary ("
            " id INTEGER PRIMARY KEY CHECK (id=1),"
            " stage TEXT NOT NULL, request_id TEXT NOT NULL,"
            " position_ticket TEXT, stop TEXT, volume TEXT,"
            " reason TEXT NOT NULL ) STRICT"
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> CanaryJournal:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def stage(self) -> str:
        item = self._conn.execute("SELECT stage FROM canary WHERE id=1").fetchone()
        return "UNUSED" if item is None else str(item[0])

    def position(self) -> tuple[str, Decimal, Decimal]:
        item = self._conn.execute(
            "SELECT position_ticket,volume,stop FROM canary "
            "WHERE id=1 AND stage='OPEN'"
        ).fetchone()
        if item is None or any(x is None for x in item):
            raise DemoSafetyError("CANARY_NO_CONFIRMED_OPEN_POSITION")
        return str(item[0]), d(item[1], "volume"), d(item[2], "stop")

    def reserve_entry(self, req: DemoOrderRequest) -> None:
        req.validate()
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            if self._conn.execute("SELECT id FROM canary WHERE id=1").fetchone():
                raise DemoSafetyError("CANARY_ONCE_ONLY_ENTRY_ALREADY_CONSUMED")
            self._conn.execute(
                "INSERT INTO canary(id,stage,request_id,reason)"
                " VALUES(1,'ENTRY_IN_FLIGHT',?,'ENTRY_INTENT_DURABLE')",
                (req.request_id,),
            )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def entered(self, ticket: str, stop: Decimal, volume: Decimal) -> None:
        self._transition("ENTRY_IN_FLIGHT", "OPEN", "ENTRY_RECONCILED",
                         ticket=ticket, stop=stop, volume=volume)

    def reserve_close(self) -> None:
        self._transition("OPEN", "CLOSE_IN_FLIGHT", "CLOSE_INTENT_DURABLE")

    def closed(self) -> None:
        self._transition("CLOSE_IN_FLIGHT", "CLOSED", "FLAT_RECONCILED")

    def uncertain(self, reason: str) -> None:
        self._conn.execute(
            "UPDATE canary SET stage='UNCERTAIN',reason=? WHERE id=1",
            (reason[:400],),
        )
        self._conn.commit()

    def _transition(
        self, before: str, after: str, reason: str,
        *, ticket: str | None = None, stop: Decimal | None = None,
        volume: Decimal | None = None,
    ) -> None:
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            cur = self._conn.execute(
                "UPDATE canary SET stage=?,reason=?,"
                "position_ticket=COALESCE(?,position_ticket),"
                "stop=COALESCE(?,stop),volume=COALESCE(?,volume)"
                " WHERE id=1 AND stage=?",
                (after, reason, ticket, str(stop) if stop is not None else None,
                 str(volume) if volume is not None else None, before),
            )
            if cur.rowcount != 1:
                raise DemoSafetyError("CANARY_JOURNAL_STAGE_MISMATCH")
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise


@dataclass(frozen=True, slots=True)
class OpenCanaryResult:
    status: str
    ticket: str
    worst_loss_usd: Decimal
    risk_cap_usd: Decimal
    classification: str = "DEMO_CANARY_ONLY"


class DemoCanaryLifecycle:
    def __init__(
        self, mt5: Any, control: DemoControlStore,
        journal: CanaryJournal,
        *, clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._mt5 = mt5
        self._control = control
        self._journal = journal
        self._identity = exact_demo_identity()
        self._clock = clock or (lambda: datetime.now(UTC))

    def _check_clock(self, now: datetime) -> None:
        current = self._clock()
        if (now.tzinfo is None or current.tzinfo is None or
                abs((current.astimezone(UTC) - now.astimezone(UTC)).total_seconds()) > 2):
            raise DemoSafetyError("CANARY_CLOCK_NOT_CURRENT")

    def _check(self, *, now: datetime,
               permit: DemoActivationPermit) -> dict[str, Any]:
        self._check_clock(now)
        if permit.max_daily_submissions != 1:
            raise DemoSafetyError("CANARY_PERMIT_MUST_LIMIT_TO_ONE")
        self._control.assert_active(permit=permit, identity=self._identity, now=now)
        t = row(self._mt5.terminal_info(), "TERMINAL")
        a = row(self._mt5.account_info(), "ACCOUNT")
        if t.get("connected") is not True or t.get("tradeapi_disabled") is not False:
            raise DemoSafetyError("CANARY_TERMINAL_NOT_CONNECTED_OR_DISABLED")
        if a.get("trade_mode") != self._mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise DemoSafetyError("CANARY_NOT_EXNESS_DEMO")
        if (a.get("company"), a.get("server"), a.get("currency")) != (
            BROKER, SERVER, CURRENCY
        ):
            raise DemoSafetyError("CANARY_BROKER_SERVER_CURRENCY_MISMATCH")
        if type(a.get("login")) is not int or a["login"] <= 0:
            raise DemoSafetyError("CANARY_UNKNOWN_LOGIN")
        fingerprint = hashlib.sha256(
            f"{BROKER}|{SERVER}|{a['login']}|{CURRENCY}".encode()
        ).hexdigest()
        if fingerprint != ACCOUNT_SHA256:
            raise DemoSafetyError("CANARY_FINGERPRINT_MISMATCH")
        return a

    def _exposure(self) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
        ps = self._mt5.positions_get()
        os = self._mt5.orders_get()
        if ps is None or os is None:
            raise DemoSafetyError("CANARY_UNRECONCILED_EXPOSURE")
        return tuple(ps), tuple(os)

    def _symbol_quote(self, now: datetime) -> tuple[dict[str, Any], dict[str, Any]]:
        info = row(self._mt5.symbol_info("XAUUSD"), "SYMBOL")
        tick = row(self._mt5.symbol_info_tick("XAUUSD"), "TICK")
        if info.get("name") != "XAUUSD":
            raise DemoSafetyError("CANARY_SYMBOL_IDENTITY_MISMATCH")
        if info.get("trade_mode") != self._mt5.SYMBOL_TRADE_MODE_FULL:
            raise DemoSafetyError("CANARY_SYMBOL_NOT_FULL_TRADING")
        if (type(tick.get("time_msc")) is not int
                or abs(int(now.timestamp() * 1000) - tick["time_msc"]) > 5000):
            raise DemoSafetyError("CANARY_QUOTE_STALE")
        return info, tick

    def _filling(self, info: dict[str, Any]) -> int:
        # SYMBOL_FILLING_MODE flags: FOK=1, IOC=2. Never guess RETURN.
        flags = info.get("filling_mode")
        if type(flags) is not int or flags < 0:
            raise DemoSafetyError("CANARY_UNVERIFIED_FILLING_MODE")
        if flags & 1:
            return int(self._mt5.ORDER_FILLING_FOK)
        if flags & 2:
            return int(self._mt5.ORDER_FILLING_IOC)
        raise DemoSafetyError("CANARY_UNSUPPORTED_MARKET_FILLING")

    def _risk(
        self, request: DemoOrderRequest, a: dict[str, Any],
        now: datetime,
    ) -> tuple[CanaryRiskDecision, dict[str, Any]]:
        info, tick = self._symbol_quote(now)
        is_buy = request.side.value == "BUY"
        order_type = (self._mt5.ORDER_TYPE_BUY if is_buy
                      else self._mt5.ORDER_TYPE_SELL)
        entry = d(tick["ask" if is_buy else "bid"], "entry")
        margin = self._mt5.order_calc_margin(
            order_type, "XAUUSD", float(request.volume_lots), float(entry)
        )
        calc_profit = self._mt5.order_calc_profit(
            order_type, "XAUUSD", float(request.volume_lots),
            float(entry), float(request.stop_loss)
        )
        if margin is None or calc_profit is None:
            raise DemoSafetyError("CANARY_BROKER_RISK_RECONCILIATION_FAILED")
        stops_level = info.get("trade_stops_level")
        if type(stops_level) is not int:
            raise DemoSafetyError("CANARY_STOP_LEVEL_UNVERIFIED")
        ev = CanaryRiskEvidence(
            symbol=request.symbol, side=request.side.value,
            lots=request.volume_lots, stop=request.stop_loss,
            bid=d(tick.get("bid"), "bid"), ask=d(tick.get("ask"), "ask"),
            tick_msec=tick["time_msc"], now_msec=int(now.timestamp() * 1000),
            tick_size=d(info.get("trade_tick_size"), "tick_size"),
            tick_value_loss=d(info.get("trade_tick_value_loss"), "tick_loss"),
            contract_size=d(info.get("trade_contract_size"), "contract_size"),
            currency_profit=str(info.get("currency_profit") or ""),
            volume_min=d(info.get("volume_min"), "volume_min"),
            volume_max=d(info.get("volume_max"), "volume_max"),
            volume_step=d(info.get("volume_step"), "volume_step"),
            point=d(info.get("point"), "point"),
            stops_level=stops_level,
            equity=d(a.get("equity"), "equity"),
            balance=d(a.get("balance"), "balance"),
            free_margin=d(a.get("margin_free"), "margin_free"),
            margin_used=d(a.get("margin"), "margin"),
            incremental_margin=d(margin, "incremental_margin"),
            broker_stop_profit_usd=d(calc_profit, "stop_profit"),
        )
        decision = evaluate_canary_risk(ev)
        payload = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": "XAUUSD", "type": order_type,
            "volume": float(request.volume_lots), "price": float(entry),
            "sl": float(request.stop_loss),
            "deviation": MAX_DEVIATION_POINTS,
            "magic": MAGIC, "comment": "ONE DEMO CANARY",
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._filling(info),
        }
        return decision, payload

    def _fail(self, reason: str, now: datetime) -> None:
        # Journal intent is never recycled. Unknown exposure: no auto-close.
        self._journal.uncertain(reason)
        self._control.quarantine(reason=reason, now=now)

    def open_once(
        self, *, request: DemoOrderRequest, permit: DemoActivationPermit,
        now: datetime, apc_token: str,
    ) -> OpenCanaryResult:
        if apc_token != CANARY_APC_TOKEN:
            raise DemoSafetyError("CANARY_OWNER_APC_REQUIRED")
        request.validate()
        if self._journal.stage() != "UNUSED":
            raise DemoSafetyError("CANARY_ENTRY_BUDGET_CONSUMED")
        try:
            a = self._check(now=now, permit=permit)
            ps, os = self._exposure()
            if ps or os:
                raise DemoSafetyError("CANARY_NOT_STARTING_FLAT")
            risk, payload = self._risk(request, a, now)
            check = row(self._mt5.order_check(payload), "ORDER_CHECK")
            if int(check.get("retcode", -1)) != 0:
                raise DemoSafetyError("CANARY_ORDER_CHECK_FAILED")
            # Exact account/exposure checked a second time immediately before send.
            self._check(now=now, permit=permit)
            ps, os = self._exposure()
            if ps or os:
                raise DemoSafetyError("CANARY_EXPOSURE_CHANGED_BEFORE_ENTRY")
            _, newest_tick = self._symbol_quote(self._clock())
            is_buy = request.side.value == "BUY"
            current_price = d(newest_tick["ask" if is_buy else "bid"], "latest_entry")
            if abs(current_price - d(payload["price"], "checked_entry")) > Decimal("0.20"):
                raise DemoSafetyError("CANARY_ENTRY_QUOTE_MOVED_AFTER_RISK_CHECK")
        except Exception:
            self._control.quarantine(reason="CANARY_PREENTRY_FAIL_CLOSED", now=now)
            raise
        self._journal.reserve_entry(request)
        try:
            result = row(self._mt5.order_send(payload), "ENTRY_RESULT")
            if result.get("retcode") != self._mt5.TRADE_RETCODE_DONE:
                raise DemoSafetyError("CANARY_NONFINAL_ENTRY_ACK")
            ps, os = self._exposure()
            if len(ps) != 1 or os:
                raise DemoSafetyError("CANARY_POST_ENTRY_EXPOSURE_UNCERTAIN")
            p = row(ps[0], "POSITION")
            if (p.get("symbol") != "XAUUSD" or
                    d(p.get("volume"), "position_volume") != request.volume_lots or
                    d(p.get("sl"), "position_sl") != request.stop_loss):
                raise DemoSafetyError("CANARY_POST_ENTRY_POSITION_MISMATCH")
            if type(p.get("ticket")) is not int or p["ticket"] <= 0:
                raise DemoSafetyError("CANARY_POST_ENTRY_TICKET_UNKNOWN")
            ticket = str(p["ticket"])
            self._journal.entered(ticket, request.stop_loss, request.volume_lots)
            return OpenCanaryResult(
                status="OPEN_RECONCILED", ticket=ticket,
                worst_loss_usd=risk.worst_loss_to_stop_usd,
                risk_cap_usd=risk.risk_cap_usd,
            )
        except BaseException:
            self._fail("CANARY_ENTRY_OUTCOME_UNCERTAIN", now)
            raise

    def close_once(
        self, *, permit: DemoActivationPermit, now: datetime,
        apc_token: str,
    ) -> str:
        if apc_token != CANARY_APC_TOKEN:
            raise DemoSafetyError("CANARY_CLOSE_OWNER_APC_REQUIRED")
        if self._journal.stage() != "OPEN":
            raise DemoSafetyError("CANARY_NOT_IN_CONFIRMED_OPEN_STATE")
        try:
            self._check(now=now, permit=permit)
            expected_ticket, volume, stop = self._journal.position()
            ps, os = self._exposure()
            if len(ps) != 1 or os:
                raise DemoSafetyError("CANARY_CLOSE_EXPOSURE_UNCERTAIN")
            pos = row(ps[0], "CLOSE_POSITION")
            if (str(pos.get("ticket")) != expected_ticket or
                    pos.get("symbol") != "XAUUSD" or
                    d(pos.get("volume"), "close_volume") != volume or
                    d(pos.get("sl"), "close_sl") != stop):
                raise DemoSafetyError("CANARY_CLOSE_POSITION_CHANGED")
            if pos.get("type") not in (
                self._mt5.POSITION_TYPE_BUY, self._mt5.POSITION_TYPE_SELL
            ):
                raise DemoSafetyError("CANARY_CLOSE_UNKNOWN_POSITION_SIDE")
            info, tick = self._symbol_quote(now)
            is_buy = pos["type"] == self._mt5.POSITION_TYPE_BUY
            close_type = (self._mt5.ORDER_TYPE_SELL if is_buy
                          else self._mt5.ORDER_TYPE_BUY)
            close_px = d(tick["bid" if is_buy else "ask"], "close_price")
            payload = {
                "action": self._mt5.TRADE_ACTION_DEAL, "symbol": "XAUUSD",
                "position": int(expected_ticket), "type": close_type,
                "volume": float(volume), "price": float(close_px),
                "deviation": MAX_DEVIATION_POINTS, "magic": MAGIC,
                "comment": "CLOSE ONE DEMO CANARY",
                "type_time": self._mt5.ORDER_TIME_GTC,
                "type_filling": self._filling(info),
            }
            check = row(self._mt5.order_check(payload), "CLOSE_CHECK")
            if int(check.get("retcode", -1)) != 0:
                raise DemoSafetyError("CANARY_CLOSE_ORDER_CHECK_FAILED")
        except Exception:
            self._fail("CANARY_CLOSE_PREFLIGHT_UNCERTAIN_MANUAL_REVIEW", now)
            raise
        self._journal.reserve_close()
        try:
            done = row(self._mt5.order_send(payload), "CLOSE_RESULT")
            if done.get("retcode") != self._mt5.TRADE_RETCODE_DONE:
                raise DemoSafetyError("CANARY_CLOSE_ACK_UNCERTAIN")
            ps, os = self._exposure()
            if ps or os:
                raise DemoSafetyError("CANARY_CLOSE_NOT_FLAT")
            self._journal.closed()
            self._control.kill(reason="ONE_DEMO_CANARY_FINISHED", now=now)
            return "CLOSED_FLAT_KILLED"
        except BaseException:
            self._fail("CANARY_CLOSE_OUTCOME_UNCERTAIN_MANUAL_REVIEW", now)
            raise
