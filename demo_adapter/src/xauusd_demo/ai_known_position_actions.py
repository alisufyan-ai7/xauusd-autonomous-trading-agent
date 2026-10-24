"""AI-reviewed TP refinement and early exit of EXACT broker-owned DEMO positions.

Never initiates new exposure. Every mutation has one durable prepared intent,
one broker submission, and confirmation against history/position state.
An uncertain outcome freezes that position's further management; no retry.
Only approved known-position deal histories and authenticated broker flatness
can mark an AI-initiated early close final.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .continuous_coordinator import QualifiedBrokerAck
from .envelope import DemoSafetyError
from .known_position_reconciliation import (
    KnownPositionBinding,
    observe_known_mt5_position,
)
from .mt5_demo import _decimal, _record

if TYPE_CHECKING:
    from .openai_demo_advisor import OpenAIDemoAdvisor


class AIKnownPositionActions:
    """One-writer ancillary manager, NEVER a new MT5 login or entry sender."""

    def __init__(
        self, path: Path, *, advisor: OpenAIDemoAdvisor,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS ai_position_actions ("
            "position_id INTEGER PRIMARY KEY, account TEXT NOT NULL, "
            "original_tp TEXT NOT NULL, current_tp TEXT NOT NULL, "
            "next_tp TEXT, stage TEXT NOT NULL, at_utc TEXT NOT NULL)"
        )
        self._db.commit()
        self._advisor = advisor

    def __enter__(self) -> AIKnownPositionActions:
        return self

    def __exit__(self, *_: object) -> None:
        self._db.close()

    def _row(
        self, receipt: QualifiedBrokerAck, now: datetime,
    ) -> tuple[str, str, str, str | None, str]:
        row = self._db.execute(
            "SELECT account,original_tp,current_tp,next_tp,stage "
            "FROM ai_position_actions WHERE position_id=?",
            (receipt.position_id,),
        ).fetchone()
        if row is None:
            self._db.execute(
                "INSERT INTO ai_position_actions VALUES (?,?,?,?,?,?,?)",
                (
                    receipt.position_id, receipt.account_fingerprint,
                    str(receipt.take_profit), str(receipt.take_profit),
                    None, "ACK", now.isoformat(),
                ),
            )
            self._db.commit()
            return (
                receipt.account_fingerprint, str(receipt.take_profit),
                str(receipt.take_profit), None, "ACK",
            )
        if (
            row[0] != receipt.account_fingerprint
            or Decimal(str(row[1])) != receipt.take_profit
        ):
            raise DemoSafetyError("AI position receipt identity changed")
        return (str(row[0]), str(row[1]), str(row[2]),
                str(row[3]) if row[3] is not None else None, str(row[4]))

    def _persist(
        self, receipt: QualifiedBrokerAck, now: datetime,
        *, current: Decimal, candidate: Decimal | None, stage: str,
    ) -> None:
        self._db.execute(
            "UPDATE ai_position_actions SET current_tp=?,next_tp=?,"
            "stage=?,at_utc=? WHERE position_id=?",
            (
                str(current), str(candidate) if candidate is not None else None,
                stage, now.isoformat(), receipt.position_id,
            ),
        )
        self._db.commit()

    def current_tp(
        self, receipt: QualifiedBrokerAck, *,
        now: datetime, broker_position: dict[str, Any] | None,
    ) -> Decimal:
        _account, _original, current, proposed, stage = self._row(receipt, now)
        old = Decimal(current)
        if stage == "TP_UNCERTAIN":
            if (
                broker_position is None or proposed is None
                or _decimal(broker_position.get("tp"), "broker TP")
                   != Decimal(proposed)
            ):
                raise DemoSafetyError(
                    "prior TP broker modification unresolved; no retries"
                )
            old = Decimal(proposed)
            self._persist(
                receipt, now, current=old, candidate=None, stage="ACK",
            )
        elif stage not in ("ACK", "EXIT_UNCERTAIN", "CLOSED"):
            raise DemoSafetyError("unknown AI position modification journal state")
        return old

    def reconcile_exit(
        self, mt5: Any, receipt: QualifiedBrokerAck, *,
        now: datetime, current_stop: Decimal, current_tp: Decimal,
    ) -> bool:
        row = self._row(receipt, now)
        if row[4] == "CLOSED":
            return True
        if row[4] != "EXIT_UNCERTAIN":
            return False
        state = observe_known_mt5_position(
            mt5,
            binding=KnownPositionBinding(
                position_id=receipt.position_id,
                entry_order=receipt.order_ticket,
                entry_deal=receipt.entry_deal_ticket,
                account_fingerprint=receipt.account_fingerprint,
                side=receipt.side,
                volume=receipt.volume_lots,
                protective_sl=current_stop,
                protective_tp=current_tp,
                tick_size=receipt.tick_size,
            ),
            now=now,
        )
        if state != "CLOSED":
            raise DemoSafetyError(
                "AI early-exit outcome unresolved; no duplicate close"
            )
        self._persist(
            receipt, now, current=current_tp, candidate=None,
            stage="CLOSED",
        )
        return True

    @staticmethod
    def _aligned(
        value: Decimal, tick: Decimal, *, up: bool,
    ) -> Decimal:
        rounding = ROUND_CEILING if up else ROUND_FLOOR
        return (value / tick).to_integral_value(rounding=rounding) * tick

    def review_and_act(
        self, mt5: Any, receipt: QualifiedBrokerAck, *,
        position: dict[str, Any], now: datetime,
        bid: Decimal, ask: Decimal,
        current_stop: Decimal, current_tp: Decimal,
        minimum_distance: Decimal,
    ) -> str:
        """Read broker candle once per M15 close, AI call only on that bar."""
        timeframe = getattr(mt5, "TIMEFRAME_M15", None)
        if timeframe is None:
            return "AI_M15_TIMEFRAME_UNAVAILABLE"
        history = mt5.copy_rates_from_pos("XAUUSD", timeframe, 1, 4)
        if history is None or len(history) != 4:
            return "AI_M15_HISTORY_UNAVAILABLE"
        try:
            stamp = int(history[0]["time"])
            bar_close = datetime.fromtimestamp(stamp, UTC) + timedelta(
                minutes=15,
            )
        except (ValueError, TypeError, OverflowError, KeyError):
            return "AI_BAR_TIME_UNAVAILABLE"
        if not timedelta(0) <= now-bar_close <= timedelta(seconds=20):
            return "AI_WAIT_NEXT_M15"
        info = [{
            "t": int(row["time"]),
            "o": float(row["open"]), "h": float(row["high"]),
            "l": float(row["low"]), "c": float(row["close"]),
        } for row in history]
        context: dict[str, object] = {
            "symbol": "XAUUSD", "kind": "KNOWN_POSITION",
            "side": receipt.side, "entry": str(receipt.entry_price),
            "initial_sl": str(receipt.stop_loss),
            "current_sl": str(current_stop), "current_tp": str(current_tp),
            "bid": str(bid), "ask": str(ask), "m15": info,
            "utc": bar_close.isoformat(),
        }
        action = self._advisor.manage_position(
            review_key=(
                f"position:{receipt.position_id}:{stamp + 900}"
            ),
            observed_utc=now, market=context,
        )
        if action == "HOLD":
            return "AI_HOLD"
        if action == "TIGHTEN_TP":
            # Model supplies the ACTION only; broker-tradable target is
            # deterministic and strictly nearer than previously recorded TP.
            if receipt.side == "BUY":
                candidate = self._aligned(
                    current_tp - (
                        current_tp - receipt.entry_price
                    ) * Decimal("0.25"),
                    receipt.tick_size, up=False,
                )
                allowed = (
                    candidate < current_tp - receipt.tick_size
                    and candidate > ask + minimum_distance
                    and candidate > bid
                )
            else:
                candidate = self._aligned(
                    current_tp + (
                        receipt.entry_price - current_tp
                    ) * Decimal("0.25"),
                    receipt.tick_size, up=True,
                )
                allowed = (
                    candidate > current_tp + receipt.tick_size
                    and candidate < bid - minimum_distance
                    and candidate < ask
                )
            if not allowed:
                return "AI_TP_NO_SAFE_REFINEMENT"
            self._persist(
                receipt, now, current=current_tp, candidate=candidate,
                stage="TP_UNCERTAIN",
            )
            payload = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": position["ticket"], "symbol": "XAUUSD",
                "sl": float(current_stop), "tp": float(candidate),
                "magic": 260101,
            }
            try:
                check = _record(mt5.order_check(payload), "AI TP check")
                if int(check.get("retcode", -1)) != 0:
                    # No send means no unknown broker mutation.
                    self._persist(
                        receipt, now, current=current_tp,
                        candidate=None, stage="ACK",
                    )
                    return "AI_TP_BROKER_CHECK_REJECTED"
                reply = _record(mt5.order_send(payload), "AI TP send")
                if reply.get("retcode") != mt5.TRADE_RETCODE_DONE:
                    raise DemoSafetyError("AI TP broker response uncertain")
                active = mt5.positions_get()
                if active is None or len(tuple(active)) != 1:
                    raise DemoSafetyError("AI TP post-send exposure uncertain")
                updated = _record(tuple(active)[0], "AI TP verified position")
                if (
                    updated.get("identifier") != receipt.position_id
                    or _decimal(updated.get("tp"), "updated TP") != candidate
                    or _decimal(updated.get("sl"), "unchanged SL")
                    != current_stop
                ):
                    raise DemoSafetyError("AI TP broker change unconfirmed")
            except Exception as exc:
                raise DemoSafetyError(
                    "AI TP modification uncertain; no retry"
                ) from exc
            self._persist(
                receipt, now, current=candidate,
                candidate=None, stage="ACK",
            )
            return "AI_TP_REFINED_CONFIRMED"

        if action == "EARLY_EXIT":
            volume = _decimal(position.get("volume"), "known exit volume")
            if volume != receipt.volume_lots:
                return "AI_EXIT_PARTIAL_POSITION_NOT_SUPPORTED"
            symbol_info = _record(mt5.symbol_info("XAUUSD"), "exit symbol")
            filling = int(symbol_info.get("filling_mode") or 0)
            if filling & 2:
                fill_type = getattr(mt5, "ORDER_FILLING_IOC", None)
            elif filling & 1:
                fill_type = getattr(mt5, "ORDER_FILLING_FOK", None)
            else:
                return "AI_EXIT_FILLING_MODE_NOT_SUPPORTED"
            if fill_type is None:
                return "AI_EXIT_FILLING_UNKNOWN"
            exit_is_sell = receipt.side == "BUY"
            payload = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": "XAUUSD", "position": position["ticket"],
                "volume": float(volume), "magic": 260101,
                "type": mt5.ORDER_TYPE_SELL if exit_is_sell
                else mt5.ORDER_TYPE_BUY,
                "price": float(bid if exit_is_sell else ask),
                "deviation": 10,
                "type_filling": fill_type,
                "comment": "XAUUSD-AI-KNOWN-EXIT",
            }
            check = _record(mt5.order_check(payload), "known exit check")
            if int(check.get("retcode", -1)) != 0:
                return "AI_EXIT_BROKER_CHECK_DENIED"
            self._persist(
                receipt, now, current=current_tp, candidate=None,
                stage="EXIT_UNCERTAIN",
            )
            try:
                reply = _record(mt5.order_send(payload), "known exit send")
                if reply.get("retcode") != mt5.TRADE_RETCODE_DONE:
                    raise DemoSafetyError("exit broker result uncertain")
                if not self.reconcile_exit(
                    mt5, receipt, now=now, current_stop=current_stop,
                    current_tp=current_tp,
                ):
                    raise DemoSafetyError("known exit deals not reconciled")
            except Exception as exc:
                raise DemoSafetyError(
                    "AI known-position close uncertain; no retry"
                ) from exc
            return "AI_EARLY_EXIT_BROKER_CONFIRMED"
        raise DemoSafetyError("unexpected AI position action")
