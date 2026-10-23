"""Demo-only MetaTrader 5 adapter with exact identity and risk-envelope guards."""

from __future__ import annotations

import hashlib
import importlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from .control import DemoControlStore
from .envelope import (
    DemoActivationPermit,
    DemoIdentity,
    DemoOrderRequest,
    DemoPolicy,
    DemoSafetyError,
    DemoSide,
)
from .ledger import DemoSubmissionLedger
from .risk_binding import DemoRiskCalibration, evaluate_bound_demo_risk
from .s2_order_sources import S2OrderSources

SUBMISSION_CONFIRMATION = "SUBMIT-BOUNDED-DEMO-XAUUSD"


def _record(value: Any, label: str) -> dict[str, Any]:
    if value is None:
        raise DemoSafetyError(f"{label} returned no data")
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    if hasattr(value, "__dict__"):
        return dict(vars(value))
    raise DemoSafetyError(f"{label} returned unsupported data")


def _decimal(value: Any, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise DemoSafetyError(f"{label} is not decimal") from exc
    if not result.is_finite():
        raise DemoSafetyError(f"{label} is not finite")
    return result


class DemoMT5Adapter:
    def __init__(
        self,
        identity: DemoIdentity,
        policy: DemoPolicy,
        ledger: DemoSubmissionLedger,
        *,
        control: DemoControlStore | None = None,
        module: Any | None = None,
    ) -> None:
        identity.validate()
        policy.validate()
        self._identity = identity
        self._policy = policy
        self._ledger = ledger
        self._control = control
        self._mt5 = module
        self._initialized = False

    def initialize(self) -> None:
        if self._mt5 is None:
            try:
                self._mt5 = importlib.import_module("MetaTrader5")
            except ImportError as exc:
                raise DemoSafetyError("MetaTrader5 package unavailable") from exc
        if not bool(self._mt5.initialize()):
            raise DemoSafetyError(f"MT5 initialize failed: {self._mt5.last_error()}")
        self._initialized = True
        try:
            self._identity_guard(require_execution_enabled=False)
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        if self._initialized and self._mt5 is not None:
            self._mt5.shutdown()
        self._initialized = False

    def __enter__(self) -> DemoMT5Adapter:
        self.initialize()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _identity_guard(
        self,
        *,
        require_execution_enabled: bool,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self._initialized or self._mt5 is None:
            raise DemoSafetyError("demo MT5 adapter is not initialized")

        terminal = _record(self._mt5.terminal_info(), "terminal_info")
        account = _record(self._mt5.account_info(), "account_info")

        if terminal.get("connected") is not True:
            raise DemoSafetyError("MT5 terminal is not connected")

        tradeapi_disabled = terminal.get("tradeapi_disabled")
        if require_execution_enabled and tradeapi_disabled is not False:
            raise DemoSafetyError("external Python demo execution is not enabled")

        demo_mode = int(self._mt5.ACCOUNT_TRADE_MODE_DEMO)
        if int(account.get("trade_mode", -1)) != demo_mode:
            raise DemoSafetyError("account is not an MT5 demo account")

        broker = str(account.get("company") or "")
        server = str(account.get("server") or "")
        currency = str(account.get("currency") or "")
        login = str(account.get("login") or "")
        fingerprint = hashlib.sha256(
            f"{broker}|{server}|{login}|{currency}".encode()
        ).hexdigest()

        if broker != self._identity.broker:
            raise DemoSafetyError("demo broker identity mismatch")
        if server != self._identity.server:
            raise DemoSafetyError("demo server identity mismatch")
        if currency != self._identity.currency:
            raise DemoSafetyError("demo account currency mismatch")
        if fingerprint != self._identity.account_id_sha256:
            raise DemoSafetyError("demo account fingerprint mismatch")

        return terminal, account

    def _zero_exposure_guard(self) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
        assert self._mt5 is not None
        positions = self._mt5.positions_get()
        orders = self._mt5.orders_get()
        if positions is None:
            raise DemoSafetyError(f"positions_get failed: {self._mt5.last_error()}")
        if orders is None:
            raise DemoSafetyError(f"orders_get failed: {self._mt5.last_error()}")
        positions_tuple = tuple(positions)
        orders_tuple = tuple(orders)
        if positions_tuple or orders_tuple:
            raise DemoSafetyError(
                "demo activation/new risk requires zero positions and zero pending orders"
            )
        return positions_tuple, orders_tuple

    def preflight(self) -> dict[str, object]:
        terminal, _ = self._identity_guard(require_execution_enabled=False)
        positions, orders = self._zero_exposure_guard()
        control_state = "KILLED"
        if self._control is not None:
            control_state = self._control.snapshot().state.value
        return {
            "demo_identity_match": True,
            "demo_trade_mode": True,
            "connected": True,
            "external_python_trading_enabled": terminal.get("tradeapi_disabled") is False,
            "symbol": "XAUUSD",
            "open_positions": len(positions),
            "pending_orders": len(orders),
            "maximum_volume_lots": "0.01",
            "maximum_concurrent_positions": 1,
            "protective_stop_required": True,
            "control_state": control_state,
        }

    def _build_request(
        self, request: DemoOrderRequest, *, now: datetime | None = None
    ) -> dict[str, Any]:
        request.validate()
        assert self._mt5 is not None

        info = _record(self._mt5.symbol_info("XAUUSD"), "symbol_info")
        tick = _record(self._mt5.symbol_info_tick("XAUUSD"), "symbol_info_tick")

        volume_min = _decimal(info.get("volume_min"), "volume_min")
        volume_max = _decimal(info.get("volume_max"), "volume_max")
        volume_step = _decimal(info.get("volume_step"), "volume_step")
        point = _decimal(info.get("point"), "point")

        if request.volume_lots < volume_min or request.volume_lots > volume_max:
            raise DemoSafetyError("requested volume is outside broker symbol bounds")
        if volume_step <= 0:
            raise DemoSafetyError("broker volume_step is invalid")
        steps = request.volume_lots / volume_step
        if steps != steps.to_integral_value():
            raise DemoSafetyError("requested volume is not aligned to broker volume_step")

        bid = _decimal(tick.get("bid"), "bid")
        ask = _decimal(tick.get("ask"), "ask")
        stops_level = Decimal(int(info.get("trade_stops_level") or 0)) * point
        if bid <= 0 or ask <= bid or point <= 0:
            raise DemoSafetyError("invalid broker quote or point")
        if request.is_tpb_stop:
            assert request.entry_stop is not None
            assert request.take_profit is not None
            assert request.expires_utc is not None
            effective = now or datetime.now(UTC)
            if (
                effective.tzinfo is None
                or effective.utcoffset() != timedelta(0)
                or not effective < request.expires_utc
                or request.expires_utc - effective > timedelta(hours=1)
            ):
                raise DemoSafetyError("TPB STOP expiry not an eligible 4-bar window")
            tick_size = _decimal(info.get("trade_tick_size"), "trade_tick_size")
            if tick_size <= 0:
                raise DemoSafetyError("symbol tick size unavailable")
            for value in (
                request.entry_stop, request.stop_loss, request.take_profit,
            ):
                steps = value / tick_size
                if steps != steps.to_integral_value():
                    raise DemoSafetyError("TPB STOP price not broker tick normalized")
            buy = request.side is DemoSide.BUY
            if (
                (buy and (
                    request.entry_stop <= ask + stops_level
                    or request.entry_stop - request.stop_loss < stops_level
                    or request.take_profit - request.entry_stop < stops_level
                ))
                or (not buy and (
                    request.entry_stop >= bid - stops_level
                    or request.stop_loss - request.entry_stop < stops_level
                    or request.entry_stop - request.take_profit < stops_level
                ))
            ):
                raise DemoSafetyError("TPB STOP violates market or protective levels")
            order_type = (
                int(self._mt5.ORDER_TYPE_BUY_STOP)
                if buy else int(self._mt5.ORDER_TYPE_SELL_STOP)
            )
            return {
                "action": int(self._mt5.TRADE_ACTION_PENDING),
                "symbol": "XAUUSD",
                "volume": float(request.volume_lots),
                "type": order_type,
                "price": float(request.entry_stop),
                "sl": float(request.stop_loss),
                "tp": float(request.take_profit),
                "expiration": int(request.expires_utc.timestamp()),
                "type_time": int(self._mt5.ORDER_TIME_SPECIFIED),
                "deviation": self._policy.max_deviation_points,
                "magic": 260101,
                "comment": f"XAU-TPB {request.request_id[:8]}",
            }

        if request.side is DemoSide.BUY:
            price = ask
            order_type = int(self._mt5.ORDER_TYPE_BUY)
            if request.stop_loss >= bid:
                raise DemoSafetyError("BUY protective stop must be below current bid")
            if stops_level > 0 and bid - request.stop_loss < stops_level:
                raise DemoSafetyError("BUY protective stop violates broker stop distance")
        else:
            price = bid
            order_type = int(self._mt5.ORDER_TYPE_SELL)
            if request.stop_loss <= ask:
                raise DemoSafetyError("SELL protective stop must be above current ask")
            if stops_level > 0 and request.stop_loss - ask < stops_level:
                raise DemoSafetyError("SELL protective stop violates broker stop distance")

        return {
            "action": int(self._mt5.TRADE_ACTION_DEAL),
            "symbol": "XAUUSD",
            "volume": float(request.volume_lots),
            "type": order_type,
            "price": float(price),
            "sl": float(request.stop_loss),
            "deviation": self._policy.max_deviation_points,
            "magic": 260101,
            "comment": f"XAU-DEMO {request.request_id[:8]}",
            "type_time": int(self._mt5.ORDER_TIME_GTC),
        }

    def _mark_uncertain_and_quarantine(
        self,
        *,
        request_id: str,
        detail: str,
        now: datetime,
    ) -> None:
        self._ledger.mark_uncertain(request_id, detail=detail)
        if self._control is not None:
            self._control.quarantine(
                reason=f"UNCERTAIN_SUBMISSION:{detail}",
                now=now,
            )

    def submit_market_order(
        self,
        request: DemoOrderRequest,
        *,
        confirmation_phrase: str,
        activation_permit: DemoActivationPermit | None = None,
        risk_calibration: DemoRiskCalibration | None = None,
        full_policy_sources: S2OrderSources | None = None,
        now: datetime | None = None,
    ) -> dict[str, object]:
        if confirmation_phrase != SUBMISSION_CONFIRMATION:
            raise DemoSafetyError("exact demo submission confirmation token required")

        request.validate()
        effective_now = now or datetime.now(UTC)

        if activation_permit is None:
            raise DemoSafetyError("demo execution requires an owner-gated activation permit")
        if self._control is None:
            raise DemoSafetyError("demo execution requires a durable kill/quarantine control")

        activation_permit.validate(now=effective_now)
        if activation_permit.max_daily_submissions != self._policy.max_daily_submissions:
            self._control.quarantine(
                reason="ACTIVATION_DAILY_BUDGET_MISMATCH",
                now=effective_now,
            )
            raise DemoSafetyError("activation daily submission budget mismatch")

        self._control.assert_active(
            permit=activation_permit,
            identity=self._identity,
            now=effective_now,
        )

        try:
            _, account = self._identity_guard(require_execution_enabled=True)
            self._zero_exposure_guard()
        except DemoSafetyError:
            self._control.quarantine(
                reason="PRE_SUBMIT_IDENTITY_OR_EXPOSURE_FAILURE",
                now=effective_now,
            )
            raise

        mt5_request = self._build_request(request, now=effective_now)
        assert self._mt5 is not None

        # Broker margin calculator uses directional BUY/SELL economics even
        # for a future STOP entry; the order submission type remains STOP.
        # NEVER pass pending ORDER_TYPE_*_STOP as proof of current exposure.
        margin_direction_type = (
            int(self._mt5.ORDER_TYPE_BUY)
            if request.side is DemoSide.BUY else int(self._mt5.ORDER_TYPE_SELL)
        )
        margin_raw = self._mt5.order_calc_margin(
            margin_direction_type,
            "XAUUSD",
            float(request.volume_lots),
            float(mt5_request["price"]),
        )
        if margin_raw is None:
            self._control.quarantine(
                reason="MARGIN_CALCULATION_UNAVAILABLE",
                now=effective_now,
            )
            raise DemoSafetyError(f"order_calc_margin failed: {self._mt5.last_error()}")

        try:
            risk = evaluate_bound_demo_risk(
                account=account,
                request=request,
                incremental_margin=_decimal(margin_raw, "incremental margin"),
                calibration=risk_calibration,
                expected_calibration_sha256=self._policy.risk_calibration_sha256,
            )
        except DemoSafetyError:
            self._control.quarantine(
                reason="RISK_GOVERNOR_PRECONDITION_OR_DENIAL",
                now=effective_now,
            )
            raise

        # Existing old callers still fail without SOURCE INPUTS. This is no
        # longer a permanent unconditional rejection: the SAME S2 sender may
        # proceed for a STOP order only after it independently recomputes live
        # full Policy A from MT5 cash history, official snapshots and broker
        # stop-loss / margin for the exact request and exact UTC observation.
        # A caller-supplied risk_pass Boolean or mathematical receipt is NEVER
        # accepted as execution authority.
        if full_policy_sources is None or not request.is_tpb_stop:
            self._control.quarantine(
                reason="FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED",
                now=effective_now,
            )
            raise DemoSafetyError(
                "full Policy A broker-reconciled USD cash-risk binding is not admitted"
            )
        from .s2_full_policy_probe import preview_s2_full_policy_tpb

        sources = full_policy_sources
        # Explicitly disallow synthetic provenance in a broker-order route.
        # Positive adverse slip/gap reserves are mandatory; unavailable
        # adverse costs do not become ZERO because this is virtual money.
        if (
            sources.costs.calibration_id.upper().startswith("SYNTHETIC")
            or sources.costs.slippage_reserve_usd <= 0
            or sources.costs.gap_reserve_usd <= 0
            or not sources.official_snapshots
            or any(
                "SYNTHETIC" in shot.parser_version.upper()
                for shot in sources.official_snapshots
            )
        ):
            self._control.quarantine(
                reason="UNQUALIFIED_REAL_DEMO_SOURCE_PROVENANCE",
                now=effective_now,
            )
            raise DemoSafetyError("real DEMO order source provenance is not admitted")
        try:
            full = preview_s2_full_policy_tpb(
                self, request, now=effective_now,
                cash_journal=sources.cash_journal,
                calibrated_costs=sources.costs,
                pinned_cost_sha256=sources.expected_cost_sha256,
                official_snapshots=sources.official_snapshots,
                session_verified_through_utc=sources.session_verified_through_utc,
                shock_locked=sources.shock_locked,
                normalized=sources.normalized,
            )
            if (
                not full.mathematics_pass
                or full.request_id != request.request_id
                or full.broker_entry != _decimal(mt5_request.get("price"), "entry")
                or full.broker_stop != request.stop_loss
                or full.broker_take_profit != request.take_profit
                or full.broker_order_type != int(mt5_request["type"])
                or full.broker_expiration_utc != request.expires_utc
            ):
                raise DemoSafetyError("full source-bound Policy A denied STOP")
            # One final broker/account/exposure check before order_check and
            # intent-before-send. The two source readings are on the same MT5.
            self._identity_guard(require_execution_enabled=True)
            self._zero_exposure_guard()
        except Exception:
            self._control.quarantine(
                reason="FULL_POLICY_A_SOURCE_OR_RISK_REJECTED",
                now=effective_now,
            )
            raise

        check = self._mt5.order_check(mt5_request)
        if check is None:
            raise DemoSafetyError(f"order_check failed: {self._mt5.last_error()}")
        check_row = _record(check, "order_check")
        if int(check_row.get("retcode", -1)) != 0:
            raise DemoSafetyError(
                f"order_check rejected request: retcode={check_row.get('retcode')}"
            )

        self._ledger.reserve(request, now=effective_now)

        try:
            result = self._mt5.order_send(mt5_request)
        except Exception as exc:
            detail = f"order_send exception: {type(exc).__name__}: {exc}"
            self._mark_uncertain_and_quarantine(
                request_id=request.request_id,
                detail=detail,
                now=effective_now,
            )
            raise DemoSafetyError(
                "demo submission outcome is uncertain; reconcile before any retry"
            ) from exc

        if result is None:
            self._mark_uncertain_and_quarantine(
                request_id=request.request_id,
                detail=f"order_send returned no result: {self._mt5.last_error()}",
                now=effective_now,
            )
            raise DemoSafetyError(
                "demo submission outcome is uncertain; reconcile before any retry"
            )

        try:
            result_row = _record(result, "order_send")
            retcode = int(result_row.get("retcode", -1))
        except (ValueError, TypeError, DemoSafetyError) as exc:
            self._mark_uncertain_and_quarantine(
                request_id=request.request_id,
                detail="unparseable broker response after send",
                now=effective_now,
            )
            raise DemoSafetyError(
                "demo broker response unparseable; reconcile before any retry"
            ) from exc
        done_code = int(self._mt5.TRADE_RETCODE_DONE)
        if request.is_tpb_stop and retcode == getattr(
            self._mt5, "TRADE_RETCODE_PLACED", None
        ):
            # PLACED is not a fill. Any unparseable post-send observation is
            # uncertain, NOT an ordinary NO_TRADE: a real pending order may
            # already be accepted by the server.
            try:
                ticket = result_row.get("order")
                pending_rows = self._mt5.orders_get()
                positions_rows = self._mt5.positions_get()
                if (
                    type(ticket) is not int or ticket <= 0
                    or pending_rows is None or positions_rows is None
                    or len(tuple(positions_rows)) != 0
                    or len(tuple(pending_rows)) != 1
                ):
                    raise DemoSafetyError("pending STOP not singular/flat")
                pending = _record(tuple(pending_rows)[0], "pending order")
                if (
                    pending.get("ticket") != ticket
                    or pending.get("symbol") != "XAUUSD"
                    or pending.get("magic") != 260101
                    or pending.get("type") != mt5_request["type"]
                    or _decimal(pending.get("volume_initial"), "pending lots")
                    != request.volume_lots
                    or _decimal(pending.get("price_open"), "pending entry")
                    != request.entry_stop
                    or _decimal(pending.get("sl"), "pending stop") != request.stop_loss
                    or _decimal(pending.get("tp"), "pending target")
                    != request.take_profit
                    or pending.get("time_expiration") != mt5_request["expiration"]
                    or pending.get("state") != getattr(
                        self._mt5, "ORDER_STATE_PLACED", None
                    )
                ):
                    raise DemoSafetyError("pending STOP differs from intent")
                self._ledger.mark_acknowledged(
                    request.request_id, mt5_retcode=retcode,
                    order_ticket=str(ticket),
                )
            except Exception as exc:
                if self._ledger.status(request.request_id) == "PREPARED":
                    self._mark_uncertain_and_quarantine(
                        request_id=request.request_id,
                        detail="post-send pending STOP acknowledgment unreconciled",
                        now=effective_now,
                    )
                raise DemoSafetyError(
                    "pending STOP broker acknowledgment uncertain; no retry"
                ) from exc
            return {
                "status": "PENDING_ACKNOWLEDGED",
                "request_id": request.request_id,
                "symbol": "XAUUSD",
                "side": request.side.value,
                "volume_lots": str(request.volume_lots),
                "pending_order_ticket": ticket,
                "entry_stop": str(request.entry_stop),
                "protective_stop": str(request.stop_loss),
                "take_profit": str(request.take_profit),
                "expires_utc": request.expires_utc.isoformat(),
                "mt5_retcode": retcode,
                "risk_policy": risk.policy,
                "control_state": self._control.snapshot().state.value,
                "live_account_permitted": False,
            }

        if retcode != done_code or request.is_tpb_stop:
            self._mark_uncertain_and_quarantine(
                request_id=request.request_id,
                detail=f"non-final demo retcode={retcode}",
                now=effective_now,
            )
            raise DemoSafetyError(
                "demo submission was not definitively completed; reconcile before retry"
            )

        positions = self._mt5.positions_get()
        orders = self._mt5.orders_get()
        if positions is None or orders is None:
            self._mark_uncertain_and_quarantine(
                request_id=request.request_id,
                detail="post-submit exposure observation unavailable",
                now=effective_now,
            )
            raise DemoSafetyError("post-submit reconciliation unavailable")

        positions_tuple = tuple(positions)
        orders_tuple = tuple(orders)
        if len(positions_tuple) != 1 or orders_tuple:
            self._mark_uncertain_and_quarantine(
                request_id=request.request_id,
                detail=(
                    f"unexpected post-submit exposure: positions={len(positions_tuple)} "
                    f"orders={len(orders_tuple)}"
                ),
                now=effective_now,
            )
            raise DemoSafetyError("post-submit exposure failed bounded reconciliation")

        position = _record(positions_tuple[0], "position")
        if str(position.get("symbol") or "") != "XAUUSD":
            self._mark_uncertain_and_quarantine(
                request_id=request.request_id,
                detail="post-submit position symbol mismatch",
                now=effective_now,
            )
            raise DemoSafetyError("post-submit position identity mismatch")
        if _decimal(position.get("volume"), "position volume") > Decimal("0.01"):
            self._mark_uncertain_and_quarantine(
                request_id=request.request_id,
                detail="post-submit position volume exceeds 0.01",
                now=effective_now,
            )
            raise DemoSafetyError("post-submit position exceeded volume cap")
        if _decimal(position.get("sl"), "position stop loss") <= 0:
            self._mark_uncertain_and_quarantine(
                request_id=request.request_id,
                detail="post-submit protective stop missing",
                now=effective_now,
            )
            raise DemoSafetyError("post-submit protective stop missing")

        ticket = str(result_row.get("order") or result_row.get("deal") or "")
        self._ledger.mark_acknowledged(
            request.request_id,
            mt5_retcode=retcode,
            order_ticket=ticket,
        )

        return {
            "status": "ACKNOWLEDGED",
            "request_id": request.request_id,
            "symbol": "XAUUSD",
            "volume_lots": str(request.volume_lots),
            "side": request.side.value,
            "protective_stop": str(request.stop_loss),
            "mt5_retcode": retcode,
            "order_ticket": ticket,
            "risk_policy": risk.policy,
            "risk_reason_codes": list(risk.reason_codes),
            "control_state": self._control.snapshot().state.value,
            "open_positions": 1,
            "pending_orders": 0,
            "live_account_permitted": False,
        }
