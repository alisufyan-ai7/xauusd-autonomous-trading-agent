"""Offline first-DEMO-order release denial contract; NEVER an order launcher.

The real S2 source remains intentionally blocked until the *whole* Policy A
cash-risk and broker evidence chain is independently admitted. These tests
must NEVER connect to a real MT5 terminal, enable trading, or send an order.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from test_demo_adapter import (
    FakeMT5,
    activation,
    arm,
    calibration,
    executable_policy,
    identity,
    request,
)
from xauusd_demo import (
    DemoControlState,
    DemoControlStore,
    DemoMT5Adapter,
    DemoSafetyError,
    DemoSubmissionLedger,
)

NOW = datetime(2026, 10, 18, tzinfo=UTC)
CONFIRMATION = "SUBMIT-BOUNDED-DEMO-XAUUSD"


class CountingFakeMT5(FakeMT5):
    """Synthetic object. Explicitly records if any send/check becomes reachable."""

    def __init__(self) -> None:
        super().__init__()
        self.check_calls = 0

    def order_check(self, payload: dict[str, object]) -> object:
        self.check_calls += 1
        return super().order_check(payload)


def test_first_order_release_fails_at_full_cash_policy_with_no_broker_calls(
    tmp_path: Path,
) -> None:
    fake = CountingFakeMT5()
    # Synthetic override ONLY: this never modifies an actual terminal.
    fake.tradeapi_disabled = False
    item = request()
    db = tmp_path / "demo-submission.sqlite"
    control_path = tmp_path / "demo-kill.sqlite"
    with (
        DemoSubmissionLedger(db, max_daily_submissions=3) as ledger,
        DemoControlStore(control_path) as control,
    ):
        arm(control)
        with DemoMT5Adapter(
            identity(), executable_policy(), ledger,
            control=control, module=fake,
        ) as adapter:
            with pytest.raises(
                DemoSafetyError,
                match="full Policy A broker-reconciled USD cash-risk binding",
            ):
                adapter.submit_market_order(
                    item, confirmation_phrase=CONFIRMATION,
                    activation_permit=activation(),
                    risk_calibration=calibration(), now=NOW,
                )
        assert ledger.status(item.request_id) is None
        assert control.snapshot().state is DemoControlState.QUARANTINED
    assert fake.check_calls == 0
    assert fake.send_calls == 0
    # Real durable control state must not revert to ACTIVE on restart.
    with DemoControlStore(control_path) as restored:
        assert restored.snapshot().state is DemoControlState.QUARANTINED
        with pytest.raises(DemoSafetyError, match="explicit reset"):
            arm(restored)


def test_missing_activation_or_python_protection_fails_before_order_api(
    tmp_path: Path,
) -> None:
    fake = CountingFakeMT5()
    with (
        DemoSubmissionLedger(tmp_path / "submission.sqlite", max_daily_submissions=3) as ledger,
        DemoControlStore(tmp_path / "control.sqlite") as control,
    ):
        arm(control)
        with DemoMT5Adapter(
            identity(), executable_policy(), ledger,
            control=control, module=fake,
        ) as adapter:
            with pytest.raises(DemoSafetyError, match="not enabled"):
                adapter.submit_market_order(
                    request(), confirmation_phrase=CONFIRMATION,
                    activation_permit=activation(),
                    risk_calibration=calibration(), now=NOW,
                )
        assert control.snapshot().state is DemoControlState.QUARANTINED
    assert fake.check_calls == 0 and fake.send_calls == 0


def test_demo_preflight_remains_read_only_and_killed_by_default(
    tmp_path: Path,
) -> None:
    fake = CountingFakeMT5()
    with (
        DemoSubmissionLedger(tmp_path / "submission.sqlite", max_daily_submissions=1) as ledger,
        DemoControlStore(tmp_path / "control.sqlite") as control,
    ):
        with DemoMT5Adapter(
            identity(), executable_policy(), ledger,
            control=control, module=fake,
        ) as adapter:
            evidence = adapter.preflight()
            assert evidence["control_state"] == "KILLED"
            assert evidence["external_python_trading_enabled"] is False
            assert evidence["open_positions"] == 0
            assert evidence["pending_orders"] == 0
    assert fake.check_calls == 0 and fake.send_calls == 0
