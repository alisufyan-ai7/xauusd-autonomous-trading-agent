"""Durable outbox for closed-set internal events only.

This module contains no transport and cannot submit broker operations.
"""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from xauusd_agent.core.canonical import canonical_bytes, canonical_json, sha256_hex
from xauusd_agent.core.clock import Clock, SystemClock, ensure_utc, format_utc
from xauusd_agent.core.errors import ConcurrentWriteError, IntegrityError, ValidationError
from xauusd_agent.core.model import InternalEventType

from .database import immediate_transaction
from .lease import LeaseToken, assert_lease


@dataclass(frozen=True, slots=True)
class OutboxItem:
    sequence: int
    event_id: str
    event_type: InternalEventType
    payload_json: str
    status: str
    attempts: int
    version: int
    claim_token: str | None


def _content_hash(
    sequence: int,
    event_id: str,
    event_type: str,
    payload_canonical: bytes,
    created_utc: str,
) -> str:
    return sha256_hex(
        "internal-outbox-v1",
        sequence,
        event_id,
        event_type,
        payload_canonical,
        created_utc,
    )


def _item(row: sqlite3.Row) -> OutboxItem:
    return OutboxItem(
        row["sequence"],
        row["event_id"],
        InternalEventType(row["event_type"]),
        row["payload_json"],
        row["status"],
        row["attempts"],
        row["version"],
        row["claim_token"],
    )


class InternalOutbox:
    def __init__(self, connection: sqlite3.Connection, clock: Clock | None = None) -> None:
        self._connection = connection
        self._clock = clock or SystemClock()

    def enqueue(
        self,
        token: LeaseToken,
        event_type: InternalEventType,
        payload: Mapping[str, Any],
        *,
        available_utc: datetime | None = None,
        event_id: str | None = None,
    ) -> OutboxItem:
        if not isinstance(event_type, InternalEventType):
            raise ValidationError("outbox accepts only InternalEventType")
        event_id = event_id or str(uuid.uuid4())
        try:
            uuid.UUID(event_id)
        except (ValueError, AttributeError) as exc:
            raise ValidationError("event_id must be a UUID") from exc
        payload_canonical = canonical_bytes(payload)
        payload_json = canonical_json(payload)
        observed = self._clock.observe()
        created_utc = format_utc(observed.utc)
        availability = format_utc(ensure_utc(available_utc)) if available_utc else created_utc
        with immediate_transaction(self._connection):
            assert_lease(self._connection, token, created_utc)
            row = self._connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 AS next FROM internal_outbox"
            ).fetchone()
            sequence = row["next"]
            content_hash = _content_hash(
                sequence,
                event_id,
                event_type.value,
                payload_canonical,
                created_utc,
            )
            self._connection.execute(
                """INSERT INTO internal_outbox
                   (sequence,event_id,event_type,payload_json,payload_canonical,created_utc,
                    available_utc,content_hash,status,attempts,version)
                   VALUES (?,?,?,?,?,?,?,?,'PENDING',0,1)""",
                (
                    sequence,
                    event_id,
                    event_type.value,
                    payload_json,
                    payload_canonical,
                    created_utc,
                    availability,
                    content_hash,
                ),
            )
        return OutboxItem(sequence, event_id, event_type, payload_json, "PENDING", 0, 1, None)

    def claim_next(self, consumer_id: str, lease_for: timedelta) -> OutboxItem | None:
        if not consumer_id or len(consumer_id) > 128:
            raise ValidationError("consumer_id must contain 1..128 characters")
        if lease_for <= timedelta(0):
            raise ValidationError("claim duration must be positive")
        observed = self._clock.observe()
        now = format_utc(observed.utc)
        claimed_until = format_utc(observed.utc + lease_for)
        claim_token = str(uuid.uuid4())
        with immediate_transaction(self._connection):
            row = self._connection.execute(
                """SELECT * FROM internal_outbox
                   WHERE available_utc <= ? AND (
                       status = 'PENDING' OR (status = 'CLAIMED' AND claimed_until_utc <= ?)
                   ) ORDER BY sequence LIMIT 1""",
                (now, now),
            ).fetchone()
            if row is None:
                return None
            cursor = self._connection.execute(
                """UPDATE internal_outbox
                   SET status='CLAIMED', claimed_by=?, claim_token=?, claimed_until_utc=?,
                       attempts=attempts+1, version=version+1
                   WHERE sequence=? AND version=?""",
                (consumer_id, claim_token, claimed_until, row["sequence"], row["version"]),
            )
            if cursor.rowcount != 1:
                raise ConcurrentWriteError("outbox claim lost compare-and-swap")
            claimed = self._connection.execute(
                "SELECT * FROM internal_outbox WHERE sequence=?", (row["sequence"],)
            ).fetchone()
        return _item(claimed)

    def mark_delivered(self, item: OutboxItem) -> OutboxItem:
        if item.status != "CLAIMED" or item.claim_token is None:
            raise ValidationError("only a claimed outbox item can be delivered")
        delivered = format_utc(self._clock.observe().utc)
        with immediate_transaction(self._connection):
            cursor = self._connection.execute(
                """UPDATE internal_outbox SET status='DELIVERED', claimed_by=NULL,
                   claim_token=NULL, claimed_until_utc=NULL, delivered_utc=?, version=version+1
                   WHERE sequence=? AND version=? AND status='CLAIMED' AND claim_token=?""",
                (delivered, item.sequence, item.version, item.claim_token),
            )
            if cursor.rowcount != 1:
                raise ConcurrentWriteError("outbox delivery lost compare-and-swap")
            row = self._connection.execute(
                "SELECT * FROM internal_outbox WHERE sequence=?", (item.sequence,)
            ).fetchone()
        return _item(row)

    def retry(self, item: OutboxItem, delay: timedelta, error_code: str) -> OutboxItem:
        if item.status != "CLAIMED" or item.claim_token is None:
            raise ValidationError("only a claimed outbox item can be retried")
        if delay < timedelta(0):
            raise ValidationError("retry delay must be non-negative")
        if not error_code or len(error_code) > 128:
            raise ValidationError("error_code must contain 1..128 characters")
        available = format_utc(self._clock.observe().utc + delay)
        with immediate_transaction(self._connection):
            cursor = self._connection.execute(
                """UPDATE internal_outbox SET status='PENDING', claimed_by=NULL,
                   claim_token=NULL, claimed_until_utc=NULL, available_utc=?,
                   last_error_code=?, version=version+1
                   WHERE sequence=? AND version=? AND status='CLAIMED' AND claim_token=?""",
                (available, error_code, item.sequence, item.version, item.claim_token),
            )
            if cursor.rowcount != 1:
                raise ConcurrentWriteError("outbox retry lost compare-and-swap")
            row = self._connection.execute(
                "SELECT * FROM internal_outbox WHERE sequence=?", (item.sequence,)
            ).fetchone()
        return _item(row)


def verify_outbox(connection: sqlite3.Connection) -> int:
    count = 0
    for row in connection.execute("SELECT * FROM internal_outbox ORDER BY sequence"):
        try:
            InternalEventType(row["event_type"])
        except ValueError as exc:
            raise IntegrityError(f"unknown internal outbox event at {row['sequence']}") from exc
        expected = _content_hash(
            row["sequence"],
            row["event_id"],
            row["event_type"],
            bytes(row["payload_canonical"]),
            row["created_utc"],
        )
        if row["content_hash"] != expected:
            raise IntegrityError(f"outbox content hash mismatch at {row['sequence']}")
        count += 1
    return count
