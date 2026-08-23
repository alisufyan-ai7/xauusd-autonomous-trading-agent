"""Local, deterministic M1 verifier for a private read-only account snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from phase0.validation.margin_evidence.stress_artifact import admit_stress_artifact


D = Decimal
MIN_LEVEL = D("1000")
MIN_FREE = D("0.90")
STRESS_MULTIPLIER = D("2.0")


@dataclass(frozen=True)
class Result:
    status: str
    reason: str
    current_margin_level_percent: Decimal | None = None
    stressed_margin_level_percent: Decimal | None = None


def _decimal(value: Any, *, positive: bool = False) -> Decimal:
    try:
        parsed = D(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid decimal input") from exc
    if not parsed.is_finite() or (parsed <= 0 if positive else parsed < 0):
        raise ValueError("invalid decimal input")
    return parsed


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("snapshot timestamp lacks offset")
    return parsed.astimezone(timezone.utc)


def incremental_margin(snapshot: dict[str, Any], *, volume: Decimal) -> Decimal:
    """Independent calc-mode-0 estimate; unsupported currency paths reject."""
    if snapshot.get("trade_calc_mode") != 0:
        raise ValueError("unsupported trade calculation mode")
    leverage = _decimal(snapshot.get("leverage"), positive=True)
    contract = _decimal(snapshot.get("trade_contract_size"), positive=True)
    if volume <= 0:
        raise ValueError("volume must be positive")
    margin_currency = snapshot.get("currency_margin")
    account_currency = snapshot.get("account_currency")
    base_currency = snapshot.get("currency_base")
    profit_currency = snapshot.get("currency_profit")
    if margin_currency == account_currency:
        conversion = D("1")
    elif margin_currency == base_currency and account_currency == profit_currency:
        conversion = max(_decimal(snapshot.get("bid"), positive=True), _decimal(snapshot.get("ask"), positive=True))
    else:
        raise ValueError("unsupported or ambiguous margin conversion")
    return contract * volume / leverage * conversion


def evaluate_m1_snapshot(
    snapshot: dict[str, Any], stress_artifact: dict[str, Any], *, now_utc: datetime,
    expected_bundle_root_sha256: str, expected_stress_artifact_sha256: str,
    current_entry_cost: Any, volume: Decimal = D("0.01"), max_age_seconds: int = 30,
) -> Result:
    try:
        if now_utc.tzinfo is None or now_utc.utcoffset() != timedelta(0):
            raise ValueError("now_utc must have a zero UTC offset")
        if snapshot.get("tradeapi_disabled") is not True:
            return Result("FAIL_CLOSED", "EXTERNAL_PYTHON_TRADING_NOT_DISABLED")
        age = now_utc.astimezone(timezone.utc) - _utc(str(snapshot.get("observed_utc", "")))
        if age < timedelta(seconds=-2) or age > timedelta(seconds=max_age_seconds):
            return Result("FAIL_CLOSED", "SNAPSHOT_STALE_OR_FUTURE")
        equity = _decimal(snapshot.get("equity"), positive=True)
        used = _decimal(snapshot.get("margin"))
        increment = incremental_margin(snapshot, volume=volume)
        current_cost = _decimal(current_entry_cost)
        admission = admit_stress_artifact(
            stress_artifact, expected_bundle_root_sha256=expected_bundle_root_sha256,
            now_utc=now_utc,
        )
        if (admission.status != "ADMITTED_SPEC_ONLY"
                or admission.artifact_sha256 != expected_stress_artifact_sha256):
            return Result("FAIL_CLOSED", "STRESS_ARTIFACT_NOT_ADMITTED_OR_BOUND")
        stresses = dict(admission.adverse_stresses)
        spread = stresses["spread_stress"]
        slippage = stresses["slippage_stress"]
        gap = stresses["gap_stress"]
        cost = stresses["cost_stress"]
    except (AttributeError, KeyError, ValueError, TypeError):
        return Result("FAIL_CLOSED", "MISSING_INVALID_OR_AMBIGUOUS_INPUT")

    current_equity = equity - current_cost
    current_used = used + increment
    stressed_equity = current_equity - spread - slippage - gap - cost
    stressed_used = used + STRESS_MULTIPLIER * increment
    if current_equity <= 0 or stressed_equity <= 0:
        return Result("REJECT", "PROJECTED_EQUITY_NONPOSITIVE")
    current_level = D("Infinity") if current_used == 0 else current_equity / current_used * D("100")
    stressed_level = D("Infinity") if stressed_used == 0 else stressed_equity / stressed_used * D("100")
    current_free = current_equity - current_used
    stressed_free = stressed_equity - stressed_used
    if current_level < MIN_LEVEL or current_free < MIN_FREE * current_equity:
        return Result("REJECT", "M1_CURRENT_THRESHOLD_FAILED", current_level, stressed_level)
    if stressed_level < MIN_LEVEL or stressed_free < MIN_FREE * stressed_equity:
        return Result("REJECT", "M1_STRESSED_THRESHOLD_FAILED", current_level, stressed_level)
    return Result("PASS_SPEC_ONLY", "M1_PASS_NOT_TRADE_AUTHORITY", current_level, stressed_level)
