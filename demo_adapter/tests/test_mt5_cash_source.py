# ruff: noqa: I001
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from xauusd_demo.envelope import DemoSafetyError
from xauusd_demo import mt5_cash_source as source
from xauusd_demo.prospective_cash_journal import ProspectiveDemoCashJournal

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)
LOGIN = 12345678
DEMO_FP = hashlib.sha256(
    f"Exness Technologies Ltd|Exness-MT5Trial15|{LOGIN}|USD".encode()
).hexdigest()


class FakeCashMT5:
    DEAL_TYPE_BUY = 0
    DEAL_TYPE_SELL = 1
    DEAL_TYPE_BALANCE = 2
    DEAL_TYPE_CREDIT = 3

    def __init__(self) -> None:
        self.connected = True
        self.trade_mode = 0
        self.account_server = "Exness-MT5Trial15"
        self.account_balance = Decimal("10000")
        self.account_equity = Decimal("10000")
        self.positions: tuple[Any, ...] | None = ()
        self.orders: tuple[Any, ...] | None = ()
        self.extra_deal: dict[str, Any] | None = None
        self.mutate_inception = False
        self.calls: list[str] = []

    def terminal_info(self) -> dict[str, Any]:
        self.calls.append("terminal_info")
        return {"connected": self.connected, "tradeapi_disabled": True}

    def account_info(self) -> dict[str, Any]:
        self.calls.append("account_info")
        return {
            "trade_mode": self.trade_mode,
            "company": "Exness Technologies Ltd",
            "server": self.account_server,
            "currency": "USD",
            "login": LOGIN,
            "balance": self.account_balance,
            "equity": self.account_equity,
        }

    def positions_get(self) -> tuple[Any, ...] | None:
        self.calls.append("positions_get")
        return self.positions

    def orders_get(self) -> tuple[Any, ...] | None:
        self.calls.append("orders_get")
        return self.orders

    def history_deals_get(
        self, start: datetime, end: datetime,
    ) -> tuple[dict[str, Any], ...]:
        self.calls.append("history_deals_get")
        assert start.year == 2000 and end == NOW
        deposit = {
            "ticket": 10,
            "type": self.DEAL_TYPE_BALANCE, "magic": 0,
            "time_msc": int(datetime(2026, 9, 1, tzinfo=UTC).timestamp() * 1000),
            "profit": Decimal("9999" if self.mutate_inception else "10000"),
            "commission": 0, "fee": 0, "swap": 0,
        }
        return (
            (deposit, self.extra_deal)
            if self.extra_deal is not None else (deposit,)
        )


@pytest.fixture(autouse=True)
def accepted_test_fingerprint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(source, "_EXPECTED_SHA", DEMO_FP)


def test_real_api_cash_source_is_compatible_with_durable_policy_baseline(
    tmp_path: Path,
) -> None:
    fake = FakeCashMT5()
    obs = source.read_mt5_pro_demo_cash(fake, now=NOW)
    assert obs.broker_history_complete
    assert obs.balance == obs.equity == Decimal("10000")
    assert obs.account_fingerprint == DEMO_FP
    assert obs.positions_count == 0
    assert len(obs.broker_deals) == 1
    assert "history_deals_get" in fake.calls
    assert "order_send" not in fake.calls
    assert "order_check" not in fake.calls
    with ProspectiveDemoCashJournal(tmp_path / "cash.sqlite") as journal:
        result = journal.observe(obs)
        assert result.admitted
        assert result.initial_equity == Decimal("10000")
        assert result.no_order_authority


@pytest.mark.parametrize("change", [
    {"trade_mode": 2}, {"account_server": "Exness-Live"},
    {"account_balance": Decimal("9000")}, {"connected": False},
    {"positions": None}, {"orders": None},
    {"mutate_inception": True},
])
def test_untrusted_account_or_broker_cash_source_rejected(change: dict) -> None:
    fake = FakeCashMT5()
    for key, value in change.items():
        setattr(fake, key, value)
    with pytest.raises(DemoSafetyError):
        source.read_mt5_pro_demo_cash(fake, now=NOW)
    assert "order_send" not in fake.calls


def test_unowned_broker_history_and_unknown_cash_deal_rejected(tmp_path: Path) -> None:
    fake = FakeCashMT5()
    fake.extra_deal = {
        "ticket": 33,
        "type": fake.DEAL_TYPE_BUY,
        "magic": 17,
        "time_msc": int(NOW.timestamp() * 1000),
        "profit": Decimal("-5"), "commission": Decimal(0),
        "fee": Decimal(0), "swap": Decimal(0),
    }
    fake.account_balance = Decimal("9995")
    obs = source.read_mt5_pro_demo_cash(fake, now=NOW)
    assert obs.broker_deals[-1].magic == 17
    assert obs.balance == Decimal("9995")
    with ProspectiveDemoCashJournal(tmp_path / "foreign.sqlite") as journal:
        with pytest.raises(DemoSafetyError, match="prior account trading"):
            journal.observe(obs)
