"""Append-only, hash-chained audit journal."""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from xauusd_agent.core.canonical import canonical_bytes, canonical_json, sha256_hex
from xauusd_agent.core.clock import Clock, SystemClock, format_utc
from xauusd_agent.core.errors import IntegrityError, ValidationError
from xauusd_agent.core.model import AuditEventType

from .database import immediate_transaction
from .lease import LeaseToken, assert_lease

GENESIS_HASH = "0" * 64


@dataclass(frozen=True, slots=True)
class JournalEntry:
    sequence: int
    event_id: str
    stream_id: str
    event_type: AuditEventType
    occurred_utc: str
    monotonic_ns: int
    payload_json: str
    previous_hash: str
    entry_hash: str
    writer_fencing_token: int


def _entry_hash(
    sequence: int,
    event_id: str,
    stream_id: str,
    event_type: str,
    occurred_utc: str,
    monotonic_ns: int,
    payload_canonical: bytes,
    previous_hash: str,
    writer_fencing_token: int,
) -> str:
    return sha256_hex(
        "audit-journal-v1",
        sequence,
        event_id,
        stream_id,
        event_type,
        occurred_utc,
        monotonic_ns,
        payload_canonical,
        previous_hash,
        writer_fencing_token,
    )


class AuditJournal:
    def __init__(self, connection: sqlite3.Connection, clock: Clock | None = None) -> None:
        self._connection = connection
        self._clock = clock or SystemClock()

    def append(
        self,
        token: LeaseToken,
        stream_id: str,
        event_type: AuditEventType,
        payload: Mapping[str, Any],
        *,
        event_id: str | None = None,
    ) -> JournalEntry:
        if not isinstance(event_type, AuditEventType):
            raise ValidationError("event_type must be AuditEventType")
        if not stream_id or len(stream_id) > 256:
            raise ValidationError("stream_id must contain 1..256 characters")
        event_id = event_id or str(uuid.uuid4())
        try:
            uuid.UUID(event_id)
        except (ValueError, AttributeError) as exc:
            raise ValidationError("event_id must be a UUID") from exc
        payload_canonical = canonical_bytes(payload)
        payload_json = canonical_json(payload)
        observed = self._clock.observe()
        occurred_utc = format_utc(observed.utc)

        with immediate_transaction(self._connection):
            assert_lease(self._connection, token, occurred_utc)
            prior = self._connection.execute(
                "SELECT sequence, entry_hash FROM audit_journal ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            sequence = 1 if prior is None else prior["sequence"] + 1
            previous_hash = GENESIS_HASH if prior is None else prior["entry_hash"]
            entry_hash = _entry_hash(
                sequence,
                event_id,
                stream_id,
                event_type.value,
                occurred_utc,
                observed.monotonic_ns,
                payload_canonical,
                previous_hash,
                token.fencing_token,
            )
            self._connection.execute(
                """INSERT INTO audit_journal
                   (sequence,event_id,stream_id,event_type,occurred_utc,monotonic_ns,
                    payload_json,payload_canonical,previous_hash,entry_hash,writer_fencing_token)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    sequence,
                    event_id,
                    stream_id,
                    event_type.value,
                    occurred_utc,
                    observed.monotonic_ns,
                    payload_json,
                    payload_canonical,
                    previous_hash,
                    entry_hash,
                    token.fencing_token,
                ),
            )
        return JournalEntry(
            sequence,
            event_id,
            stream_id,
            event_type,
            occurred_utc,
            observed.monotonic_ns,
            payload_json,
            previous_hash,
            entry_hash,
            token.fencing_token,
        )


def verify_journal(connection: sqlite3.Connection) -> int:
    expected_sequence = 1
    previous_hash = GENESIS_HASH
    for row in connection.execute("SELECT * FROM audit_journal ORDER BY sequence"):
        if row["sequence"] != expected_sequence:
            raise IntegrityError("audit journal sequence is not contiguous")
        if row["previous_hash"] != previous_hash:
            raise IntegrityError(f"audit journal previous hash mismatch at {expected_sequence}")
        expected_hash = _entry_hash(
            row["sequence"],
            row["event_id"],
            row["stream_id"],
            row["event_type"],
            row["occurred_utc"],
            row["monotonic_ns"],
            bytes(row["payload_canonical"]),
            row["previous_hash"],
            row["writer_fencing_token"],
        )
        if row["entry_hash"] != expected_hash:
            raise IntegrityError(f"audit journal entry hash mismatch at {expected_sequence}")
        previous_hash = expected_hash
        expected_sequence += 1
    return expected_sequence - 1
