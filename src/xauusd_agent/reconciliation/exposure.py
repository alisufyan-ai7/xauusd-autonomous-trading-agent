"""Broker-authoritative exposure comparison.

Mismatch and unknown exposure quarantine the runtime.  This module deliberately
offers no automatic close, cancel, mutation, or retry path.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from xauusd_agent.broker.observation import OrderObservation, PositionObservation


class ReconciliationStatus(StrEnum):
    MATCH_ZERO = "MATCH_ZERO"
    MATCH_KNOWN = "MATCH_KNOWN"
    MISMATCH = "MISMATCH"
    UNKNOWN_EXPOSURE = "UNKNOWN_EXPOSURE"
    INVALID_OBSERVATION = "INVALID_OBSERVATION"


class ReconciliationDisposition(StrEnum):
    CONTINUE = "CONTINUE"
    QUARANTINE_HUMAN_REVIEW = "QUARANTINE_HUMAN_REVIEW"


@dataclass(frozen=True, slots=True, order=True)
class ExpectedExposure:
    kind: str
    exposure_id: str
    symbol: str
    side: str
    volume_lots: Decimal


@dataclass(frozen=True, slots=True)
class ExposureReconciliation:
    status: ReconciliationStatus
    disposition: ReconciliationDisposition
    reason_codes: tuple[str, ...]
    expected: tuple[ExpectedExposure, ...]
    observed: tuple[ExpectedExposure, ...]
    automatic_close_permitted: bool = False

    def __post_init__(self) -> None:
        if self.automatic_close_permitted:
            raise ValueError("automatic unknown-exposure closure is prohibited")


def _valid_exposure(item: ExpectedExposure) -> bool:
    return (
        item.kind in {"POSITION", "ORDER"}
        and isinstance(item.exposure_id, str)
        and bool(item.exposure_id)
        and isinstance(item.symbol, str)
        and item.symbol.upper() == "XAUUSD"
        and isinstance(item.side, str)
        and item.side in {"BUY", "SELL"}
        and isinstance(item.volume_lots, Decimal)
        and item.volume_lots.is_finite()
        and item.volume_lots > 0
    )


def _normalize_observed(
    positions: tuple[PositionObservation, ...] | None,
    orders: tuple[OrderObservation, ...] | None,
) -> tuple[ExpectedExposure, ...] | None:
    if positions is None or orders is None:
        return None
    observed = tuple(
        ExpectedExposure(
            kind="POSITION",
            exposure_id=item.position_id,
            symbol=item.symbol.upper() if isinstance(item.symbol, str) else "",
            side=item.side.upper() if isinstance(item.side, str) else "",
            volume_lots=item.volume_lots,
        )
        for item in positions
    ) + tuple(
        ExpectedExposure(
            kind="ORDER",
            exposure_id=item.order_id,
            symbol=item.symbol.upper() if isinstance(item.symbol, str) else "",
            side=item.side.upper() if isinstance(item.side, str) else "",
            volume_lots=item.volume_lots,
        )
        for item in orders
    )
    return tuple(sorted(observed))


def reconcile_exposure(
    expected: tuple[ExpectedExposure, ...] | None,
    observed_positions: tuple[PositionObservation, ...] | None,
    observed_orders: tuple[OrderObservation, ...] | None,
) -> ExposureReconciliation:
    """Compare local expectation with broker observations; broker is authoritative."""

    observed = _normalize_observed(observed_positions, observed_orders)
    if expected is None or observed is None:
        return ExposureReconciliation(
            status=ReconciliationStatus.UNKNOWN_EXPOSURE,
            disposition=ReconciliationDisposition.QUARANTINE_HUMAN_REVIEW,
            reason_codes=("EXPOSURE_SNAPSHOT_MISSING",),
            expected=tuple() if expected is None else expected,
            observed=tuple() if observed is None else observed,
        )

    try:
        normalized_expected = tuple(sorted(expected))
    except (TypeError, AttributeError):
        return ExposureReconciliation(
            status=ReconciliationStatus.INVALID_OBSERVATION,
            disposition=ReconciliationDisposition.QUARANTINE_HUMAN_REVIEW,
            reason_codes=("EXPOSURE_VALUE_INVALID",),
            expected=tuple(),
            observed=observed,
        )
    if not all(_valid_exposure(item) for item in normalized_expected + observed):
        return ExposureReconciliation(
            status=ReconciliationStatus.INVALID_OBSERVATION,
            disposition=ReconciliationDisposition.QUARANTINE_HUMAN_REVIEW,
            reason_codes=("EXPOSURE_VALUE_INVALID",),
            expected=normalized_expected,
            observed=observed,
        )

    expected_identities = tuple((item.kind, item.exposure_id) for item in normalized_expected)
    observed_identities = tuple((item.kind, item.exposure_id) for item in observed)
    if len(set(expected_identities)) != len(expected_identities) or len(
        set(observed_identities)
    ) != len(observed_identities):
        return ExposureReconciliation(
            status=ReconciliationStatus.INVALID_OBSERVATION,
            disposition=ReconciliationDisposition.QUARANTINE_HUMAN_REVIEW,
            reason_codes=("DUPLICATE_EXPOSURE_IDENTITY",),
            expected=normalized_expected,
            observed=observed,
        )

    if normalized_expected == observed:
        zero = not observed
        return ExposureReconciliation(
            status=(ReconciliationStatus.MATCH_ZERO if zero else ReconciliationStatus.MATCH_KNOWN),
            disposition=ReconciliationDisposition.CONTINUE,
            reason_codes=("BROKER_EXPOSURE_MATCHES_EXPECTATION",),
            expected=normalized_expected,
            observed=observed,
        )

    reasons: list[str] = ["BROKER_EXPOSURE_MISMATCH"]
    if not normalized_expected and observed:
        reasons.append("UNEXPECTED_BROKER_EXPOSURE")
    if normalized_expected and not observed:
        reasons.append("EXPECTED_EXPOSURE_ABSENT_AT_BROKER")
    return ExposureReconciliation(
        status=ReconciliationStatus.MISMATCH,
        disposition=ReconciliationDisposition.QUARANTINE_HUMAN_REVIEW,
        reason_codes=tuple(reasons),
        expected=normalized_expected,
        observed=observed,
    )
