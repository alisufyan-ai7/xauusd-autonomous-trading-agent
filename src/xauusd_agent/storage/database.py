"""Hardened SQLite connection and transaction helpers."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from xauusd_agent.core.errors import IntegrityError

from .schema import initialize_schema


def open_database(path: str | Path) -> sqlite3.Connection:
    """Open a local database with durability and fail-closed pragmas."""

    connection = sqlite3.connect(
        str(path),
        timeout=5.0,
        isolation_level=None,
        check_same_thread=True,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA synchronous = FULL")
    connection.execute("PRAGMA trusted_schema = OFF")
    journal_mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
    # SQLite reports ``memory`` only for an explicit in-memory test database.
    if str(journal_mode).lower() not in {"wal", "memory"}:
        connection.close()
        raise IntegrityError(f"SQLite WAL mode unavailable: {journal_mode}")
    return connection


def create_database(path: str | Path) -> sqlite3.Connection:
    connection = open_database(path)
    try:
        initialize_schema(connection)
    except Exception:
        connection.close()
        raise
    return connection


@contextmanager
def immediate_transaction(connection: sqlite3.Connection) -> Iterator[None]:
    if connection.in_transaction:
        raise IntegrityError("nested SQLite transactions are forbidden")
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        connection.rollback()
        raise
    else:
        connection.commit()
