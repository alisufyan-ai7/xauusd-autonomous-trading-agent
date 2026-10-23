# ruff: noqa: I001
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

import pytest

from xauusd_demo.continuous_coordinator import (
    ContinuousDemoCoordinator, PendingBrokerAck, PendingOrderObservation,
    QualifiedBrokerAck, VerifiedProposal,
)
from xauusd_demo.envelope import DemoSafetyError

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)
FP = "a" * 64
ARM = "ARM-CONTINUOUS-PRO-DEMO-XAUUSD"


class FakePending:
    def __init__(self):
        self.proposal = VerifiedProposal(
            "b" * 64, "XAUUSD", "BUY",
            NOW - timedelta(seconds=5),
            NOW + timedelta(seconds=20),
        )
        self.send_calls = 0
        self.status = "PENDING"
        self.position_status = "OPEN"
        self.forged_fill = False

    def submit_qualified(self, proposal, now):
        self.send_calls += 1
        return PendingBrokerAck(
            proposal.setup_key, FP, 501, proposal.side, D("0.01"),
            D("2701"), D("2695"), D("2720"), NOW + timedelta(minutes=50),
        )

    def one_cycle_proposal(self, now):
        return self.proposal

    def known_pending_state(self, receipt, now):
        assert receipt.order_ticket == 501
        if self.status == "FILLED":
            fill = QualifiedBrokerAck(
                self.proposal.setup_key, FP, 700,
                999 if self.forged_fill else 501,
                1001, "BUY", D("0.01"), D("2701"),
                D("2695"), D("2720"), D("0.01"),
            )
            return PendingOrderObservation("FILLED", fill)
        return PendingOrderObservation(self.status)

    def known_position_state(self, receipt, now):
        assert receipt.position_id == 700
        return self.position_status


def armed(path):
    c = ContinuousDemoCoordinator(path, account_fingerprint=FP)
    c.arm_attended(confirmation=ARM, broker_flat_confirmed=True)
    return c


def test_accepted_stop_is_pending_not_a_filled_position(tmp_path: Path):
    p = FakePending()
    with armed(tmp_path / "pending.sqlite") as c:
        first = c.cycle(p, now=NOW)
        assert first.action == "BROKER_PENDING_ACKNOWLEDGED"
        assert first.reason == "501"
        assert c.cycle(p, now=NOW).action == "MONITOR_PENDING_ORDER"
        assert p.send_calls == 1
        assert c.conn.execute(
            "SELECT stage FROM agent_cycles"
        ).fetchone()[0] == "PENDING"
        assert c.conn.execute(
            "SELECT COUNT(*) FROM agent_broker_receipts"
        ).fetchone()[0] == 0


def test_pending_fill_atomically_binds_position_and_then_known_close(
    tmp_path: Path,
):
    p = FakePending()
    path = tmp_path / "fills.sqlite"
    with armed(path) as c:
        c.cycle(p, now=NOW)
    # restart must poll existing accepted pending order, not submit again
    with ContinuousDemoCoordinator(path, account_fingerprint=FP) as c:
        p.status = "FILLED"
        result = c.cycle(p, now=NOW + timedelta(seconds=5))
        assert result.action == "PENDING_ORDER_FILLED"
        assert result.reason == "700"
        assert c.conn.execute(
            "SELECT stage FROM agent_cycles"
        ).fetchone()[0] == "ACKNOWLEDGED"
        assert c.cycle(p, now=NOW).action == "MONITOR_KNOWN_POSITION"
        p.position_status = "CLOSED"
        assert c.cycle(p, now=NOW).action == "POSITION_CLOSED"
        assert p.send_calls == 1
        assert c.cycle(p, now=NOW).reason == "SETUP_ID_ALREADY_CONSUMED"


def test_expired_pending_requires_broker_terminal_proof(tmp_path: Path):
    p = FakePending()
    with armed(tmp_path / "expired.sqlite") as c:
        c.cycle(p, now=NOW)
        future = NOW + timedelta(minutes=51)
        assert c.cycle(p, now=future).state == "QUARANTINED"
        assert p.send_calls == 1

    p = FakePending()
    with armed(tmp_path / "confirmed_expired.sqlite") as c:
        c.cycle(p, now=NOW)
        p.status = "EXPIRED"
        outcome = c.cycle(p, now=NOW + timedelta(minutes=51))
        assert outcome.action == "PENDING_ORDER_EXPIRED"
        assert c.conn.execute(
            "SELECT stage FROM agent_cycles"
        ).fetchone()[0] == "CLOSED"
        assert p.send_calls == 1


@pytest.mark.parametrize("scenario", [
    "wrong_ticket", "missing_receipt", "malformed_receipt",
    "unknown_broker", "wrong_fill_order",
])
def test_ambiguous_pending_reconciliations_latch_no_retry(
    tmp_path: Path, scenario: str
):
    p = FakePending()
    with armed(tmp_path / f"{scenario}.sqlite") as c:
        c.cycle(p, now=NOW)
        if scenario == "wrong_ticket":
            c.conn.execute("UPDATE agent_cycles SET ticket='999'")
        elif scenario == "missing_receipt":
            c.conn.execute("DELETE FROM agent_pending_receipts")
        elif scenario == "malformed_receipt":
            c.conn.execute(
                "UPDATE agent_pending_receipts SET receipt_json='bad JSON'"
            )
        elif scenario == "unknown_broker":
            p.status = "UNKNOWN"
        else:
            p.status = "FILLED"
            p.forged_fill = True
        outcome = c.cycle(p, now=NOW)
        assert outcome.state == "QUARANTINED"
        assert outcome.action == "NO_ORDER"
        assert p.send_calls == 1
        assert c.cycle(p, now=NOW).state == "QUARANTINED"


@pytest.mark.parametrize("field,value", [
    ("volume_lots", D("0.02")), ("stop_loss", D("2702")),
    ("order_ticket", 0), ("expires_utc", NOW - timedelta(seconds=1)),
])
def test_unqualified_pending_ack_denies_at_creation(tmp_path: Path, field, value):
    class MalformedPending(FakePending):
        def submit_qualified(self, proposal, now):
            receipt = super().submit_qualified(proposal, now)
            return replace(receipt, **{field: value})

    port = MalformedPending()
    with armed(tmp_path / f"{field}.sqlite") as c:
        assert c.cycle(port, now=NOW).state == "QUARANTINED"
        assert port.send_calls == 1
        assert c.conn.execute(
            "SELECT COUNT(*) FROM agent_pending_receipts"
        ).fetchone()[0] == 0


def test_pending_observation_cannot_claim_filled_without_receipt():
    with pytest.raises(DemoSafetyError):
        PendingOrderObservation("FILLED")
    with pytest.raises(DemoSafetyError):
        PendingOrderObservation("UNKNOWN", QualifiedBrokerAck(
            "b" * 64, FP, 7, 1, 2, "BUY", D("0.01"), D("2701"),
            D("2695"), D("2720"), D("0.01"),
        ))
