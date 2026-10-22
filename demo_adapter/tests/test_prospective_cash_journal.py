# ruff: noqa: I001
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from xauusd_demo.envelope import DemoSafetyError
from xauusd_demo.prospective_cash_journal import (
    MAGIC,
    CashDeal,
    CashObservation,
    ProspectiveDemoCashJournal,
)

DAY = datetime(2026, 10, 23, 12, tzinfo=UTC)
D = Decimal
FP = "9" * 64


def deposit() -> CashDeal:
    return CashDeal(
        deal_id="funding-1", time_utc=DAY - timedelta(days=2),
        kind="BALANCE", amount=D("10000"), magic=0,
    )


def observation(
    *, now: datetime = DAY, cash: Decimal = D("10000"),
    deals: tuple[CashDeal, ...] | None = None,
) -> CashObservation:
    return CashObservation(
        now, cash, cash, "USD", FP, True, 0, 0,
        (deposit(),) if deals is None else deals,
    )


def test_clean_prospective_demo_campaign_and_reopen_are_durable(tmp_path: Path) -> None:
    path = tmp_path / "cash.sqlite"
    with ProspectiveDemoCashJournal(path) as journal:
        first = journal.observe(observation())
        assert first.admitted
        assert first.initial_equity == D("10000")
        assert first.day_start_equity == D("10000")
        assert first.normalized_high_water == D("10000")
        assert first.no_order_authority
    with ProspectiveDemoCashJournal(path) as journal:
        second = journal.observe(observation(now=DAY + timedelta(seconds=10)))
        assert second.admitted
        assert second.observed_day_loss == 0
        assert second.no_order_authority


@pytest.mark.parametrize("bad", [
    {"broker_history_complete": False}, {"account_currency": "EUR"},
    {"positions_count": 1}, {"orders_count": 1},
    {"positions_count": -1}, {"balance": D("0")},
    {"equity": D("9999")}, {"account_fingerprint": "bad"},
])
def test_bad_initial_account_does_not_initialize(tmp_path: Path, bad: dict) -> None:
    with ProspectiveDemoCashJournal(tmp_path / "bad.sqlite") as journal:
        with pytest.raises(DemoSafetyError):
            journal.observe(replace(observation(), **bad))


def test_old_trade_history_cannot_be_called_a_fresh_inception(tmp_path: Path) -> None:
    oldtrade = CashDeal("before", DAY-timedelta(days=1), "SELL", D("-4"), MAGIC)
    with ProspectiveDemoCashJournal(tmp_path / "old.sqlite") as journal:
        with pytest.raises(DemoSafetyError, match="prior account trading"):
            journal.observe(observation(deals=(deposit(), oldtrade)))


def test_known_profitable_broker_closed_deal_is_cash_reconciled(tmp_path: Path) -> None:
    with ProspectiveDemoCashJournal(tmp_path / "profit.sqlite") as journal:
        journal.observe(observation())
        trade = CashDeal("deal-2", DAY + timedelta(minutes=2), "SELL", D("4"), MAGIC)
        after = observation(
            now=DAY + timedelta(minutes=4), cash=D("10004"),
            deals=(deposit(), trade),
        )
        result = journal.observe(after)
        assert result.admitted
        assert result.initial_equity == D("10000")
        assert result.normalized_high_water == D("10004")
        assert result.observed_drawdown == 0
        assert result.no_order_authority


def test_negative_realized_cash_trade_quarantines_persistently(tmp_path: Path) -> None:
    path = tmp_path / "loss.sqlite"
    loss = CashDeal("deal-3", DAY + timedelta(minutes=2), "SELL", D("-3"), MAGIC)
    with ProspectiveDemoCashJournal(path) as journal:
        journal.observe(observation())
        with pytest.raises(DemoSafetyError, match="losing trade"):
            journal.observe(observation(
                now=DAY + timedelta(minutes=3), cash=D("9997"),
                deals=(deposit(), loss),
            ))
    with ProspectiveDemoCashJournal(path) as journal:
        with pytest.raises(DemoSafetyError, match="quarantined"):
            journal.observe(observation(now=DAY + timedelta(minutes=5)))


@pytest.mark.parametrize("scenario", ["different_balance", "unowned", "funding", "missing_history", "timestamp_changed"])
def test_unreconciled_mutated_or_foreign_history_halts(
    tmp_path: Path, scenario: str
) -> None:
    with ProspectiveDemoCashJournal(tmp_path / "history.sqlite") as journal:
        journal.observe(observation())
        existing = deposit()
        now = DAY + timedelta(minutes=5)
        if scenario == "different_balance":
            obs = observation(now=now, cash=D("9998"))
        elif scenario == "unowned":
            foreign = CashDeal("foreign", now, "BUY", D("1"), 44)
            obs = observation(now=now, cash=D("10001"), deals=(existing, foreign))
        elif scenario == "funding":
            funding = CashDeal("deposit-2", now, "BALANCE", D("100"), 0)
            obs = observation(now=now, cash=D("10100"), deals=(existing, funding))
        elif scenario == "missing_history":
            obs = observation(now=now, deals=())
        else:
            changed = replace(existing, time_utc=existing.time_utc + timedelta(seconds=1))
            obs = observation(now=now, deals=(changed,))
        with pytest.raises(DemoSafetyError):
            journal.observe(obs)


def test_campaign_refuses_overlap_and_clock_rollback(tmp_path: Path) -> None:
    with ProspectiveDemoCashJournal(tmp_path / "clock.sqlite") as journal:
        journal.observe(observation())
        with pytest.raises(DemoSafetyError, match="clock rollback"):
            journal.observe(observation(now=DAY-timedelta(minutes=1)))
        with pytest.raises(DemoSafetyError, match="account changed"):
            journal.observe(replace(
                observation(now=DAY+timedelta(seconds=1)),
                account_fingerprint="e" * 64,
            ))


def test_no_simulated_trade_execution_method():
    assert not any(
        hasattr(ProspectiveDemoCashJournal, method)
        for method in ("order_send", "order_check", "execute", "enable_python_trading")
    )
