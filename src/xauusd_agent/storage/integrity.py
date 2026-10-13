"""Startup verification that fails closed before runtime readiness."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from xauusd_agent.core.errors import IntegrityError
from xauusd_agent.core.model import ExecutionCapability, RuntimeMode

from .journal import verify_journal
from .outbox import verify_outbox
from .schema import APPLICATION_ID, SCHEMA_VERSION

_REQUIRED_TRIGGERS = {
    "audit_journal_no_update",
    "audit_journal_no_delete",
    "storage_metadata_no_update",
    "storage_metadata_no_delete",
}


@dataclass(frozen=True, slots=True)
class IntegrityReport:
    schema_version: int
    journal_entries: int
    outbox_entries: int
    runtime_mode: RuntimeMode
    execution_capability: ExecutionCapability


def verify_startup(connection: sqlite3.Connection) -> IntegrityReport:
    quick = connection.execute("PRAGMA integrity_check").fetchall()
    if len(quick) != 1 or quick[0][0] != "ok":
        raise IntegrityError("SQLite integrity_check failed")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise IntegrityError("SQLite foreign key check failed")
    if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
        raise IntegrityError("unexpected schema version")
    if connection.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID:
        raise IntegrityError("unexpected SQLite application id")
    metadata = connection.execute("SELECT * FROM storage_metadata WHERE singleton=1").fetchone()
    if metadata is None or metadata["schema_version"] != SCHEMA_VERSION:
        raise IntegrityError("storage metadata is absent or inconsistent")
    try:
        mode = RuntimeMode(metadata["runtime_mode"])
        capability = ExecutionCapability(metadata["execution_capability"])
    except ValueError as exc:
        raise IntegrityError("storage capability metadata is invalid") from exc
    if mode is not RuntimeMode.EXECUTION_DISABLED or capability is not ExecutionCapability.ABSENT:
        raise IntegrityError("storage is not execution-disabled")
    triggers = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_schema WHERE type='trigger'")
    }
    missing = _REQUIRED_TRIGGERS - triggers
    if missing:
        raise IntegrityError(f"required immutability triggers missing: {sorted(missing)}")
    return IntegrityReport(
        SCHEMA_VERSION,
        verify_journal(connection),
        verify_outbox(connection),
        mode,
        capability,
    )
