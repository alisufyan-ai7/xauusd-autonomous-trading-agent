"""Offline-verifiable DEMO_CANARY_ONLY USD loss-to-stop and M1 veto.

Not a real-money calibration or authorization. All inputs MUST be collected
directly from one reconciled XAUUSD DEMO broker snapshot by the caller.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from typing import Any

from xauusd_agent.risk.policy_a import (
    ExposureKnowledge, PolicyAInput, evaluate_policy_a,
)

from .envelope import DemoSafetyError

MAX_LOTS = Decimal("0.01")
RISK_RATE = Decimal("0.0025")
RISK_ABSOLUTE_CAP = Decimal("25")
ALLOCATION_CAP = Decimal("10000")
# Conservative deterministic engineering assumptions; NOT empirical calibration.
SLIPPAGE_PRICE_BUFFER = Decimal("0.50")
GAP_PRICE_BUFFER = Decimal("2.00")
COMMISSION_BUFFER_USD = Decimal("5.00")
SWAP_BUFFER_USD = Decimal("2.00")
MAX_TICK_AGE_MSEC = 5000
MAX_SPREAD_PRICE = Decimal("1.00")
METADATA_REL_TOL = Decimal("0.01")


def d(value: Any, label: str) -> Decimal:
    try:
        if isinstance(value, bool) or value is None:
            raise ValueError("missing/bool")
        number = Decimal(str(value))
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise DemoSafetyError("UNKNOWN_" + label) from exc
    if not number.is_finite():
        raise DemoSafetyError("NONFINITE_" + label)
    return number


@dataclass(frozen=True, slots=True)
class CanaryRiskEvidence:
    symbol: str
    side: str
    lots: Decimal
    stop: Decimal
    bid: Decimal
    ask: Decimal
    tick_msec: int
    now_msec: int
    tick_size: Decimal
    tick_value_loss: Decimal
    contract_size: Decimal
    currency_profit: str
    volume_min: Decimal
    volume_max: Decimal
    volume_step: Decimal
    point: Decimal
    stops_level: int
    equity: Decimal
    balance: Decimal
    free_margin: Decimal
    margin_used: Decimal
    incremental_margin: Decimal
    # Independent broker-side profit-at-stop (already negative) for the
    # observed market entry; no order placement or order_check needed here.
    broker_stop_profit_usd: Decimal


@dataclass(frozen=True, slots=True)
class CanaryRiskDecision:
    risk_cap_usd: Decimal
    worst_loss_to_stop_usd: Decimal
    price_loss_usd: Decimal
    stressed_deduction_usd: Decimal
    worst_entry: Decimal
    current_margin_level_percent: Decimal
    stressed_margin_level_percent: Decimal
    classification: str = "DEMO_CANARY_ONLY_NOT_REAL_MONEY_CALIBRATION"


def _up_cent(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_CEILING)


def evaluate_canary_risk(ev: CanaryRiskEvidence) -> CanaryRiskDecision:
    """Hard fail closed: complete USD loss-to-stop, broker cash metadata, M1."""
    if ev.symbol != "XAUUSD" or ev.side not in ("BUY", "SELL"):
        raise DemoSafetyError("CANARY_SYMBOL_OR_SIDE_MISMATCH")
    fields = (
        "lots", "stop", "bid", "ask", "tick_size", "tick_value_loss",
        "contract_size", "volume_min", "volume_max", "volume_step", "point",
        "equity", "balance", "free_margin", "margin_used", "incremental_margin",
        "broker_stop_profit_usd",
    )
    if any(type(getattr(ev, k)) is not Decimal or
           not getattr(ev, k).is_finite() for k in fields):
        raise DemoSafetyError("CANARY_NON_DECIMAL_OR_NONFINITE")
    if (
        ev.lots != MAX_LOTS or ev.lots < ev.volume_min or
        ev.lots > ev.volume_max or ev.volume_step <= 0 or
        (ev.lots - ev.volume_min) % ev.volume_step != 0
    ):
        raise DemoSafetyError("CANARY_LOT_OR_VOLUME_GRID")
    if (min(ev.tick_size, ev.tick_value_loss, ev.contract_size, ev.point,
            ev.bid, ev.ask, ev.equity, ev.balance, ev.incremental_margin) <= 0 or
            ev.free_margin < 0 or ev.margin_used < 0):
        raise DemoSafetyError("CANARY_INVALID_NUMERICS")
    if ev.currency_profit != "USD":
        raise DemoSafetyError("CANARY_UNPROVEN_USD_TICK_CONVERSION")
    if not isinstance(ev.tick_msec, int) or not isinstance(ev.now_msec, int):
        raise DemoSafetyError("CANARY_UNVERIFIED_TICK_CLOCK")
    age = ev.now_msec - ev.tick_msec
    if age < 0 or age > MAX_TICK_AGE_MSEC:
        raise DemoSafetyError("CANARY_STALE_OR_FUTURE_QUOTE")
    if ev.ask <= ev.bid or ev.ask - ev.bid > MAX_SPREAD_PRICE:
        raise DemoSafetyError("CANARY_INVERTED_OR_EXCESSIVE_SPREAD")
    if ev.stops_level < 0 or ev.stops_level > 100000:
        raise DemoSafetyError("CANARY_UNPROVEN_STOP_LEVEL")
    if (ev.stop / ev.tick_size) != (
        ev.stop / ev.tick_size
    ).to_integral_value():
        raise DemoSafetyError("CANARY_STOP_OFF_TICK_GRID")
    if ev.side == "BUY":
        if ev.stop >= ev.bid - ev.point * ev.stops_level:
            raise DemoSafetyError("CANARY_BUY_STOP_NOT_PROTECTIVE")
        worst_entry = ev.ask + SLIPPAGE_PRICE_BUFFER
        distance = worst_entry - ev.stop + GAP_PRICE_BUFFER
    else:
        if ev.stop <= ev.ask + ev.point * ev.stops_level:
            raise DemoSafetyError("CANARY_SELL_STOP_NOT_PROTECTIVE")
        worst_entry = ev.bid - SLIPPAGE_PRICE_BUFFER
        distance = ev.stop - worst_entry + GAP_PRICE_BUFFER
    if distance <= 0 or worst_entry <= 0:
        raise DemoSafetyError("CANARY_INVALID_STOP_DISTANCE")
    # XAUUSD profit currency must be USD. Verify broker-reported loss-tick
    # value against independent XAU contract-ounce USD arithmetic.
    expected_loss_tick = ev.contract_size * ev.tick_size
    if (abs(ev.tick_value_loss - expected_loss_tick) /
            expected_loss_tick > METADATA_REL_TOL):
        raise DemoSafetyError("CANARY_TICK_VALUE_CONTRACT_MISMATCH")
    observed_distance = ((ev.ask - ev.stop) if ev.side == "BUY"
                         else (ev.stop - ev.bid))
    expected_broker_loss = observed_distance * ev.contract_size * ev.lots
    if ev.broker_stop_profit_usd >= 0:
        raise DemoSafetyError("CANARY_BROKER_STOP_PROFIT_NOT_NEGATIVE")
    if (abs(-ev.broker_stop_profit_usd - expected_broker_loss) /
            expected_broker_loss > METADATA_REL_TOL):
        raise DemoSafetyError("CANARY_BROKER_CALC_PROFIT_MISMATCH")

    ticks = (distance / ev.tick_size).to_integral_value(rounding=ROUND_CEILING)
    price_loss = _up_cent(ticks * ev.tick_value_loss * ev.lots)
    worst_loss = _up_cent(
        price_loss + COMMISSION_BUFFER_USD + SWAP_BUFFER_USD
    )
    cap = min(
        RISK_ABSOLUTE_CAP,
        _up_cent(min(ev.equity, ev.balance, ALLOCATION_CAP) * RISK_RATE),
    )
    if cap <= 0 or worst_loss > cap:
        raise DemoSafetyError("CANARY_FULL_LOSS_TO_STOP_EXCEEDS_POLICY_A_CAP")
    # Treat one entire worst-stop loss as the adverse-cost deduction for M1.
    # Stressed M1 doubles the loss deduction AND incremental margin.
    margin = evaluate_policy_a(PolicyAInput(
        symbol="XAUUSD", requested_volume_lots=ev.lots,
        account_equity=ev.equity, account_free_margin=ev.free_margin,
        account_margin_used=ev.margin_used,
        incremental_margin=ev.incremental_margin,
        current_adverse_cost=worst_loss,
        stressed_adverse_cost=worst_loss * 2,
        exposure=ExposureKnowledge.CONFIRMED_ZERO,
        fingerprint_matches=True, protective_stop_present=True,
    ))
    if not margin.allowed or margin.current_projected_margin_level_percent is None:
        raise DemoSafetyError("CANARY_CURRENT_OR_STRESSED_POLICY_A_M1_DENIED")
    if margin.stressed_projected_margin_level_percent is None:
        raise DemoSafetyError("CANARY_STRESSED_MARGIN_UNDEFINED")
    return CanaryRiskDecision(
        risk_cap_usd=cap, worst_loss_to_stop_usd=worst_loss,
        price_loss_usd=price_loss, stressed_deduction_usd=worst_loss * 2,
        worst_entry=worst_entry,
        current_margin_level_percent=margin.current_projected_margin_level_percent,
        stressed_margin_level_percent=margin.stressed_projected_margin_level_percent,
    )
