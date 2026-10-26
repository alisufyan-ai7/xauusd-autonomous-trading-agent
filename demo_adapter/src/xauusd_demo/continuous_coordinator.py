"""Durable continuous DEMO trade coordinator (broker-port agnostic).

This is *not* an executable MT5 order adapter: all broker order authority must
stay inside a separately audited, source-bound DEMO implementation of
QualifiedDemoBrokerPort. An old S2 adapter with its hard Policy A block is NOT
a qualifying implementation. No fake success or arbitrary 'risk_pass=True'
claim may authorize MT5 submission through this module.

The coordinator supplies process looping, persistent idempotency, one-known-
position sequencing, crash/unknown-ack quarantine and human restart gates.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from .envelope import DemoSafetyError


class PositionStage(StrEnum):
    PREPARING = "PREPARING"
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    CLOSED = "CLOSED"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True)
class VerifiedProposal:
    """Research setup identity only; does not independently authorize an order."""
    setup_key: str
    symbol: str
    side: str
    confirmed_bar_utc: datetime
    expires_utc: datetime

    def validate(self, now: datetime) -> None:
        if (
            len(self.setup_key) != 64
            or any(c not in "0123456789abcdef" for c in self.setup_key)
            or self.symbol != "XAUUSD"
            or self.side not in {"BUY", "SELL"}
            or self.confirmed_bar_utc.tzinfo is None
            or self.expires_utc.tzinfo is None
            or not self.confirmed_bar_utc < self.expires_utc
            or not self.confirmed_bar_utc <= now < self.expires_utc
            or self.expires_utc - self.confirmed_bar_utc > timedelta(seconds=30)
        ):
            raise DemoSafetyError("unqualified or expired DEMO setup key")



@dataclass(frozen=True, slots=True)
class QualifiedBrokerAck:
    """Exact, immutable broker fill receipt; durable before ACK state change.

    position_id is DEAL_POSITION_ID / POSITION_IDENTIFIER, NOT order/deal.
    This type is only a broker port *contract*, never admission to send.
    """
    setup_key: str
    account_fingerprint: str
    position_id: int
    order_ticket: int
    entry_deal_ticket: int
    side: str
    volume_lots: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    tick_size: Decimal

    def validate(self, *, setup_key: str, account_fingerprint: str, side: str) -> None:
        if (
            self.setup_key != setup_key
            or self.account_fingerprint != account_fingerprint
            or self.side != side
            or any(
                type(x) is not int or x <= 0
                for x in (
                    self.position_id, self.order_ticket,
                    self.entry_deal_ticket,
                )
            )
            or any(
                type(x) is not Decimal or not x.is_finite() or x <= 0
                for x in (
                    self.volume_lots, self.entry_price, self.stop_loss,
                    self.take_profit, self.tick_size,
                )
            )
            or self.volume_lots != Decimal("0.01")
            or (
                self.side == "BUY"
                and not (self.stop_loss < self.entry_price < self.take_profit)
            )
            or (
                self.side == "SELL"
                and not (self.take_profit < self.entry_price < self.stop_loss)
            )
        ):
            raise DemoSafetyError("broker acknowledgment lacks exact owned stop/TP fill")

    def encode(self) -> str:
        """Canonical text for SQLite; no account number or credential."""
        return json.dumps(
            {
                "setup_key": self.setup_key,
                "account_fingerprint": self.account_fingerprint,
                "position_id": self.position_id,
                "order_ticket": self.order_ticket,
                "entry_deal_ticket": self.entry_deal_ticket,
                "side": self.side,
                "volume_lots": str(self.volume_lots),
                "entry_price": str(self.entry_price),
                "stop_loss": str(self.stop_loss),
                "take_profit": str(self.take_profit),
                "tick_size": str(self.tick_size),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def decode(cls, serialized: str) -> QualifiedBrokerAck:
        raw = json.loads(serialized)
        if type(raw) is not dict:
            raise DemoSafetyError("malformed broker receipt")
        return cls(
            setup_key=raw["setup_key"],
            account_fingerprint=raw["account_fingerprint"],
            position_id=raw["position_id"],
            order_ticket=raw["order_ticket"],
            entry_deal_ticket=raw["entry_deal_ticket"],
            side=raw["side"],
            volume_lots=Decimal(raw["volume_lots"]),
            entry_price=Decimal(raw["entry_price"]),
            stop_loss=Decimal(raw["stop_loss"]),
            take_profit=Decimal(raw["take_profit"]),
            tick_size=Decimal(raw["tick_size"]),
        )


@dataclass(frozen=True, slots=True)
class PendingBrokerAck:
    """Durable accepted STOP ORDER, not proof of a filled position."""
    setup_key: str
    account_fingerprint: str
    order_ticket: int
    side: str
    volume_lots: Decimal
    entry_stop: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    expires_utc: datetime

    def validate(
        self, *, setup_key: str, account_fingerprint: str, side: str,
        now: datetime | None = None,
    ) -> None:
        if (
            self.setup_key != setup_key
            or self.account_fingerprint != account_fingerprint
            or self.side != side
            or type(self.order_ticket) is not int or self.order_ticket <= 0
            or any(
                type(x) is not Decimal or not x.is_finite() or x <= 0
                for x in (
                    self.volume_lots, self.entry_stop, self.stop_loss,
                    self.take_profit,
                )
            )
            or self.volume_lots != Decimal("0.01")
            or (
                self.side == "BUY"
                and not (self.stop_loss < self.entry_stop < self.take_profit)
            )
            or (
                self.side == "SELL"
                and not (self.take_profit < self.entry_stop < self.stop_loss)
            )
            or self.expires_utc.tzinfo is None
            or self.expires_utc.utcoffset() != timedelta(0)
            or (
                now is not None and (
                    not now < self.expires_utc
                    or self.expires_utc - now > timedelta(hours=1)
                )
            )
        ):
            raise DemoSafetyError("unqualified pending STOP acknowledgment")

    def encode(self) -> str:
        return json.dumps(
            {
                "setup_key": self.setup_key,
                "account_fingerprint": self.account_fingerprint,
                "order_ticket": self.order_ticket,
                "side": self.side,
                "volume_lots": str(self.volume_lots),
                "entry_stop": str(self.entry_stop),
                "stop_loss": str(self.stop_loss),
                "take_profit": str(self.take_profit),
                "expires_utc": self.expires_utc.isoformat(),
            }, sort_keys=True, separators=(",", ":"),
        )

    @classmethod
    def decode(cls, content: str) -> PendingBrokerAck:
        payload = json.loads(content)
        if type(payload) is not dict:
            raise DemoSafetyError("unusable pending broker receipt")
        return cls(
            setup_key=payload["setup_key"],
            account_fingerprint=payload["account_fingerprint"],
            order_ticket=payload["order_ticket"],
            side=payload["side"],
            volume_lots=Decimal(payload["volume_lots"]),
            entry_stop=Decimal(payload["entry_stop"]),
            stop_loss=Decimal(payload["stop_loss"]),
            take_profit=Decimal(payload["take_profit"]),
            expires_utc=datetime.fromisoformat(payload["expires_utc"]),
        )


@dataclass(frozen=True, slots=True)
class PendingOrderObservation:
    """Broker-authoritative port must prove waiting/fill/expired/cancelled."""
    state: str
    fill: QualifiedBrokerAck | None = None

    def __post_init__(self) -> None:
        if self.state not in {"PENDING", "FILLED", "EXPIRED", "UNKNOWN"}:
            raise DemoSafetyError("unrecognized pending order state")
        if (self.state == "FILLED") != (self.fill is not None):
            raise DemoSafetyError("fill receipt required only for FILLED state")

@dataclass(frozen=True)
class CycleResult:
    state: str
    action: str
    reason: str


class QualifiedDemoBrokerPort(Protocol):
    """Only a broker adapter that independently proves all gates may submit."""

    def one_cycle_proposal(self, now: datetime) -> VerifiedProposal | None:
        """Query actual seven-frame source, complete TPB, verified events and risk."""

    def submit_qualified(
        self, proposal: VerifiedProposal, now: datetime
    ) -> QualifiedBrokerAck | PendingBrokerAck:
        """Internally recheck account/stop/cash/period/M1/event/position, send once.

        Must *never* trust a proposal to assert broker cash or risk approval.
        Return a definitive known fill OR pending-order receipt; never assume PLACED is filled.
        """

    def known_position_state(self, receipt: QualifiedBrokerAck, now: datetime) -> str:
        """Return OPEN, CLOSED or UNKNOWN using authoritative broker deals."""

    def known_pending_state(
        self, receipt: PendingBrokerAck, now: datetime
    ) -> PendingOrderObservation:
        """Prove pending, filled (full receipt), expired-flat or UNKNOWN via MT5."""


class ContinuousDemoCoordinator:
    """Single-writer SQLite control; default KILLED and P1 human-only arming."""

    def __init__(self, path: Path, *, account_fingerprint: str) -> None:
        if len(account_fingerprint) != 64:
            raise DemoSafetyError("exact SHA256 account fingerprint required")
        self._fingerprint = account_fingerprint
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, isolation_level=None)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("PRAGMA busy_timeout=250")
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS agent_control (
             id INTEGER PRIMARY KEY CHECK(id=1), state TEXT NOT NULL,
             fingerprint TEXT NOT NULL, reason TEXT NOT NULL
            ) STRICT"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS agent_cycles (
             setup_key TEXT PRIMARY KEY, stage TEXT NOT NULL,
             side TEXT NOT NULL, bar_utc TEXT NOT NULL, ticket TEXT
            ) STRICT"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS agent_broker_receipts (
             setup_key TEXT PRIMARY KEY, receipt_json TEXT NOT NULL,
             FOREIGN KEY(setup_key) REFERENCES agent_cycles(setup_key)
            ) STRICT"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS agent_pending_receipts (
             setup_key TEXT PRIMARY KEY, receipt_json TEXT NOT NULL,
             FOREIGN KEY(setup_key) REFERENCES agent_cycles(setup_key)
            ) STRICT"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS supervisor_runner_lease (
             id INTEGER PRIMARY KEY CHECK(id=1),
             acquired INTEGER NOT NULL CHECK(acquired IN (0,1))
            ) STRICT"""
        )
        self.conn.execute(
            "INSERT OR IGNORE INTO supervisor_runner_lease VALUES(1,0)"
        )
        row = self.conn.execute(
            "SELECT state, fingerprint FROM agent_control WHERE id=1"
        ).fetchone()
        if row is None:
            self.conn.execute(
                "INSERT INTO agent_control VALUES(1,'KILLED',?,'DEFAULT_NO_ORDER')",
                (account_fingerprint,),
            )
        elif row[1] != account_fingerprint:
            raise DemoSafetyError("persistent supervisor account fingerprint mismatch")

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> ContinuousDemoCoordinator:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def status(self) -> str:
        return str(self.conn.execute(
            "SELECT state FROM agent_control WHERE id=1"
        ).fetchone()[0])

    def kill(self, reason: str) -> None:
        self.conn.execute(
            "UPDATE agent_control SET state='KILLED', reason=? WHERE id=1",
            (reason[:150],),
        )

    def _quarantine(self, reason: str) -> None:
        self.conn.execute(
            "UPDATE agent_control SET state='QUARANTINED', reason=? WHERE id=1",
            (reason[:150],),
        )

    def arm_attended(self, *, confirmation: str, broker_flat_confirmed: bool) -> None:
        """Separate broker source MUST prove zero exposure; Boolean not sufficient
        for broker authority. This only arms the local supervisor coordinator."""
        if confirmation != "ARM-CONTINUOUS-PRO-DEMO-XAUUSD":
            raise DemoSafetyError("explicit attended P1 activation required")
        if self.status() != "KILLED":
            raise DemoSafetyError("quarantine requires separate manual review")
        if broker_flat_confirmed is not True:
            raise DemoSafetyError("cannot arm with unknown account exposure")
        if self.conn.execute(
            "SELECT COUNT(*) FROM agent_cycles WHERE stage != 'CLOSED'"
        ).fetchone()[0]:
            raise DemoSafetyError("pending or uncertain prior broker activity")
        self.conn.execute(
            "UPDATE agent_control SET state='ACTIVE',reason='OWNER_ATTENDED_ARM' WHERE id=1"
        )

    def cycle(self, port: QualifiedDemoBrokerPort, *, now: datetime) -> CycleResult:
        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise DemoSafetyError("exact UTC clock required")
        if self.status() != "ACTIVE":
            return CycleResult(self.status(), "NO_ORDER", "SUPERVISOR_NOT_ARMED")
        rows = self.conn.execute(
            "SELECT setup_key,stage,ticket FROM agent_cycles WHERE stage != 'CLOSED'"
        ).fetchall()
        if len(rows) > 1:
            self._quarantine("MULTIPLE_OUTSTANDING_ORDER_INTENTS")
            return CycleResult("QUARANTINED", "NO_ORDER", "MULTIPLE_INTENTS")
        if rows:
            key, stage, ticket = rows[0]
            if not ticket:
                self._quarantine("UNKNOWN_UNACKNOWLEDGED_BROKER_SUBMISSION")
                return CycleResult("QUARANTINED", "NO_ORDER", "AMBIGUOUS_SUBMISSION")
            if stage == "PENDING":
                try:
                    persisted = self.conn.execute(
                        "SELECT receipt_json FROM agent_pending_receipts "
                        "WHERE setup_key=?", (key,),
                    ).fetchone()
                    if persisted is None:
                        raise DemoSafetyError("missing pending STOP order receipt")
                    pending = PendingBrokerAck.decode(str(persisted[0]))
                    pending.validate(
                        setup_key=str(key), account_fingerprint=self._fingerprint,
                        side=str(self.conn.execute(
                            "SELECT side FROM agent_cycles WHERE setup_key=?",
                            (key,),
                        ).fetchone()[0]),
                    )
                    if str(pending.order_ticket) != str(ticket):
                        raise DemoSafetyError("pending ticket changed")
                    observation = port.known_pending_state(pending, now)
                    if observation.state == "PENDING" and now < pending.expires_utc:
                        return CycleResult("ACTIVE", "MONITOR_PENDING_ORDER", str(ticket))
                    if observation.state == "EXPIRED":
                        # Port must prove broker history is fully expired/cancelled,
                        # no fill/deal and no positions or foreign exposure.
                        self.conn.execute(
                            "UPDATE agent_cycles SET stage='CLOSED' WHERE setup_key=?",
                            (key,),
                        )
                        return CycleResult("ACTIVE", "PENDING_ORDER_EXPIRED", str(ticket))
                    if observation.state != "FILLED" or observation.fill is None:
                        raise DemoSafetyError("pending status unknown/unreconciled")
                    receipt = observation.fill
                    receipt.validate(
                        setup_key=str(key), account_fingerprint=self._fingerprint,
                        side=pending.side,
                    )
                    if receipt.order_ticket != pending.order_ticket:
                        raise DemoSafetyError("opening order ticket does not match pending")
                    if (
                        receipt.stop_loss != pending.stop_loss
                        or receipt.take_profit != pending.take_profit
                        or receipt.volume_lots != pending.volume_lots
                    ):
                        raise DemoSafetyError("filled position lost bound protections")
                    self.conn.execute("BEGIN IMMEDIATE")
                    self.conn.execute(
                        "INSERT INTO agent_broker_receipts VALUES (?,?)",
                        (key, receipt.encode()),
                    )
                    self.conn.execute(
                        "UPDATE agent_cycles SET stage='ACKNOWLEDGED',ticket=? "
                        "WHERE setup_key=?", (str(receipt.position_id), key),
                    )
                    self.conn.execute("COMMIT")
                    return CycleResult(
                        "ACTIVE", "PENDING_ORDER_FILLED", str(receipt.position_id)
                    )
                except Exception:
                    if self.conn.in_transaction:
                        self.conn.execute("ROLLBACK")
                    self._quarantine("PENDING_ORDER_RECONCILIATION_UNKNOWN")
                    return CycleResult("QUARANTINED", "NO_ORDER", "PENDING_UNKNOWN")
            if stage != "ACKNOWLEDGED":
                self._quarantine("UNCERTAIN_BROKER_SUBMISSION")
                return CycleResult("QUARANTINED", "NO_ORDER", "AMBIGUOUS_SUBMISSION")
            try:
                saved = self.conn.execute(
                    "SELECT receipt_json FROM agent_broker_receipts WHERE setup_key=?",
                    (key,),
                ).fetchone()
                if saved is None:
                    raise DemoSafetyError("prior ACK receipt not persisted")
                receipt = QualifiedBrokerAck.decode(str(saved[0]))
                receipt.validate(
                    setup_key=str(key), account_fingerprint=self._fingerprint,
                    side=str(self.conn.execute(
                        "SELECT side FROM agent_cycles WHERE setup_key=?",
                        (key,),
                    ).fetchone()[0]),
                )
                if str(receipt.position_id) != str(ticket):
                    raise DemoSafetyError("broker position identifier changed")
                observed = port.known_position_state(receipt, now)
            except Exception:
                observed = "UNKNOWN"
            if observed == "OPEN":
                return CycleResult("ACTIVE", "MONITOR_KNOWN_POSITION", str(ticket))
            if observed != "CLOSED":
                self._quarantine("BROKER_POSITION_NOT_RECONCILED")
                return CycleResult("QUARANTINED", "NO_ORDER", "UNKNOWN_POSITION")
            self.conn.execute(
                "UPDATE agent_cycles SET stage='CLOSED' WHERE setup_key=?",
                (key,),
            )
            return CycleResult("ACTIVE", "POSITION_CLOSED", str(ticket))

        try:
            proposal = port.one_cycle_proposal(now)
        except DemoSafetyError as exc:
            # Only the exact, broker-port-reported *disconnected terminal*
            # condition is an expected no-order pause while NO intent exists.
            # Recheck the exact DEMO account fingerprint on every next cycle;
            # wrong account, wrong server, unknown exposure and all other
            # safety/source faults remain durably quarantined. Do not use
            # this branch while a known pending/filled/uncertain intent exists:
            # those states are handled by the earlier reconciliation path.
            if str(exc) == "MT5 terminal is not connected":
                return CycleResult("ACTIVE", "NO_ORDER", "MT5_DISCONNECTED_NO_ORDER")
            self._quarantine("SOURCE_OR_FEATURE_EXCEPTION")
            return CycleResult("QUARANTINED", "NO_ORDER", type(exc).__name__)
        except Exception as exc:
            self._quarantine("SOURCE_OR_FEATURE_EXCEPTION")
            return CycleResult("QUARANTINED", "NO_ORDER", type(exc).__name__)
        if proposal is None:
            return CycleResult("ACTIVE", "NO_ORDER", "NO_QUALIFIED_TPB_SETUP")
        try:
            proposal.validate(now)
        except DemoSafetyError:
            return CycleResult("ACTIVE", "NO_ORDER", "SETUP_EXPIRED_OR_UNQUALIFIED")
        existing = self.conn.execute(
            "SELECT stage FROM agent_cycles WHERE setup_key=?",
            (proposal.setup_key,),
        ).fetchone()
        if existing is not None:
            return CycleResult("ACTIVE", "NO_ORDER", "SETUP_ID_ALREADY_CONSUMED")
        self.conn.execute(
            """INSERT INTO agent_cycles(setup_key,stage,side,bar_utc,ticket)
             VALUES (?,'PREPARING',?,?,NULL)""",
            (
                proposal.setup_key, proposal.side,
                proposal.confirmed_bar_utc.astimezone(UTC).isoformat(),
            ),
        )
        # CRITICAL: durable PREPARING must survive process termination before
        # attempting an external action. No automatic resubmission on restart.
        try:
            broker_response = port.submit_qualified(proposal, now)
            if isinstance(broker_response, PendingBrokerAck):
                broker_response.validate(
                    setup_key=proposal.setup_key, side=proposal.side,
                    account_fingerprint=self._fingerprint, now=now,
                )
                # Crash before atomic COMMIT leaves PREPARING => NO RETRY.
                self.conn.execute("BEGIN IMMEDIATE")
                self.conn.execute(
                    "INSERT INTO agent_pending_receipts VALUES (?,?)",
                    (proposal.setup_key, broker_response.encode()),
                )
                self.conn.execute(
                    "UPDATE agent_cycles SET stage='PENDING',ticket=? "
                    "WHERE setup_key=?",
                    (str(broker_response.order_ticket), proposal.setup_key),
                )
                self.conn.execute("COMMIT")
                return CycleResult(
                    "ACTIVE", "BROKER_PENDING_ACKNOWLEDGED",
                    str(broker_response.order_ticket),
                )
            if not isinstance(broker_response, QualifiedBrokerAck):
                raise DemoSafetyError("broker port lacks exact verified fill receipt")
            receipt = broker_response
            receipt.validate(
                setup_key=proposal.setup_key, side=proposal.side,
                account_fingerprint=self._fingerprint,
            )
            # Commit exact receipt and ACK stage in one SQLite transaction.
            # If the broker filled but this process crashes BEFORE the commit,
            # PREPARING survives and forces human reconciliation without retry.
            self.conn.execute("BEGIN IMMEDIATE")
            self.conn.execute(
                "INSERT INTO agent_broker_receipts VALUES (?,?)",
                (proposal.setup_key, receipt.encode()),
            )
            self.conn.execute(
                "UPDATE agent_cycles SET stage='ACKNOWLEDGED',ticket=? "
                "WHERE setup_key=?",
                (str(receipt.position_id), proposal.setup_key),
            )
            self.conn.execute("COMMIT")
        except Exception:
            if self.conn.in_transaction:
                self.conn.execute("ROLLBACK")
            self.conn.execute(
                "UPDATE agent_cycles SET stage='UNCERTAIN' WHERE setup_key=?",
                (proposal.setup_key,),
            )
            self._quarantine("FAILED_OR_UNCERTAIN_BROKER_SUBMISSION")
            return CycleResult("QUARANTINED", "NO_RETRY", "BROKER_ACK_UNKNOWN")
        return CycleResult(
            "ACTIVE", "BROKER_ORDER_ACKNOWLEDGED", str(receipt.position_id)
        )

    def _acquire_runner_lease(self) -> None:
        """Persistent single-owner fence; crash needs attended P1 recovery."""
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            acquired = self.conn.execute(
                "SELECT acquired FROM supervisor_runner_lease WHERE id=1"
            ).fetchone()
            if acquired is None or int(acquired[0]) != 0:
                raise DemoSafetyError("runner already active or requires P1 review")
            if self.status() != "ACTIVE":
                raise DemoSafetyError("runner cannot start while KILLED")
            self.conn.execute(
                "UPDATE supervisor_runner_lease SET acquired=1 WHERE id=1"
            )
            self.conn.execute("COMMIT")
        except Exception:
            if self.conn.in_transaction:
                self.conn.execute("ROLLBACK")
            raise

    def run_forever(
        self, port: QualifiedDemoBrokerPort, *, interval_seconds: float = 5.0
    ) -> None:
        if not (1.0 <= interval_seconds <= 60.0):
            raise DemoSafetyError("supervisor polling interval out of bounds")
        self._acquire_runner_lease()
        # Deliberately never release the persistent lease on process crash,
        # SIGINT or exception. P1 recovery requires human broker reconciliation.
        while True:
            result = self.cycle(port, now=datetime.now(UTC))
            if result.state != "ACTIVE":
                raise DemoSafetyError(
                    f"persistent supervisor stopped: {result.reason}"
                )
            time.sleep(interval_seconds)
