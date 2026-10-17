"""Binding between demo execution and the deterministic production Risk Governor."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from xauusd_agent.risk import ExposureKnowledge, PolicyAInput, RiskEvaluation, evaluate_policy_a

from .envelope import DemoOrderRequest, DemoSafetyError


@dataclass(frozen=True, slots=True)
class DemoRiskCalibration:
    calibration_id: str
    current_adverse_cost: Decimal
    stressed_adverse_cost: Decimal

    def validate(self) -> None:
        if not self.calibration_id.strip() or len(self.calibration_id) > 128:
            raise DemoSafetyError("risk calibration id must contain 1..128 characters")
        for label, value in (
            ("current_adverse_cost", self.current_adverse_cost),
            ("stressed_adverse_cost", self.stressed_adverse_cost),
        ):
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise DemoSafetyError(f"{label} must be a finite nonnegative Decimal")
        if self.stressed_adverse_cost < self.current_adverse_cost:
            raise DemoSafetyError("stressed adverse cost cannot be below current adverse cost")

    def sha256(self) -> str:
        self.validate()
        payload = json.dumps(
            {
                "calibration_id": self.calibration_id,
                "current_adverse_cost": str(self.current_adverse_cost),
                "stressed_adverse_cost": str(self.stressed_adverse_cost),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(payload).hexdigest()


def _decimal(value: Any, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise DemoSafetyError(f"{label} is not decimal") from exc
    if not result.is_finite():
        raise DemoSafetyError(f"{label} is not finite")
    return result


def evaluate_bound_demo_risk(
    *,
    account: Mapping[str, Any],
    request: DemoOrderRequest,
    incremental_margin: Decimal,
    calibration: DemoRiskCalibration | None,
    expected_calibration_sha256: str | None,
) -> RiskEvaluation:
    if calibration is None or expected_calibration_sha256 is None:
        raise DemoSafetyError("demo execution requires a hash-bound risk calibration")
    if calibration.sha256() != expected_calibration_sha256:
        raise DemoSafetyError("risk calibration hash mismatch")

    evaluation = evaluate_policy_a(
        PolicyAInput(
            symbol=request.symbol,
            requested_volume_lots=request.volume_lots,
            account_equity=_decimal(account.get("equity"), "account equity"),
            account_free_margin=_decimal(account.get("margin_free"), "account free margin"),
            account_margin_used=_decimal(account.get("margin"), "account margin"),
            incremental_margin=incremental_margin,
            current_adverse_cost=calibration.current_adverse_cost,
            stressed_adverse_cost=calibration.stressed_adverse_cost,
            exposure=ExposureKnowledge.CONFIRMED_ZERO,
            fingerprint_matches=True,
            protective_stop_present=True,
        )
    )
    if not evaluation.allowed:
        raise DemoSafetyError(
            "deterministic Risk Governor denied demo request: "
            + ",".join(evaluation.reason_codes)
        )
    return evaluation
