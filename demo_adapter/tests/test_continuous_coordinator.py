# ruff: noqa: I001
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from xauusd_demo.continuous_coordinator import (
    ContinuousDemoCoordinator,
    QualifiedBrokerAck,
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
        self.ticket = "700"
        self.send_attempts = 0
        self.position_state = "OPEN"
        self.throw_on_submit = False
        self.throw_on_source = False

    def one_cycle_proposal(self, now: datetime) -> VerifiedProposal | None:
        if self.throw_on_source:
            raise OSError("synthetic market source failed")
        return self.proposal

    def submit_qualified(
        self, proposal: VerifiedProposal, now: datetime
    ) -> QualifiedBrokerAck:
        self.send_attempts += 1
        if self.throw_on_submit:
            raise TimeoutError("synthetic ambiguous broker ACK")
        return QualifiedBrokerAck(
            setup_key=proposal.setup_key, account_fingerprint=FP,
            position_id=int(self.ticket), order_ticket=101,
            entry_deal_ticket=201, side=proposal.side,
            volume_lots=Decimal("0.01"), entry_price=Decimal("2710"),
            stop_loss=Decimal("2700") if proposal.side == "BUY"
            else Decimal("2720"),
            take_profit=Decimal("2720") if proposal.side == "BUY"
            else Decimal("2700"),
            tick_size=Decimal("0.01"),
        )

    def known_position_state(
        self, receipt: QualifiedBrokerAck, now: datetime
    ) -> str:
        assert str(receipt.position_id) == self.ticket
        assert receipt.account_fingerprint == FP
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
        port.ticket = "701"
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


def test_idle_mt5_disconnection_pauses_no_order_and_can_recheck_on_reconnect(
    tmp_path: Path,
) -> None:
    """Only exact idle terminal disconnect is a non-trading temporary pause."""

    class DisconnectingBroker(FakeQualifiedBroker):
        connected = False

        def one_cycle_proposal(self, now: datetime) -> VerifiedProposal | None:
            if not self.connected:
                raise DemoSafetyError("MT5 terminal is not connected")
            return self.proposal

    port = DisconnectingBroker()
    path = tmp_path / "idle-disconnect.sqlite"
    with ContinuousDemoCoordinator(path, account_fingerprint=FP) as c:
        c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)
        for _ in range(3):
            result = c.cycle(port, now=NOW)
            assert result.state == "ACTIVE"
            assert result.action == "NO_ORDER"
            assert result.reason == "MT5_DISCONNECTED_NO_ORDER"
            assert c.conn.execute("SELECT COUNT(*) FROM agent_cycles").fetchone()[0] == 0
            assert port.send_attempts == 0

    # On restart this must not invent a prepared intent or grant trade authority.
    with ContinuousDemoCoordinator(path, account_fingerprint=FP) as c:
        assert c.status() == "ACTIVE"
        port.connected = True
        port.proposal = None
        result = c.cycle(port, now=NOW)
        assert result.state == "ACTIVE"
        assert result.action == "NO_ORDER"
        assert port.send_attempts == 0


@pytest.mark.parametrize("message", [
    "demo account fingerprint mismatch",
    "account is not an MT5 demo account",
    "demo server identity mismatch",
    "external Python demo execution is not enabled",
])
def test_non_transient_identity_faults_still_quarantine(
    tmp_path: Path, message: str,
) -> None:
    class IdentityFault(FakeQualifiedBroker):
        def one_cycle_proposal(self, now: datetime) -> VerifiedProposal | None:
            raise DemoSafetyError(message)

    port = IdentityFault()
    with ContinuousDemoCoordinator(
        tmp_path / "identity.sqlite", account_fingerprint=FP,
    ) as c:
        c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)
        result = c.cycle(port, now=NOW)
        assert result.state == "QUARANTINED"
        assert port.send_attempts == 0
        assert c.status() == "QUARANTINED"


def test_existing_known_position_disconnect_cannot_be_ignored(
    tmp_path: Path,
) -> None:
    class DisconnectKnownPosition(FakeQualifiedBroker):
        disconnected = False

        def known_position_state(
            self, receipt: QualifiedBrokerAck, now: datetime,
        ) -> str:
            if self.disconnected:
                raise DemoSafetyError("MT5 terminal is not connected")
            return super().known_position_state(receipt, now)

    port = DisconnectKnownPosition()
    with ContinuousDemoCoordinator(
        tmp_path / "known-position.sqlite", account_fingerprint=FP,
    ) as c:
        c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)
        assert c.cycle(port, now=NOW).action == "BROKER_ORDER_ACKNOWLEDGED"
        port.disconnected = True
        result = c.cycle(port, now=NOW)
        assert result.state == "QUARANTINED"
        assert result.reason == "UNKNOWN_POSITION"
        assert port.send_attempts == 1


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


def test_ack_receipt_is_persisted_and_reloaded_with_position_id(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ack.sqlite"
    port = FakeQualifiedBroker()
    with ContinuousDemoCoordinator(path, account_fingerprint=FP) as c:
        c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)
        assert c.cycle(port, now=NOW).reason == "700"
        receipt = c.conn.execute(
            "SELECT receipt_json FROM agent_broker_receipts"
        ).fetchone()[0]
        assert QualifiedBrokerAck.decode(receipt).position_id == 700
        assert '"entry_deal_ticket":201' in receipt
    with ContinuousDemoCoordinator(path, account_fingerprint=FP) as c:
        assert c.cycle(port, now=NOW).action == "MONITOR_KNOWN_POSITION"
        assert port.send_attempts == 1


def test_missing_corrupt_or_mismatched_receipt_is_unknown_not_closed(
    tmp_path: Path,
) -> None:
    for damaged in ("deleted", "not_json", "wrong_identifier"):
        port = FakeQualifiedBroker()
        with ContinuousDemoCoordinator(
            tmp_path / f"{damaged}.sqlite", account_fingerprint=FP
        ) as c:
            c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)
            c.cycle(port, now=NOW)
            if damaged == "deleted":
                c.conn.execute("DELETE FROM agent_broker_receipts")
            elif damaged == "not_json":
                c.conn.execute(
                    "UPDATE agent_broker_receipts SET receipt_json='not_json'"
                )
            else:
                c.conn.execute(
                    "UPDATE agent_cycles SET ticket='999' WHERE stage='ACKNOWLEDGED'"
                )
            port.position_state = "CLOSED"
            result = c.cycle(port, now=NOW)
            assert result.state == "QUARANTINED"
            assert port.send_attempts == 1


def test_malformed_or_wrong_side_fake_ack_is_quarantined_before_ack_commit(
    tmp_path: Path,
) -> None:
    class WrongAck(FakeQualifiedBroker):
        def submit_qualified(
            self, proposal: VerifiedProposal, now: datetime
        ) -> QualifiedBrokerAck:
            from dataclasses import replace

            receipt = super().submit_qualified(proposal, now)
            return replace(receipt, side="SELL")

    port = WrongAck()
    with ContinuousDemoCoordinator(
        tmp_path / "wrong-ack.sqlite", account_fingerprint=FP
    ) as c:
        c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)
        result = c.cycle(port, now=NOW)
        assert result.state == "QUARANTINED"
        assert result.action == "NO_RETRY"
        assert c.conn.execute(
            "SELECT COUNT(*) FROM agent_broker_receipts"
        ).fetchone()[0] == 0
        assert port.send_attempts == 1


def test_broker_ack_receipt_rejects_missing_protection_and_not_stop_widened():
    from dataclasses import replace

    port = FakeQualifiedBroker()
    good = port.submit_qualified(proposed(), NOW)
    good.validate(setup_key="a" * 64, account_fingerprint=FP, side="BUY")
    for wrong in (
        replace(good, stop_loss=Decimal("2711")),
        replace(good, take_profit=Decimal("2709")),
        replace(good, volume_lots=Decimal("0.02")),
        replace(good, account_fingerprint="e" * 64),
        replace(good, position_id=0),
    ):
        with pytest.raises(DemoSafetyError):
            wrong.validate(
                setup_key="a" * 64, account_fingerprint=FP, side="BUY"
            )
