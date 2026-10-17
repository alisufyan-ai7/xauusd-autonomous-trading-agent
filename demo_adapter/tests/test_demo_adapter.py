# ruff: noqa: I001
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from xauusd_demo import (
    ARM_CONFIRMATION,
    DEMO_LIFECYCLE_SCOPE,
    RESET_CONFIRMATION,
    DemoActivationPermit,
    DemoControlState,
    DemoControlStore,
    DemoIdentity,
    DemoMT5Adapter,
    DemoOrderRequest,
    DemoPolicy,
    DemoRiskCalibration,
    DemoSafetyError,
    DemoSide,
    DemoSubmissionLedger,
)


BROKER = "Exness Technologies Ltd"
SERVER = "Exness-MT5Trial15"
LOGIN = "12345678"
CURRENCY = "USD"
NOW = datetime(2026, 10, 18, tzinfo=UTC)


def fingerprint() -> str:
    return hashlib.sha256(
        f"{BROKER}|{SERVER}|{LOGIN}|{CURRENCY}".encode()
    ).hexdigest()


def identity() -> DemoIdentity:
    return DemoIdentity(BROKER, SERVER, fingerprint(), CURRENCY)


def calibration() -> DemoRiskCalibration:
    return DemoRiskCalibration(
        calibration_id="TEST-DEMO-CALIBRATION",
        source_sha256="1" * 64,
        scope=DEMO_LIFECYCLE_SCOPE,
        current_adverse_cost=Decimal("1"),
        stressed_adverse_cost=Decimal("2"),
    )


def executable_policy() -> DemoPolicy:
    item = calibration()
    return DemoPolicy(
        max_daily_submissions=3,
        risk_calibration_sha256=item.sha256(),
    )


def activation() -> DemoActivationPermit:
    return DemoActivationPermit(
        activation_id="TEST-APC-DEMO",
        account_id_sha256=fingerprint(),
        server=SERVER,
        max_daily_submissions=3,
        not_before_utc=datetime(2026, 10, 17, tzinfo=UTC),
        expires_utc=datetime(2026, 10, 19, tzinfo=UTC),
    )


def expired_activation() -> DemoActivationPermit:
    return DemoActivationPermit(
        activation_id="TEST-APC-DEMO-EXPIRED",
        account_id_sha256=fingerprint(),
        server=SERVER,
        max_daily_submissions=3,
        not_before_utc=datetime(2026, 10, 16, tzinfo=UTC),
        expires_utc=datetime(2026, 10, 17, tzinfo=UTC),
    )


def request(*, side: DemoSide = DemoSide.BUY) -> DemoOrderRequest:
    return DemoOrderRequest(
        request_id=str(uuid.uuid4()),
        symbol="XAUUSD",
        side=side,
        volume_lots=Decimal("0.01"),
        stop_loss=Decimal("1990") if side is DemoSide.BUY else Decimal("2010"),
    )


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    TRADE_ACTION_DEAL = 1
    ORDER_TIME_GTC = 0
    TRADE_RETCODE_DONE = 10009

    def __init__(self) -> None:
        self.tradeapi_disabled = True
        self.connected = True
        self.trade_mode = self.ACCOUNT_TRADE_MODE_DEMO
        self.positions: tuple[object, ...] = ()
        self.orders: tuple[object, ...] = ()
        self.send_calls = 0
        self.return_none = False
        self.send_exception: Exception | None = None

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass

    def last_error(self) -> tuple[int, str]:
        return (0, "ok")

    def terminal_info(self) -> object:
        return SimpleNamespace(
            connected=self.connected,
            tradeapi_disabled=self.tradeapi_disabled,
        )

    def account_info(self) -> object:
        return SimpleNamespace(
            company=BROKER,
            server=SERVER,
            login=LOGIN,
            currency=CURRENCY,
            trade_mode=self.trade_mode,
            equity=10000.0,
            margin_free=10000.0,
            margin=0.0,
        )

    def positions_get(self) -> tuple[object, ...]:
        return self.positions

    def orders_get(self) -> tuple[object, ...]:
        return self.orders

    def symbol_info(self, symbol: str) -> object:
        assert symbol == "XAUUSD"
        return SimpleNamespace(
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            point=0.001,
            trade_stops_level=10,
        )

    def symbol_info_tick(self, symbol: str) -> object:
        assert symbol == "XAUUSD"
        return SimpleNamespace(bid=2000.0, ask=2000.2)

    def order_calc_margin(
        self,
        order_type: int,
        symbol: str,
        volume: float,
        price: float,
    ) -> float:
        assert order_type in (self.ORDER_TYPE_BUY, self.ORDER_TYPE_SELL)
        assert symbol == "XAUUSD"
        assert volume == 0.01
        assert price > 0
        return 5.0

    def order_check(self, payload: dict[str, object]) -> object:
        assert payload["symbol"] == "XAUUSD"
        assert payload["volume"] == 0.01
        assert payload["sl"]
        return SimpleNamespace(retcode=0)

    def order_send(self, payload: dict[str, object]) -> object | None:
        self.send_calls += 1
        if self.send_exception is not None:
            raise self.send_exception
        if self.return_none:
            return None
        self.positions = (
            SimpleNamespace(
                symbol="XAUUSD",
                volume=payload["volume"],
                sl=payload["sl"],
            ),
        )
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=77, deal=88)


def ledger(tmp_path: Path, *, cap: int = 3) -> DemoSubmissionLedger:
    return DemoSubmissionLedger(
        tmp_path / "demo.sqlite3",
        max_daily_submissions=cap,
    )


def control(tmp_path: Path) -> DemoControlStore:
    return DemoControlStore(tmp_path / "control.sqlite3")


def arm(item: DemoControlStore, *, permit: DemoActivationPermit | None = None) -> None:
    item.arm(
        permit=permit or activation(),
        identity=identity(),
        now=NOW,
        confirmation_phrase=ARM_CONFIRMATION,
    )


def test_request_rejects_non_xauusd_and_volume_above_cap() -> None:
    with pytest.raises(DemoSafetyError):
        DemoOrderRequest(
            str(uuid.uuid4()),
            "EURUSD",
            DemoSide.BUY,
            Decimal("0.01"),
            Decimal("1"),
        ).validate()

    with pytest.raises(DemoSafetyError):
        DemoOrderRequest(
            str(uuid.uuid4()),
            "XAUUSD",
            DemoSide.BUY,
            Decimal("0.02"),
            Decimal("1990"),
        ).validate()


def test_request_requires_protective_stop() -> None:
    with pytest.raises(DemoSafetyError):
        DemoOrderRequest(
            str(uuid.uuid4()),
            "XAUUSD",
            DemoSide.BUY,
            Decimal("0.01"),
            Decimal("0"),
        ).validate()


def test_risk_calibration_requires_provenance_and_demo_scope() -> None:
    with pytest.raises(DemoSafetyError, match="source_sha256"):
        DemoRiskCalibration(
            calibration_id="X",
            source_sha256="bad",
            scope=DEMO_LIFECYCLE_SCOPE,
            current_adverse_cost=Decimal("1"),
            stressed_adverse_cost=Decimal("2"),
        ).validate()

    with pytest.raises(DemoSafetyError, match="scope"):
        DemoRiskCalibration(
            calibration_id="X",
            source_sha256="1" * 64,
            scope="LIVE",
            current_adverse_cost=Decimal("1"),
            stressed_adverse_cost=Decimal("2"),
        ).validate()


def test_control_defaults_killed_and_arms_only_with_exact_confirmation(tmp_path: Path) -> None:
    with control(tmp_path) as gate:
        assert gate.snapshot().state is DemoControlState.KILLED

        with pytest.raises(DemoSafetyError, match="arm confirmation"):
            gate.arm(
                permit=activation(),
                identity=identity(),
                now=NOW,
                confirmation_phrase="WRONG",
            )

        arm(gate)
        snapshot = gate.snapshot()
        assert snapshot.state is DemoControlState.ACTIVE
        assert snapshot.activation_id == activation().activation_id
        assert snapshot.account_id_sha256 == fingerprint()


def test_quarantine_requires_explicit_reset_before_rearm(tmp_path: Path) -> None:
    with control(tmp_path) as gate:
        arm(gate)
        gate.quarantine(reason="TEST_FAULT", now=NOW)
        assert gate.snapshot().state is DemoControlState.QUARANTINED

        with pytest.raises(DemoSafetyError, match="explicit reset"):
            arm(gate)

        with pytest.raises(DemoSafetyError, match="reset confirmation"):
            gate.reset_quarantine_to_killed(
                confirmation_phrase="WRONG",
                reason="operator reviewed",
                now=NOW,
            )

        gate.reset_quarantine_to_killed(
            confirmation_phrase=RESET_CONFIRMATION,
            reason="operator reviewed",
            now=NOW,
        )
        assert gate.snapshot().state is DemoControlState.KILLED
        arm(gate)
        assert gate.snapshot().state is DemoControlState.ACTIVE


def test_expired_permit_kills_active_control(tmp_path: Path) -> None:
    with control(tmp_path) as gate:
        arm(gate)
        with pytest.raises(DemoSafetyError, match="not currently valid"):
            gate.assert_active(
                permit=expired_activation(),
                identity=identity(),
                now=NOW,
            )
        assert gate.snapshot().state is DemoControlState.KILLED


def test_preflight_accepts_exact_demo_identity_while_execution_disabled(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    with ledger(tmp_path) as book, control(tmp_path) as gate:
        adapter = DemoMT5Adapter(
            identity(),
            DemoPolicy(3),
            book,
            control=gate,
            module=mt5,
        )
        adapter.initialize()
        result = adapter.preflight()
        adapter.close()

    assert result["demo_identity_match"] is True
    assert result["external_python_trading_enabled"] is False
    assert result["open_positions"] == 0
    assert result["control_state"] == "KILLED"
    assert mt5.send_calls == 0


def test_live_trade_mode_is_rejected_before_any_send(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    mt5.trade_mode = 2

    with ledger(tmp_path) as book:
        adapter = DemoMT5Adapter(identity(), DemoPolicy(3), book, module=mt5)
        with pytest.raises(DemoSafetyError, match="not an MT5 demo account"):
            adapter.initialize()

    assert mt5.send_calls == 0


def test_account_fingerprint_mismatch_is_rejected(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    wrong = DemoIdentity(BROKER, SERVER, "0" * 64, CURRENCY)

    with ledger(tmp_path) as book:
        adapter = DemoMT5Adapter(wrong, DemoPolicy(3), book, module=mt5)
        with pytest.raises(DemoSafetyError, match="fingerprint mismatch"):
            adapter.initialize()

    assert mt5.send_calls == 0


def test_submission_requires_exact_confirmation(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    with ledger(tmp_path) as book:
        adapter = DemoMT5Adapter(identity(), DemoPolicy(3), book, module=mt5)
        adapter.initialize()
        with pytest.raises(DemoSafetyError, match="confirmation token"):
            adapter.submit_market_order(request(), confirmation_phrase="WRONG")
        adapter.close()
    assert mt5.send_calls == 0


def test_submission_requires_durable_control(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    mt5.tradeapi_disabled = False

    with ledger(tmp_path) as book:
        adapter = DemoMT5Adapter(identity(), executable_policy(), book, module=mt5)
        adapter.initialize()
        with pytest.raises(DemoSafetyError, match="durable kill/quarantine control"):
            adapter.submit_market_order(
                request(),
                confirmation_phrase="SUBMIT-BOUNDED-DEMO-XAUUSD",
                activation_permit=activation(),
                risk_calibration=calibration(),
                now=NOW,
            )
        adapter.close()

    assert mt5.send_calls == 0


def test_execution_disabled_after_arm_quarantines_control(tmp_path: Path) -> None:
    mt5 = FakeMT5()

    with ledger(tmp_path) as book, control(tmp_path) as gate:
        arm(gate)
        adapter = DemoMT5Adapter(
            identity(),
            executable_policy(),
            book,
            control=gate,
            module=mt5,
        )
        adapter.initialize()

        with pytest.raises(DemoSafetyError, match="not enabled"):
            adapter.submit_market_order(
                request(),
                confirmation_phrase="SUBMIT-BOUNDED-DEMO-XAUUSD",
                activation_permit=activation(),
                risk_calibration=calibration(),
                now=NOW,
            )

        adapter.close()
        assert gate.snapshot().state is DemoControlState.QUARANTINED

    assert mt5.send_calls == 0


def test_missing_activation_permit_blocks_send(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    mt5.tradeapi_disabled = False

    with ledger(tmp_path) as book, control(tmp_path) as gate:
        adapter = DemoMT5Adapter(
            identity(),
            executable_policy(),
            book,
            control=gate,
            module=mt5,
        )
        adapter.initialize()
        with pytest.raises(DemoSafetyError, match="owner-gated activation permit"):
            adapter.submit_market_order(
                request(),
                confirmation_phrase="SUBMIT-BOUNDED-DEMO-XAUUSD",
                risk_calibration=calibration(),
                now=NOW,
            )
        adapter.close()

    assert mt5.send_calls == 0


def test_missing_risk_calibration_quarantines_control(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    mt5.tradeapi_disabled = False

    with ledger(tmp_path) as book, control(tmp_path) as gate:
        arm(gate)
        adapter = DemoMT5Adapter(
            identity(),
            executable_policy(),
            book,
            control=gate,
            module=mt5,
        )
        adapter.initialize()
        with pytest.raises(DemoSafetyError, match="hash-bound risk calibration"):
            adapter.submit_market_order(
                request(),
                confirmation_phrase="SUBMIT-BOUNDED-DEMO-XAUUSD",
                activation_permit=activation(),
                now=NOW,
            )
        adapter.close()
        assert gate.snapshot().state is DemoControlState.QUARANTINED

    assert mt5.send_calls == 0


def test_existing_exposure_quarantines_control(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    mt5.tradeapi_disabled = False
    mt5.positions = (
        SimpleNamespace(symbol="XAUUSD", volume=0.01, sl=1990.0),
    )

    with ledger(tmp_path) as book, control(tmp_path) as gate:
        arm(gate)
        adapter = DemoMT5Adapter(
            identity(),
            executable_policy(),
            book,
            control=gate,
            module=mt5,
        )
        adapter.initialize()
        with pytest.raises(DemoSafetyError, match="requires zero positions"):
            adapter.submit_market_order(
                request(),
                confirmation_phrase="SUBMIT-BOUNDED-DEMO-XAUUSD",
                activation_permit=activation(),
                risk_calibration=calibration(),
                now=NOW,
            )
        adapter.close()
        assert gate.snapshot().state is DemoControlState.QUARANTINED

    assert mt5.send_calls == 0


def test_successful_bounded_demo_submission_keeps_control_active(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    mt5.tradeapi_disabled = False
    order = request()

    with ledger(tmp_path) as book, control(tmp_path) as gate:
        arm(gate)
        adapter = DemoMT5Adapter(
            identity(),
            executable_policy(),
            book,
            control=gate,
            module=mt5,
        )
        adapter.initialize()
        result = adapter.submit_market_order(
            order,
            confirmation_phrase="SUBMIT-BOUNDED-DEMO-XAUUSD",
            activation_permit=activation(),
            risk_calibration=calibration(),
            now=NOW,
        )
        adapter.close()
        status = book.status(order.request_id)
        gate_state = gate.snapshot().state

    assert result["status"] == "ACKNOWLEDGED"
    assert result["volume_lots"] == "0.01"
    assert result["live_account_permitted"] is False
    assert result["control_state"] == "ACTIVE"
    assert status == "ACKNOWLEDGED"
    assert gate_state is DemoControlState.ACTIVE
    assert mt5.send_calls == 1


def test_uncertain_submission_latches_ledger_and_quarantines_control(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    mt5.tradeapi_disabled = False
    mt5.return_none = True
    first = request()

    with ledger(tmp_path) as book, control(tmp_path) as gate:
        arm(gate)
        adapter = DemoMT5Adapter(
            identity(),
            executable_policy(),
            book,
            control=gate,
            module=mt5,
        )
        adapter.initialize()

        with pytest.raises(DemoSafetyError, match="uncertain"):
            adapter.submit_market_order(
                first,
                confirmation_phrase="SUBMIT-BOUNDED-DEMO-XAUUSD",
                activation_permit=activation(),
                risk_calibration=calibration(),
                now=NOW,
            )

        assert book.status(first.request_id) == "UNCERTAIN"
        assert gate.snapshot().state is DemoControlState.QUARANTINED

        mt5.return_none = False
        with pytest.raises(DemoSafetyError, match="not ACTIVE"):
            adapter.submit_market_order(
                request(),
                confirmation_phrase="SUBMIT-BOUNDED-DEMO-XAUUSD",
                activation_permit=activation(),
                risk_calibration=calibration(),
                now=datetime(2026, 10, 18, 1, tzinfo=UTC),
            )

        adapter.close()

    assert mt5.send_calls == 1


def test_kill_blocks_new_submission_before_broker_send(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    mt5.tradeapi_disabled = False

    with ledger(tmp_path) as book, control(tmp_path) as gate:
        arm(gate)
        gate.kill(reason="OWNER_KILL", now=NOW)
        adapter = DemoMT5Adapter(
            identity(),
            executable_policy(),
            book,
            control=gate,
            module=mt5,
        )
        adapter.initialize()
        with pytest.raises(DemoSafetyError, match="not ACTIVE"):
            adapter.submit_market_order(
                request(),
                confirmation_phrase="SUBMIT-BOUNDED-DEMO-XAUUSD",
                activation_permit=activation(),
                risk_calibration=calibration(),
                now=NOW,
            )
        adapter.close()

    assert mt5.send_calls == 0


def test_daily_submission_budget_is_hard_bounded(tmp_path: Path) -> None:
    with ledger(tmp_path, cap=1) as book:
        first = request()
        book.reserve(first, now=NOW)
        book.mark_acknowledged(first.request_id, mt5_retcode=10009, order_ticket="1")

        with pytest.raises(DemoSafetyError, match="budget exhausted"):
            book.reserve(
                request(),
                now=datetime(2026, 10, 18, 2, tzinfo=UTC),
            )
