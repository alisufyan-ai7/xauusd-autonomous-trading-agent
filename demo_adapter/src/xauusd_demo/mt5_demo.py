"""Demo-only MetaTrader 5 adapter with exact identity and risk-envelope guards."""

from __future__ import annotations

import hashlib
import importlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

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
        module: Any | None = None,
    ) -> None:
        identity.validate()
        policy.validate()
        self._identity = identity
        self._policy = policy
        self._ledger = ledger
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
        }

    def _build_request(self, request: DemoOrderRequest) -> dict[str, Any]:
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

    def submit_market_order(
        self,
        request: DemoOrderRequest,
        *,
        confirmation_phrase: str,
        activation_permit: DemoActivationPermit | None = None,
        risk_calibration: DemoRiskCalibration | None = None,
        now: datetime | None = None,
    ) -> dict[str, object]:
        if confirmation_phrase != SUBMISSION_CONFIRMATION:
            raise DemoSafetyError("exact demo submission confirmation token required")

        request.validate()
        _, account = self._identity_guard(require_execution_enabled=True)
        self._zero_exposure_guard()

        effective_now = now or datetime.now(UTC)
        if activation_permit is None:
            raise DemoSafetyError("demo execution requires an owner-gated activation permit")
        activation_permit.validate(now=effective_now)
        if activation_permit.account_id_sha256 != self._identity.account_id_sha256:
            raise DemoSafetyError("activation account fingerprint mismatch")
        if activation_permit.server != self._identity.server:
            raise DemoSafetyError("activation server mismatch")
        if activation_permit.max_daily_submissions != self._policy.max_daily_submissions:
            raise DemoSafetyError("activation daily submission budget mismatch")

        mt5_request = self._build_request(request)
        assert self._mt5 is not None

        margin_raw = self._mt5.order_calc_margin(
            int(mt5_request["type"]),
            "XAUUSD",
            float(request.volume_lots),
            float(mt5_request["price"]),
        )
        if margin_raw is None:
            raise DemoSafetyError(f"order_calc_margin failed: {self._mt5.last_error()}")
        risk = evaluate_bound_demo_risk(
            account=account,
            request=request,
            incremental_margin=_decimal(margin_raw, "incremental margin"),
            calibration=risk_calibration,
            expected_calibration_sha256=self._policy.risk_calibration_sha256,
        )

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
            self._ledger.mark_uncertain(
                request.request_id,
                detail=f"order_send exception: {type(exc).__name__}: {exc}",
            )
            raise DemoSafetyError(
                "demo submission outcome is uncertain; reconcile before any retry"
            ) from exc

        if result is None:
            self._ledger.mark_uncertain(
                request.request_id,
                detail=f"order_send returned no result: {self._mt5.last_error()}",
            )
            raise DemoSafetyError(
                "demo submission outcome is uncertain; reconcile before any retry"
            )

        result_row = _record(result, "order_send")
        done_code = int(self._mt5.TRADE_RETCODE_DONE)
        retcode = int(result_row.get("retcode", -1))

        if retcode != done_code:
            self._ledger.mark_uncertain(
                request.request_id,
                detail=f"non-final demo retcode={retcode}",
            )
            raise DemoSafetyError(
                "demo submission was not definitively completed; reconcile before retry"
            )

        positions = self._mt5.positions_get()
        orders = self._mt5.orders_get()
        if positions is None or orders is None:
            self._ledger.mark_uncertain(
                request.request_id,
                detail="post-submit exposure observation unavailable",
            )
            raise DemoSafetyError("post-submit reconciliation unavailable")

        positions_tuple = tuple(positions)
        orders_tuple = tuple(orders)
        if len(positions_tuple) != 1 or orders_tuple:
            self._ledger.mark_uncertain(
                request.request_id,
                detail=(
                    f"unexpected post-submit exposure: positions={len(positions_tuple)} "
                    f"orders={len(orders_tuple)}"
                ),
            )
            raise DemoSafetyError("post-submit exposure failed bounded reconciliation")

        position = _record(positions_tuple[0], "position")
        if str(position.get("symbol") or "") != "XAUUSD":
            self._ledger.mark_uncertain(
                request.request_id,
                detail="post-submit position symbol mismatch",
            )
            raise DemoSafetyError("post-submit position identity mismatch")
        if _decimal(position.get("volume"), "position volume") > Decimal("0.01"):
            self._ledger.mark_uncertain(
                request.request_id,
                detail="post-submit position volume exceeds 0.01",
            )
            raise DemoSafetyError("post-submit position exceeded volume cap")
        if _decimal(position.get("sl"), "position stop loss") <= 0:
            self._ledger.mark_uncertain(
                request.request_id,
                detail="post-submit protective stop missing",
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
            "open_positions": 1,
            "pending_orders": 0,
            "live_account_permitted": False,
        }
