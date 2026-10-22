from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from test_demo_adapter import FakeMT5, fingerprint
from xauusd_demo import DemoSafetyError
from xauusd_demo import broker_money_readonly as money

NOW = datetime(2026, 10, 22, 12, tzinfo=UTC)


class MoneyFake(FakeMT5):
    SYMBOL_TRADE_MODE_FULL = 4

    def __init__(self) -> None:
        super().__init__()
        self.now = NOW
        self.cash_loss_multiplier = Decimal("1")
        self.profit_calls = 0
        self.margin_calls = 0
        self.check_calls = 0
        self.history_ok = True

    def account_info(self) -> object:
        base = super().account_info()
        return SimpleNamespace(**base.__dict__, balance=10000.0)

    def symbol_info(self, symbol: str) -> object:
        super().symbol_info(symbol)
        return SimpleNamespace(
            trade_mode=self.SYMBOL_TRADE_MODE_FULL,
            volume_min="0.01", volume_step="0.01",
            trade_tick_size="0.01", trade_tick_value_loss="1",
        )

    def symbol_info_tick(self, symbol: str) -> object:
        super().symbol_info_tick(symbol)
        return SimpleNamespace(
            bid=Decimal("3000"), ask=Decimal("3000.20"),
            time_msc=int(self.now.timestamp() * 1000),
        )

    def order_calc_profit(
        self, order_type: int, symbol: str, volume: float,
        price_open: float, price_close: float,
    ) -> float:
        self.profit_calls += 1
        assert symbol == "XAUUSD" and volume == 0.01
        result = (Decimal(str(price_close)) - Decimal(str(price_open))) * 100
        if order_type == self.ORDER_TYPE_SELL:
            result = -result
        return float(result * Decimal(str(volume)) * self.cash_loss_multiplier)

    def order_calc_margin(
        self, order_type: int, symbol: str, volume: float, price: float
    ) -> float:
        self.margin_calls += 1
        return 50.0

    def history_deals_get(
        self, start: datetime, end: datetime
    ) -> tuple[object, ...] | None:
        assert start.year == 2020 and end == self.now
        return () if self.history_ok else None

    def order_check(self, payload: dict[str, object]) -> object:
        self.check_calls += 1
        raise AssertionError("broker read-only probe must never order_check")


@pytest.fixture(autouse=True)
def stub_synthetic_account(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(money, "EXPECTED_ACCOUNT_SHA256", fingerprint())


def test_real_port_contract_synthetic_cash_margin_both_sides_no_orders() -> None:
    port = MoneyFake()
    result = money.inspect_real_demo_money(port, now=NOW)
    assert result["status"] == "REAL_BROKER_READONLY_MONEY_CAPTURE_NOT_ORDER_ADMISSION"
    assert result["historical_deal_count_unclassified"] == 0
    assert result["spread_usd_per_oz"] == "0.20"
    assert len(result["hypothetical_side_calculations"]) == 2
    assert all(
        side["broker_reference_stop_loss_cash_usd"] == "5.000"
        or Decimal(side["broker_reference_stop_loss_cash_usd"]) == Decimal("5")
        for side in result["hypothetical_side_calculations"]
    )
    assert port.profit_calls == port.margin_calls == 2
    assert port.check_calls == port.send_calls == 0
    assert result["execution_permitted"] is False
    assert result["full_policy_a_runtime_admitted"] is False
    assert "12345678" not in str(result)


@pytest.mark.parametrize("field,value", [
    ("tradeapi_disabled", False), ("connected", False),
    ("trade_mode", 2),
    ("positions", (object(),)), ("orders", (object(),)),
    ("positions", None), ("orders", None), ("history_ok", False),
])
def test_live_account_exposure_history_or_python_trade_enabled_vetoes(
    field: str, value: object
) -> None:
    port = MoneyFake()
    setattr(port, field, value)
    with pytest.raises(DemoSafetyError):
        money.inspect_real_demo_money(port, now=NOW)
    assert port.check_calls == port.send_calls == 0


def test_stale_quote_does_not_reach_profit_or_margin_calculation() -> None:
    port = MoneyFake()
    port.now = NOW - timedelta(minutes=2)
    with pytest.raises(DemoSafetyError, match="stale"):
        money.inspect_real_demo_money(port, now=NOW)
    assert port.profit_calls == port.margin_calls == port.send_calls == 0


def test_broker_cash_calc_unavailable_is_rejected() -> None:
    port = MoneyFake()
    port.cash_loss_multiplier = Decimal("0")
    with pytest.raises(DemoSafetyError, match="invalid"):
        money.inspect_real_demo_money(port, now=NOW)
    assert port.check_calls == port.send_calls == 0


def test_account_fingerprint_cannot_be_switched() -> None:
    port = MoneyFake()
    money.EXPECTED_ACCOUNT_SHA256 = "f" * 64
    with pytest.raises(DemoSafetyError, match="fingerprint"):
        money.inspect_real_demo_money(port, now=NOW)
    assert port.profit_calls == port.send_calls == 0


def test_reference_is_not_a_strategy_or_real_policy_a_authorization() -> None:
    port = MoneyFake()
    r = money.inspect_real_demo_money(port, now=NOW)
    assert r["strategy_direction_qualified"] is False
    assert r["event_guard_live_source_admitted"] is False
    assert r["history_cashflow_and_loss_streak_reconciled"] is False
    assert r["order_send_calls"] == 0
