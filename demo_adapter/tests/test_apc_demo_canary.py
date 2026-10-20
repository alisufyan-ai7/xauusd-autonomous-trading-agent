"""Synthetic only. No MT5 import, terminal attachment or real order access."""
# ruff: noqa: I001
from __future__ import annotations

import hashlib
import runpy
import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

import xauusd_demo.canary_lifecycle as canary
from xauusd_demo.canary_lifecycle import (
    CANARY_APC_TOKEN, CanaryJournal, DemoCanaryLifecycle,
)
from xauusd_demo.canary_policy import CanaryRiskEvidence, evaluate_canary_risk
from xauusd_demo.control import ARM_CONFIRMATION, DemoControlState, DemoControlStore
from xauusd_demo.envelope import (
    DemoActivationPermit, DemoOrderRequest, DemoSafetyError, DemoSide,
)

NOW = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)
TICK_TIME = int(NOW.timestamp() * 1000)
LOGIN = 1234567


def fingerprint() -> str:
    return hashlib.sha256(
        f"{canary.BROKER}|{canary.SERVER}|{LOGIN}|{canary.CURRENCY}".encode()
    ).hexdigest()


def permit() -> DemoActivationPermit:
    return DemoActivationPermit(
        activation_id="TEST-APC-CANARY",
        account_id_sha256=fingerprint(),
        server=canary.SERVER, max_daily_submissions=1,
        not_before_utc=NOW - timedelta(minutes=1),
        expires_utc=NOW + timedelta(minutes=15),
    )


def request(*, side: DemoSide = DemoSide.BUY,
            stop: str = "1990.00") -> DemoOrderRequest:
    return DemoOrderRequest(
        request_id=str(uuid.uuid4()), symbol="XAUUSD",
        side=side, volume_lots=Decimal("0.01"),
        stop_loss=Decimal(stop),
    )


def evidence() -> CanaryRiskEvidence:
    return CanaryRiskEvidence(
        symbol="XAUUSD", side="BUY", lots=Decimal("0.01"),
        stop=Decimal("1990.00"), bid=Decimal("2000.00"),
        ask=Decimal("2000.20"), tick_msec=TICK_TIME, now_msec=TICK_TIME,
        tick_size=Decimal("0.01"), tick_value_loss=Decimal("1.00"),
        contract_size=Decimal("100"), currency_profit="USD",
        volume_min=Decimal("0.01"), volume_max=Decimal("100"),
        volume_step=Decimal("0.01"), point=Decimal("0.01"),
        stops_level=10, equity=Decimal("10000"), balance=Decimal("10000"),
        free_margin=Decimal("10000"), margin_used=Decimal("0"),
        incremental_margin=Decimal("5.00"),
        broker_stop_profit_usd=Decimal("-10.20"),
    )


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    SYMBOL_TRADE_MODE_FULL = 4
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    TRADE_ACTION_DEAL = 1
    ORDER_TIME_GTC = 0
    TRADE_RETCODE_DONE = 10009
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1

    def __init__(self) -> None:
        self.live = False
        self.tradeapi_disabled = False
        self.pos: tuple[dict[str, object], ...] = ()
        self.pending: tuple[object, ...] = ()
        self.calls = 0
        self.fail_send = False
        self.bad_tick = False
        self.bad_position_side = False
        self.bad_magic = False
        self.missing_deal = False
        self.bad_open_price = False

    def terminal_info(self) -> dict[str, object]:
        return {"connected": True, "tradeapi_disabled": self.tradeapi_disabled}

    def account_info(self) -> dict[str, object]:
        return {
            "trade_mode": 2 if self.live else self.ACCOUNT_TRADE_MODE_DEMO,
            "company": canary.BROKER, "server": canary.SERVER,
            "currency": canary.CURRENCY, "login": LOGIN,
            "equity": 10000.0, "balance": 10000.0,
            "margin_free": 10000.0, "margin": 0.0,
        }

    def positions_get(self) -> tuple[dict[str, object], ...]:
        return self.pos

    def orders_get(self) -> tuple[object, ...]:
        return self.pending

    def symbol_info(self, symbol: str) -> dict[str, object]:
        assert symbol == "XAUUSD"
        return {
            "name": "XAUUSD", "trade_mode": 4,
            "currency_profit": "USD",
            "volume_min": 0.01, "volume_max": 100.0,
            "volume_step": 0.01, "point": 0.01,
            "trade_tick_size": 0.01, "trade_tick_value_loss": 1.0,
            "trade_contract_size": 100, "trade_stops_level": 10,
            "filling_mode": 1,
        }

    def symbol_info_tick(self, symbol: str) -> dict[str, object]:
        assert symbol == "XAUUSD"
        return {
            "bid": 2000.0, "ask": 2000.2,
            "time_msc": TICK_TIME - (9000 if self.bad_tick else 0),
        }

    def order_calc_margin(self, *args: object) -> float:
        return 5.0

    def order_calc_profit(
        self, typ: int, symbol: str, volume: float,
        entry: float, stop: float,
    ) -> float:
        assert symbol == "XAUUSD"
        assert volume == 0.01
        return (stop - entry if typ == 0 else entry - stop) * 100 * volume

    def order_check(self, payload: dict[str, object]) -> dict[str, int]:
        return {"retcode": 0}

    def order_send(self, payload: dict[str, object]) -> dict[str, int] | None:
        self.calls += 1
        if self.fail_send:
            return None
        if "position" in payload:
            self.pos = ()
        else:
            self.pos = ({
                "ticket": 77, "symbol": "XAUUSD", "volume": 0.01,
                "sl": payload["sl"],
                "type": 1 if self.bad_position_side else (0 if payload["type"] == 0 else 1),
                "magic": 0 if self.bad_magic else canary.MAGIC,
                "price_open": (2002.0 if self.bad_open_price else payload["price"]),
            },)
        return {"retcode": self.TRADE_RETCODE_DONE,
                "deal": 0 if self.missing_deal else 111}


def test_deterministic_full_stop_loss_includes_all_buffers() -> None:
    result = evaluate_canary_risk(evidence())
    assert result.price_loss_usd == Decimal("12.70")
    assert result.worst_loss_to_stop_usd == Decimal("19.70")
    assert result.risk_cap_usd == Decimal("25.00")
    assert result.stressed_deduction_usd == Decimal("39.40")
    assert result.current_margin_level_percent >= Decimal("1000")
    assert result.stressed_margin_level_percent >= Decimal("1000")


@pytest.mark.parametrize(
    ("replacement", "reason"),
    [
        ({"stop": Decimal("1980"), "broker_stop_profit_usd": Decimal("-20.20")},
         "LOSS_TO_STOP"),
        ({"tick_value_loss": Decimal("0.10")}, "TICK_VALUE_CONTRACT"),
        ({"tick_msec": TICK_TIME - 9000}, "STALE"),
        ({"currency_profit": "EUR"}, "USD_TICK"),
        ({"lots": Decimal("0.02")}, "LOT_OR_VOLUME"),
        ({"incremental_margin": Decimal("5000")}, "POLICY_A_M1"),
        ({"stop": Decimal("2000.05")}, "STOP_NOT_PROTECTIVE"),
        ({"ask": Decimal("2002")}, "SPREAD"),
    ],
)
def test_unsafe_risk_sources_fail_closed(
    replacement: dict[str, object], reason: str,
) -> None:
    with pytest.raises(DemoSafetyError, match=reason):
        evaluate_canary_risk(replace(evidence(), **replacement))


def _setup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> tuple[FakeMT5, DemoControlStore, CanaryJournal, DemoCanaryLifecycle]:
    monkeypatch.setattr(canary, "ACCOUNT_SHA256", fingerprint())
    mt5 = FakeMT5()
    ctrl = DemoControlStore(tmp_path / "control.sqlite3")
    journal = CanaryJournal(tmp_path / "canary.sqlite3")
    ctrl.arm(
        permit=permit(), identity=canary.exact_demo_identity(),
        now=NOW, confirmation_phrase=ARM_CONFIRMATION,
    )
    return mt5, ctrl, journal, DemoCanaryLifecycle(
        mt5, ctrl, journal, clock=lambda: NOW
    )


def test_one_entry_one_close_persistently_killed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    mt5, ctrl, journal, lifecycle = _setup(monkeypatch, tmp_path)
    try:
        result = lifecycle.open_once(
            request=request(), permit=permit(), now=NOW, apc_token=CANARY_APC_TOKEN,
                approved_price_limit=Decimal("2001.00")
        )
        assert result.status == "OPEN_RECONCILED"
        assert result.ticket == "77"
        assert result.worst_loss_usd == Decimal("19.70")
        assert journal.stage() == "OPEN"
        assert mt5.calls == 1
        assert lifecycle.close_once(
            permit=permit(), now=NOW, apc_token=CANARY_APC_TOKEN
        ) == "CLOSED_FLAT_KILLED"
        assert journal.stage() == "CLOSED"
        assert ctrl.snapshot().state == DemoControlState.KILLED
        assert mt5.calls == 2
        with pytest.raises(DemoSafetyError, match="BUDGET_CONSUMED"):
            lifecycle.open_once(
                request=request(), permit=permit(),
                now=NOW, apc_token=CANARY_APC_TOKEN,
                approved_price_limit=Decimal("2001.00"),
            )
        assert mt5.calls == 2
    finally:
        ctrl.close()
        journal.close()


def test_live_account_never_sends_and_quarantines(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    mt5, ctrl, journal, lifecycle = _setup(monkeypatch, tmp_path)
    try:
        mt5.live = True
        with pytest.raises(DemoSafetyError, match="NOT_EXNESS_DEMO"):
            lifecycle.open_once(
                request=request(), permit=permit(), now=NOW,
                apc_token=CANARY_APC_TOKEN,
                approved_price_limit=Decimal("2001.00"),
            )
        assert mt5.calls == 0
        assert ctrl.snapshot().state == DemoControlState.QUARANTINED
    finally:
        ctrl.close()
        journal.close()


def test_unknown_entry_no_retry_and_quarantines(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    mt5, ctrl, journal, lifecycle = _setup(monkeypatch, tmp_path)
    try:
        mt5.fail_send = True
        with pytest.raises(DemoSafetyError, match="UNKNOWN_ENTRY_RESULT"):
            lifecycle.open_once(
                request=request(), permit=permit(),
                now=NOW, apc_token=CANARY_APC_TOKEN,
                approved_price_limit=Decimal("2001.00"),
            )
        assert journal.stage() == "UNCERTAIN"
        assert ctrl.snapshot().state == DemoControlState.QUARANTINED
        with pytest.raises(DemoSafetyError, match="BUDGET_CONSUMED"):
            lifecycle.open_once(
                request=request(), permit=permit(),
                now=NOW, apc_token=CANARY_APC_TOKEN,
                approved_price_limit=Decimal("2001.00"),
            )
        assert mt5.calls == 1
    finally:
        ctrl.close()
        journal.close()


def test_preflight_stale_quote_blocks_send(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    mt5, ctrl, journal, lifecycle = _setup(monkeypatch, tmp_path)
    try:
        mt5.bad_tick = True
        with pytest.raises(DemoSafetyError, match="QUOTE_STALE"):
            lifecycle.open_once(
                request=request(), permit=permit(),
                now=NOW, apc_token=CANARY_APC_TOKEN,
                approved_price_limit=Decimal("2001.00"),
            )
        assert mt5.calls == 0
    finally:
        ctrl.close()
        journal.close()


def test_preflight_pure_inspect_no_order_apis() -> None:
    path = Path(__file__).resolve().parents[1] / (
        "scripts/apc_demo_canary_readonly_preflight.py"
    )
    fn = runpy.run_path(str(path), run_name="offline_test")["inspect"]
    mt5 = FakeMT5()
    mt5.tradeapi_disabled = True
    # The committed production allowlist cannot be overridden by an API input.
    # In synthetic testing, the module namespace alone substitutes its hash.
    scope = fn.__globals__
    original = scope["EXPECTED_FINGERPRINT"]
    scope["EXPECTED_FINGERPRINT"] = fingerprint()
    try:
        response = fn(mt5, TICK_TIME)
        assert response["status"] == "READ_ONLY_DEMO_PREFLIGHT_PASS"
        assert response["python_trading_disabled"] is True
        assert mt5.calls == 0
        mt5.live = True
        with pytest.raises(ValueError, match="LIVE_OR_UNEXPECTED_ACCOUNT_MODE"):
            fn(mt5, TICK_TIME)
    finally:
        scope["EXPECTED_FINGERPRINT"] = original


@pytest.mark.parametrize(
    ("problem", "outcome"),
    [
        ("bad_position_side", "CANARY_POST_ENTRY_POSITION_MISMATCH"),
        ("bad_magic", "CANARY_POST_ENTRY_POSITION_MISMATCH"),
        ("bad_open_price", "CANARY_POST_ENTRY_POSITION_MISMATCH"),
        ("missing_deal", "CANARY_ENTRY_DEAL_ID_UNKNOWN"),
    ],
)
def test_entry_mismatch_consumes_one_attempt_and_quarantines(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    problem: str, outcome: str,
) -> None:
    mt5, ctrl, journal, lifecycle = _setup(monkeypatch, tmp_path)
    try:
        setattr(mt5, problem, True)
        with pytest.raises(DemoSafetyError, match=outcome):
            lifecycle.open_once(
                request=request(), permit=permit(), now=NOW,
                apc_token=CANARY_APC_TOKEN,
                approved_price_limit=Decimal("2001.00"),
            )
        assert mt5.calls == 1
        assert journal.stage() == "UNCERTAIN"
        assert ctrl.snapshot().state == DemoControlState.QUARANTINED
        with pytest.raises(DemoSafetyError, match="BUDGET_CONSUMED"):
            lifecycle.open_once(
                request=request(), permit=permit(), now=NOW,
                apc_token=CANARY_APC_TOKEN,
                approved_price_limit=Decimal("2001.00"),
            )
        assert mt5.calls == 1
    finally:
        ctrl.close()
        journal.close()


def test_close_unknown_deal_quarantines_without_second_send(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    mt5, ctrl, journal, lifecycle = _setup(monkeypatch, tmp_path)
    try:
        lifecycle.open_once(
            request=request(), permit=permit(), now=NOW,
            apc_token=CANARY_APC_TOKEN,
                approved_price_limit=Decimal("2001.00"),
        )
        mt5.missing_deal = True
        with pytest.raises(DemoSafetyError, match="CANARY_CLOSE_DEAL_ID_UNKNOWN"):
            lifecycle.close_once(permit=permit(), now=NOW, apc_token=CANARY_APC_TOKEN)
        assert mt5.calls == 2
        assert journal.stage() == "UNCERTAIN"
        assert ctrl.snapshot().state == DemoControlState.QUARANTINED
        with pytest.raises(DemoSafetyError, match="CANARY_NOT_IN_CONFIRMED_OPEN_STATE"):
            lifecycle.close_once(permit=permit(), now=NOW, apc_token=CANARY_APC_TOKEN)
        assert mt5.calls == 2
    finally:
        ctrl.close()
        journal.close()


def test_owner_approved_entry_ceiling_fails_before_order_check_or_send(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    mt5, ctrl, journal, lifecycle = _setup(monkeypatch, tmp_path)
    try:
        with pytest.raises(DemoSafetyError, match="BUY_ENTRY_ABOVE_OWNER_LIMIT"):
            lifecycle.open_once(
                request=request(), permit=permit(), now=NOW,
                apc_token=CANARY_APC_TOKEN,
                approved_price_limit=Decimal("2000.20"),
            )
        assert mt5.calls == 0
        assert journal.stage() == "UNUSED"
        assert ctrl.snapshot().state == DemoControlState.QUARANTINED
    finally:
        ctrl.close()
        journal.close()
