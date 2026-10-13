"""Frozen Policy A / V1 / M1 risk evaluation.

This module is deliberately pure.  It has no broker dependency and no execution
capability.  All arithmetic is Decimal arithmetic supplied by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import StrEnum
from typing import Final, cast

MAX_VOLUME_LOTS: Final = Decimal("0.01")
MIN_MARGIN_LEVEL_PERCENT: Final = Decimal("1000")
MIN_FREE_MARGIN_TO_EQUITY: Final = Decimal("0.90")
STRESSED_INCREMENTAL_MARGIN_MULTIPLIER: Final = Decimal("2")


class ExposureKnowledge(StrEnum):
    """Authoritative knowledge of broker exposure at decision time."""

    CONFIRMED_ZERO = "CONFIRMED_ZERO"
    CONFIRMED_NONZERO = "CONFIRMED_NONZERO"
    UNKNOWN = "UNKNOWN"


class RiskDisposition(StrEnum):
    ALLOW = "ALLOW"
    REJECT = "REJECT"
    QUARANTINE = "QUARANTINE"


@dataclass(frozen=True, slots=True)
class PolicyAInput:
    """Inputs for one deterministic candidate-risk assessment.

    ``current_adverse_cost`` and ``stressed_adverse_cost`` are frozen,
    externally admitted spread/slippage/gap/cost deductions.  They are never
    estimated or defaulted here.
    """

    symbol: str | None
    requested_volume_lots: Decimal | None
    account_equity: Decimal | None
    account_free_margin: Decimal | None
    account_margin_used: Decimal | None
    incremental_margin: Decimal | None
    current_adverse_cost: Decimal | None
    stressed_adverse_cost: Decimal | None
    exposure: ExposureKnowledge | None
    fingerprint_matches: bool | None
    protective_stop_present: bool | None


@dataclass(frozen=True, slots=True)
class RiskEvaluation:
    policy: str
    disposition: RiskDisposition
    reason_codes: tuple[str, ...]
    requested_volume_lots: Decimal | None
    current_projected_equity: Decimal | None = None
    current_projected_free_margin: Decimal | None = None
    current_projected_margin_level_percent: Decimal | None = None
    stressed_projected_equity: Decimal | None = None
    stressed_projected_free_margin: Decimal | None = None
    stressed_projected_margin_level_percent: Decimal | None = None

    @property
    def allowed(self) -> bool:
        return self.disposition is RiskDisposition.ALLOW


def _invalid_decimal(value: Decimal | None) -> bool:
    return value is None or not isinstance(value, Decimal) or not value.is_finite()


def _quarantine(data: PolicyAInput, *reasons: str) -> RiskEvaluation:
    return RiskEvaluation(
        policy="POLICY_A_V1_M1",
        disposition=RiskDisposition.QUARANTINE,
        reason_codes=tuple(reasons),
        requested_volume_lots=data.requested_volume_lots,
    )


def evaluate_policy_a(data: PolicyAInput) -> RiskEvaluation:
    """Evaluate the frozen safety envelope; never coerce or fill missing data."""

    scalar_fields = {
        "requested_volume_lots": data.requested_volume_lots,
        "account_equity": data.account_equity,
        "account_free_margin": data.account_free_margin,
        "account_margin_used": data.account_margin_used,
        "incremental_margin": data.incremental_margin,
        "current_adverse_cost": data.current_adverse_cost,
        "stressed_adverse_cost": data.stressed_adverse_cost,
    }
    invalid = tuple(
        f"INVALID_{name.upper()}"
        for name, value in scalar_fields.items()
        if _invalid_decimal(value)
    )
    if invalid:
        return _quarantine(data, *invalid)
    if data.symbol is None or not isinstance(data.symbol, str) or not data.symbol.strip():
        return _quarantine(data, "INVALID_SYMBOL")
    if data.exposure is None or not isinstance(data.exposure, ExposureKnowledge):
        return _quarantine(data, "UNKNOWN_EXPOSURE")
    if data.exposure is ExposureKnowledge.UNKNOWN:
        return _quarantine(data, "UNKNOWN_EXPOSURE")
    if data.fingerprint_matches is not True:
        return _quarantine(data, "BROKER_FINGERPRINT_UNKNOWN_OR_MISMATCH")
    if data.protective_stop_present is not True:
        return _quarantine(data, "PROTECTIVE_STOP_UNKNOWN_OR_ABSENT")

    # Type narrowing follows the fail-closed validation above.
    volume = cast(Decimal, data.requested_volume_lots)
    equity = cast(Decimal, data.account_equity)
    free_margin = cast(Decimal, data.account_free_margin)
    margin_used = cast(Decimal, data.account_margin_used)
    incremental_margin = cast(Decimal, data.incremental_margin)
    current_cost = cast(Decimal, data.current_adverse_cost)
    stressed_cost = cast(Decimal, data.stressed_adverse_cost)

    static_rejections: list[str] = []
    if data.symbol.strip().upper() != "XAUUSD":
        static_rejections.append("SYMBOL_NOT_XAUUSD")
    if volume <= 0:
        static_rejections.append("VOLUME_NOT_POSITIVE")
    if volume > MAX_VOLUME_LOTS:
        static_rejections.append("V1_VOLUME_CAP_EXCEEDED")
    if equity <= 0:
        static_rejections.append("EQUITY_NOT_POSITIVE")
    if free_margin < 0 or margin_used < 0:
        static_rejections.append("INVALID_ACCOUNT_MARGIN_STATE")
    if incremental_margin <= 0:
        static_rejections.append("INCREMENTAL_MARGIN_NOT_POSITIVE")
    if current_cost < 0 or stressed_cost < 0:
        static_rejections.append("ADVERSE_COST_NEGATIVE")
    if stressed_cost < current_cost:
        static_rejections.append("STRESSED_COST_BELOW_CURRENT_COST")
    if data.exposure is ExposureKnowledge.CONFIRMED_NONZERO:
        static_rejections.append("EXISTING_EXPOSURE_REJECT_NEW_RISK")
    if static_rejections:
        return RiskEvaluation(
            policy="POLICY_A_V1_M1",
            disposition=RiskDisposition.REJECT,
            reason_codes=tuple(static_rejections),
            requested_volume_lots=volume,
        )

    with localcontext() as context:
        context.prec = 34
        current_equity = equity - current_cost
        current_margin = margin_used + incremental_margin
        current_free_margin = free_margin - current_cost - incremental_margin
        stressed_equity = equity - stressed_cost
        stressed_margin = margin_used + incremental_margin * STRESSED_INCREMENTAL_MARGIN_MULTIPLIER
        stressed_free_margin = (
            free_margin
            - stressed_cost
            - incremental_margin * STRESSED_INCREMENTAL_MARGIN_MULTIPLIER
        )

        current_level = (
            current_equity / current_margin * Decimal("100") if current_margin > 0 else None
        )
        stressed_level = (
            stressed_equity / stressed_margin * Decimal("100") if stressed_margin > 0 else None
        )

        reasons: list[str] = []
        if current_equity <= 0 or current_free_margin < 0 or current_level is None:
            reasons.append("M1_CURRENT_INSOLVENT_OR_UNDEFINED")
        else:
            if current_level < MIN_MARGIN_LEVEL_PERCENT:
                reasons.append("M1_CURRENT_MARGIN_LEVEL_BELOW_1000_PERCENT")
            if current_free_margin < current_equity * MIN_FREE_MARGIN_TO_EQUITY:
                reasons.append("M1_CURRENT_FREE_MARGIN_BELOW_90_PERCENT_EQUITY")

        if stressed_equity <= 0 or stressed_free_margin < 0 or stressed_level is None:
            reasons.append("M1_STRESSED_INSOLVENT_OR_UNDEFINED")
        else:
            if stressed_level < MIN_MARGIN_LEVEL_PERCENT:
                reasons.append("M1_STRESSED_MARGIN_LEVEL_BELOW_1000_PERCENT")
            if stressed_free_margin < stressed_equity * MIN_FREE_MARGIN_TO_EQUITY:
                reasons.append("M1_STRESSED_FREE_MARGIN_BELOW_90_PERCENT_EQUITY")

    return RiskEvaluation(
        policy="POLICY_A_V1_M1",
        disposition=(RiskDisposition.REJECT if reasons else RiskDisposition.ALLOW),
        reason_codes=tuple(reasons) if reasons else ("ALL_FROZEN_CONTROLS_PASS",),
        requested_volume_lots=volume,
        current_projected_equity=current_equity,
        current_projected_free_margin=current_free_margin,
        current_projected_margin_level_percent=current_level,
        stressed_projected_equity=stressed_equity,
        stressed_projected_free_margin=stressed_free_margin,
        stressed_projected_margin_level_percent=stressed_level,
    )
