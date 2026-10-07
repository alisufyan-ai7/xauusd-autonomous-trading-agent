"""SQLite schema for local, execution-disabled control-plane state."""

# ruff: noqa: S608 -- interpolation is limited to closed enums and an integer constant.

from __future__ import annotations

import sqlite3

from xauusd_agent.core.model import AuditEventType, InternalEventType

SCHEMA_VERSION = 1
APPLICATION_ID = 0x58415531  # "XAU1"


def _quoted_values(values: list[str]) -> str:
    return ",".join("'" + value.replace("'", "''") + "'" for value in values)


AUDIT_TYPES = _quoted_values([item.value for item in AuditEventType])
INTERNAL_TYPES = _quoted_values([item.value for item in InternalEventType])

# Safe compile-time interpolation of closed internal enums and an integer schema version.
SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS storage_metadata (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    schema_version INTEGER NOT NULL,
    runtime_mode TEXT NOT NULL CHECK (runtime_mode = 'EXECUTION_DISABLED'),
    execution_capability TEXT NOT NULL CHECK (execution_capability = 'ABSENT')
) STRICT;

INSERT OR IGNORE INTO storage_metadata(
    singleton, schema_version, runtime_mode, execution_capability
)
VALUES (1, {SCHEMA_VERSION}, 'EXECUTION_DISABLED', 'ABSENT');

CREATE TABLE IF NOT EXISTS writer_lease (
    lease_name TEXT PRIMARY KEY,
    holder_id TEXT NOT NULL,
    fencing_token INTEGER NOT NULL CHECK (fencing_token > 0),
    version INTEGER NOT NULL CHECK (version > 0),
    acquired_utc TEXT NOT NULL,
    expires_utc TEXT NOT NULL,
    updated_utc TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS audit_journal (
    sequence INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    stream_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ({AUDIT_TYPES})),
    occurred_utc TEXT NOT NULL,
    monotonic_ns INTEGER NOT NULL CHECK (monotonic_ns >= 0),
    payload_json TEXT NOT NULL,
    payload_canonical BLOB NOT NULL,
    previous_hash TEXT NOT NULL CHECK (length(previous_hash) = 64),
    entry_hash TEXT NOT NULL UNIQUE CHECK (length(entry_hash) = 64),
    writer_fencing_token INTEGER NOT NULL CHECK (writer_fencing_token > 0)
) STRICT;

CREATE TRIGGER IF NOT EXISTS audit_journal_no_update
BEFORE UPDATE ON audit_journal BEGIN
    SELECT RAISE(ABORT, 'audit_journal is append-only');
END;

CREATE TRIGGER IF NOT EXISTS audit_journal_no_delete
BEFORE DELETE ON audit_journal BEGIN
    SELECT RAISE(ABORT, 'audit_journal is append-only');
END;

CREATE TRIGGER IF NOT EXISTS storage_metadata_no_update
BEFORE UPDATE ON storage_metadata BEGIN
    SELECT RAISE(ABORT, 'storage_metadata is immutable');
END;

CREATE TRIGGER IF NOT EXISTS storage_metadata_no_delete
BEFORE DELETE ON storage_metadata BEGIN
    SELECT RAISE(ABORT, 'storage_metadata is immutable');
END;

CREATE TABLE IF NOT EXISTS internal_outbox (
    sequence INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL CHECK (event_type IN ({INTERNAL_TYPES})),
    payload_json TEXT NOT NULL,
    payload_canonical BLOB NOT NULL,
    created_utc TEXT NOT NULL,
    available_utc TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE CHECK (length(content_hash) = 64),
    status TEXT NOT NULL CHECK (status IN ('PENDING','CLAIMED','DELIVERED')),
    claimed_by TEXT,
    claim_token TEXT,
    claimed_until_utc TEXT,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error_code TEXT,
    delivered_utc TEXT,
    version INTEGER NOT NULL CHECK (version > 0),
    CHECK (
        (status = 'PENDING' AND claimed_by IS NULL AND claim_token IS NULL
         AND claimed_until_utc IS NULL AND delivered_utc IS NULL)
        OR (status = 'CLAIMED' AND claimed_by IS NOT NULL AND claim_token IS NOT NULL
            AND claimed_until_utc IS NOT NULL AND delivered_utc IS NULL)
        OR (status = 'DELIVERED' AND claimed_by IS NULL AND claim_token IS NULL
            AND claimed_until_utc IS NULL AND delivered_utc IS NOT NULL)
    )
) STRICT;

CREATE INDEX IF NOT EXISTS internal_outbox_ready_idx
ON internal_outbox(status, available_utc, sequence);
"""


def initialize_schema(connection: sqlite3.Connection) -> None:
    current = connection.execute("PRAGMA user_version").fetchone()[0]
    if current not in (0, SCHEMA_VERSION):
        raise sqlite3.DatabaseError(f"unsupported schema version: {current}")
    connection.executescript(SCHEMA_SQL)
    connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
