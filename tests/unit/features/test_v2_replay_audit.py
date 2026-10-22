from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from xauusd_agent.features.v2_replay_audit import (
    ReplayRegistration,
    ReplayTrade,
    assess_registered_replay,
)

BASE = datetime(2026, 10, 21, tzinfo=UTC)


def registration():
    return ReplayRegistration(
        dataset_sha256="a" * 64,
        strategy_sha256="b" * 64,
        source_rights_accepted=True,
        chronological_holdout_frozen=True,
        cost_distribution_empirically_calibrated=True,
        split_utc=BASE - timedelta(days=1),
        holdout_end_utc=BASE + timedelta(days=15),
    )


def trade(idx=0, gross="15"):
    at = BASE + timedelta(days=idx)
    return ReplayTrade(
        trade_id=f"synthetic-{idx}", opened_utc=at,
        closed_utc=at + timedelta(hours=2),
        initial_risk_cash=Decimal("10"),
        gross_pnl_cash=Decimal(gross),
        spread_cash=Decimal("1"), slippage_cash=Decimal("1"),
        commission_cash=Decimal("1"), swap_cash=Decimal("0"),
        gap_cash=Decimal("0"),
    )


def test_no_real_oos_ledger_cannot_be_called_profitable():
    audit = assess_registered_replay(registration=None, trades=())
    assert audit.status == "INSUFFICIENT_EVIDENCE"
    assert audit.net_expectancy_r is None
    assert audit.profitability_admitted is False
    assert audit.execution_permitted is False


def test_synthetic_cost_accounting_and_drawdown_are_descriptive():
    observed = [trade(0, "15"), trade(1, "-10"), trade(2, "15")]
    result = assess_registered_replay(registration=registration(), trades=observed)
    assert result.status == "DESCRIPTIVE_ONLY_NOT_STATISTICALLY_ADMITTED"
    assert result.net_expectancy_r == Decimal("0.366667")
    assert result.net_stress2_expectancy_r == Decimal("0.066667")
    assert result.max_drawdown_r == Decimal("-1.300000")
    assert result.normalized_ledger_sha256 is not None
    assert not result.profitability_admitted
    same = assess_registered_replay(registration=registration(), trades=observed)
    assert same.normalized_ledger_sha256 == result.normalized_ledger_sha256


def test_unknown_cost_license_and_unfrozen_holdout_veto():
    for changed in (
        {"source_rights_accepted": False},
        {"chronological_holdout_frozen": False},
        {"cost_distribution_empirically_calibrated": False},
    ):
        result = assess_registered_replay(
            registration=replace(registration(), **changed), trades=[trade()]
        )
        assert result.status == "INSUFFICIENT_EVIDENCE"


def test_duplicate_overlap_future_and_nonmonotonic_rejected():
    r = registration()
    candidates = (
        [trade(0), trade(0)],
        [trade(1), trade(0)],
        [trade(0), replace(trade(1), opened_utc=BASE + timedelta(hours=1))],
        [trade(20)],
    )
    for ledger in candidates:
        result = assess_registered_replay(registration=r, trades=ledger)
        assert result.status == "INSUFFICIENT_EVIDENCE"


def test_invalid_costs_initial_risk_and_dates_raise():
    with pytest.raises(ValueError, match="loss/cost"):
        replace(trade(), spread_cash=Decimal("-1"))
    with pytest.raises(ValueError, match="loss/cost"):
        replace(trade(), initial_risk_cash=Decimal("0"))
    with pytest.raises(ValueError, match="chronology"):
        replace(trade(), closed_utc=BASE)
