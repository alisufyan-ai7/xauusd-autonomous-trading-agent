"""Nonexecuting cost-aware replay accounting, NOT strategy admission.

Actual historical XAUUSD bars/ticks and full frozen TPB candidate/exit stream
have not been admitted to this PR. Synthetic examples CANNOT establish
profitability. Even a positive expectancy is only descriptive until the
frozen P0-REPLAY acceptance tests and independently protected OOS are run.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal

from xauusd_agent.market.models import _require_utc


@dataclass(frozen=True, slots=True)
class ReplayRegistration:
    dataset_sha256: str
    strategy_sha256: str
    source_rights_accepted: bool
    chronological_holdout_frozen: bool
    cost_distribution_empirically_calibrated: bool
    split_utc: datetime
    holdout_end_utc: datetime

    def __post_init__(self) -> None:
        for name in ("dataset_sha256", "strategy_sha256"):
            value = getattr(self, name)
            if len(value) != 64 or any(x not in "0123456789abcdef" for x in value):
                raise ValueError(f"{name} must be a SHA256")
        _require_utc(self.split_utc, "split_utc")
        _require_utc(self.holdout_end_utc, "holdout_end_utc")
        if self.holdout_end_utc <= self.split_utc:
            raise ValueError("invalid chronological holdout")


@dataclass(frozen=True, slots=True)
class ReplayTrade:
    trade_id: str
    opened_utc: datetime
    closed_utc: datetime
    initial_risk_cash: Decimal
    gross_pnl_cash: Decimal
    spread_cash: Decimal
    slippage_cash: Decimal
    commission_cash: Decimal
    swap_cash: Decimal
    gap_cash: Decimal

    def __post_init__(self) -> None:
        _require_utc(self.opened_utc, "opened_utc")
        _require_utc(self.closed_utc, "closed_utc")
        if not self.trade_id or self.closed_utc <= self.opened_utc:
            raise ValueError("trade chronology invalid")
        values = (
            self.initial_risk_cash, self.gross_pnl_cash, self.spread_cash,
            self.slippage_cash, self.commission_cash, self.swap_cash, self.gap_cash,
        )
        if any(not v.is_finite() for v in values):
            raise ValueError("missing or nonfinite cash cost")
        if self.initial_risk_cash <= 0 or any(v < 0 for v in values[2:]):
            raise ValueError("invalid loss/cost basis")

    def r(self, *, stress_cost_multiple: Decimal = Decimal(1)) -> Decimal:
        variable = sum(
            (self.spread_cash, self.slippage_cash, self.commission_cash,
             self.swap_cash, self.gap_cash),
            Decimal(0),
        )
        return (self.gross_pnl_cash - variable * stress_cost_multiple) / self.initial_risk_cash


@dataclass(frozen=True, slots=True)
class ReplayAudit:
    status: str
    reasons: tuple[str, ...]
    trade_count: int
    net_expectancy_r: Decimal | None
    net_stress2_expectancy_r: Decimal | None
    max_drawdown_r: Decimal | None
    normalized_ledger_sha256: str | None
    profitability_admitted: bool = False
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.profitability_admitted or self.execution_permitted:
            raise ValueError("descriptive replay cannot grant profitability/trading approval")


def assess_registered_replay(
    *, registration: ReplayRegistration | None, trades: Sequence[ReplayTrade]
) -> ReplayAudit:
    reasons = []
    if registration is None:
        reasons.append("REGISTERED_DATASET_AND_SPLITS_MISSING")
    else:
        if not registration.source_rights_accepted:
            reasons.append("DATA_RIGHTS_UNVERIFIED")
        if not registration.chronological_holdout_frozen:
            reasons.append("CHRONOLOGICAL_HOLDOUT_UNFROZEN")
        if not registration.cost_distribution_empirically_calibrated:
            reasons.append("BROKER_COST_DISTRIBUTION_UNVERIFIED")
        if any(
            trade.opened_utc < registration.split_utc
            or trade.closed_utc > registration.holdout_end_utc
            for trade in trades
        ):
            reasons.append("TRADE_OUTSIDE_REGISTERED_HOLDOUT")
    if not trades:
        reasons.append("NO_OBSERVED_HOLDOUT_TRADES")
    if len({t.trade_id for t in trades}) != len(trades):
        reasons.append("DUPLICATE_TRADE_ID")
    if any(
        left.closed_utc > right.opened_utc
        for left, right in zip(trades, trades[1:], strict=False)
    ):
        reasons.append("UNRECONCILED_OVERLAPPING_POSITIONS")
    if any(
        left.opened_utc >= right.opened_utc
        for left, right in zip(trades, trades[1:], strict=False)
    ):
        reasons.append("NONMONOTONIC_TRADE_ORDER")
    if reasons:
        return ReplayAudit(
            "INSUFFICIENT_EVIDENCE", tuple(sorted(set(reasons))),
            len(trades), None, None, None, None,
        )
    r_values = [t.r() for t in trades]
    stress = [t.r(stress_cost_multiple=Decimal(2)) for t in trades]
    n = Decimal(len(trades))
    equity = Decimal(0)
    peak = Decimal(0)
    worst = Decimal(0)
    for r_value in r_values:
        equity += r_value
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    normalized = "\n".join(
        "|".join(
            (t.trade_id, t.opened_utc.isoformat(), t.closed_utc.isoformat(),
             str(t.initial_risk_cash), str(t.gross_pnl_cash),
             str(t.spread_cash), str(t.slippage_cash),
             str(t.commission_cash), str(t.swap_cash), str(t.gap_cash))
        ) for t in trades
    ).encode("ascii")
    rounding = Decimal("0.000001")
    return ReplayAudit(
        "DESCRIPTIVE_ONLY_NOT_STATISTICALLY_ADMITTED",
        ("NEEDS_BLOCK_BOOTSTRAP_10000_DSR_PBO_FOLDS_CONCENTRATION_AND_STRESS",),
        len(trades),
        (sum(r_values) / n).quantize(rounding, rounding=ROUND_HALF_EVEN),
        (sum(stress) / n).quantize(rounding, rounding=ROUND_HALF_EVEN),
        worst.quantize(rounding, rounding=ROUND_HALF_EVEN),
        hashlib.sha256(normalized).hexdigest(),
    )
