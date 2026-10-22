# ruff: noqa: I001
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from xauusd_demo.continuous_coordinator import (
    ContinuousDemoCoordinator,
    VerifiedProposal,
)
from xauusd_demo.envelope import DemoSafetyError

NOW = datetime(2026, 10, 23, 12, 0, 20, tzinfo=UTC)
FP = "9" * 64
ARM = "ARM-CONTINUOUS-PRO-DEMO-XAUUSD"


def proposed(key: str = "a" * 64) -> VerifiedProposal:
    return VerifiedProposal(
        key, "XAUUSD", "BUY",
        NOW - timedelta(seconds=10),
        NOW + timedelta(seconds=15),
    )


class FakeQualifiedBroker:
    """Fake broker: never imported/initialized against any MT5 terminal."""

    def __init__(self) -> None:
        self.proposal: VerifiedProposal | None = proposed()
        self.ticket = "ticket-1"
        self.send_attempts = 0
        self.position_state = "OPEN"
        self.throw_on_submit = False
        self.throw_on_source = False

    def one_cycle_proposal(self, now: datetime) -> VerifiedProposal | None:
        if self.throw_on_source:
            raise OSError("synthetic market source failed")
        return self.proposal

    def submit_qualified(self, proposal: VerifiedProposal, now: datetime) -> str:
        self.send_attempts += 1
        if self.throw_on_submit:
            raise TimeoutError("synthetic ambiguous broker ACK")
        return self.ticket

    def known_position_state(self, ticket: str, now: datetime) -> str:
        assert ticket == self.ticket
        return self.position_state


def test_default_killed_explicit_attended_activation_no_broker_action(
    tmp_path: Path,
) -> None:
    port = FakeQualifiedBroker()
    with ContinuousDemoCoordinator(tmp_path / "coord.sqlite", account_fingerprint=FP) as c:
        assert c.status() == "KILLED"
        assert c.cycle(port, now=NOW).action == "NO_ORDER"
        assert port.send_attempts == 0
        with pytest.raises(DemoSafetyError, match="attended"):
            c.arm_attended(confirmation="start", broker_flat_confirmed=True)
        with pytest.raises(DemoSafetyError, match="unknown"):
            c.arm_attended(confirmation=ARM, broker_flat_confirmed=False)
        c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)
        assert c.status() == "ACTIVE"


def test_continuous_sequential_multiple_known_orders_are_possible(
    tmp_path: Path,
) -> None:
    port = FakeQualifiedBroker()
    path = tmp_path / "sequential.sqlite"
    with ContinuousDemoCoordinator(path, account_fingerprint=FP) as c:
        c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)
        first = c.cycle(port, now=NOW)
        assert first.action == "BROKER_ORDER_ACKNOWLEDGED"
        assert port.send_attempts == 1
        assert c.cycle(port, now=NOW).action == "MONITOR_KNOWN_POSITION"
        assert port.send_attempts == 1
        port.position_state = "CLOSED"
        assert c.cycle(port, now=NOW).action == "POSITION_CLOSED"
        # Old idempotency key is permanently consumed.
        assert c.cycle(port, now=NOW).reason == "SETUP_ID_ALREADY_CONSUMED"
        port.proposal = proposed("b" * 64)
        port.ticket = "ticket-2"
        assert c.cycle(port, now=NOW).action == "BROKER_ORDER_ACKNOWLEDGED"
        assert port.send_attempts == 2
    # Re-open existing known position without accidental new entry.
    with ContinuousDemoCoordinator(path, account_fingerprint=FP) as c:
        port.position_state = "OPEN"
        assert c.cycle(port, now=NOW).action == "MONITOR_KNOWN_POSITION"
        assert port.send_attempts == 2


def test_timeout_quarantines_persistently_no_repeat_and_no_auto_reset(tmp_path: Path):
    path = tmp_path / "ambiguous.sqlite"
    port = FakeQualifiedBroker()
    port.throw_on_submit = True
    with ContinuousDemoCoordinator(path, account_fingerprint=FP) as c:
        c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)
        result = c.cycle(port, now=NOW)
        assert result.state == "QUARANTINED"
        assert result.action == "NO_RETRY"
        assert port.send_attempts == 1
    with ContinuousDemoCoordinator(path, account_fingerprint=FP) as c:
        assert c.cycle(port, now=NOW).action == "NO_ORDER"
        assert port.send_attempts == 1
        with pytest.raises(DemoSafetyError, match="quarantine"):
            c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)


def test_unmatched_known_ticket_latches_quarantine(tmp_path: Path) -> None:
    port = FakeQualifiedBroker()
    with ContinuousDemoCoordinator(tmp_path / "unknown.sqlite", account_fingerprint=FP) as c:
        c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)
        c.cycle(port, now=NOW)
        port.position_state = "UNKNOWN"
        assert c.cycle(port, now=NOW).state == "QUARANTINED"
        assert port.send_attempts == 1


def test_source_exception_quarantines_and_does_not_place_order(tmp_path: Path) -> None:
    port = FakeQualifiedBroker()
    port.throw_on_source = True
    with ContinuousDemoCoordinator(tmp_path / "source.sqlite", account_fingerprint=FP) as c:
        c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)
        assert c.cycle(port, now=NOW).state == "QUARANTINED"
        assert port.send_attempts == 0


def test_bad_or_expired_signal_and_forged_live_symbol_do_not_submit(tmp_path: Path):
    port = FakeQualifiedBroker()
    with ContinuousDemoCoordinator(tmp_path / "signal.sqlite", account_fingerprint=FP) as c:
        c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)
        for proposal in (
            VerifiedProposal("a" * 64, "EURUSD", "BUY", NOW, NOW + timedelta(seconds=10)),
            VerifiedProposal("b" * 64, "XAUUSD", "BUY", NOW - timedelta(minutes=1), NOW),
            VerifiedProposal("c" * 64, "XAUUSD", "BUY", NOW, NOW + timedelta(hours=1)),
        ):
            port.proposal = proposal
            assert c.cycle(port, now=NOW).action == "NO_ORDER"
        assert port.send_attempts == 0


def test_user_kill_persists_across_restart_and_wrong_account_rejected(tmp_path: Path):
    path = tmp_path / "kill.sqlite"
    with ContinuousDemoCoordinator(path, account_fingerprint=FP) as c:
        c.kill("OWNER_E1_KILL")
    with ContinuousDemoCoordinator(path, account_fingerprint=FP) as c:
        assert c.status() == "KILLED"
        assert c.cycle(FakeQualifiedBroker(), now=NOW).action == "NO_ORDER"
    with pytest.raises(DemoSafetyError, match="fingerprint"):
        ContinuousDemoCoordinator(path, account_fingerprint="e" * 64)



def test_single_continuous_runner_lease_survives_crash_and_blocks_second_process(
    tmp_path: Path,
) -> None:
    path = tmp_path / "lease.sqlite"
    with ContinuousDemoCoordinator(path, account_fingerprint=FP) as c:
        c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)
        c._acquire_runner_lease()
        with pytest.raises(DemoSafetyError, match="runner already active"):
            c._acquire_runner_lease()
    # In actual VPS a second process must not resume after an ambiguous crash.
    with ContinuousDemoCoordinator(path, account_fingerprint=FP) as c:
        with pytest.raises(DemoSafetyError, match="runner already active"):
            c._acquire_runner_lease()
