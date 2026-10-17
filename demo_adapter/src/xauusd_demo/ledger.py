"""Durable request ledger that forbids duplicate and uncertain demo submission."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .envelope import DemoOrderRequest, DemoSafetyError


class DemoSubmissionLedger:
    def __init__(self, path: Path, *, max_daily_submissions: int) -> None:
        if max_daily_submissions < 1:
            raise DemoSafetyError("max_daily_submissions must be positive")
        self._path = path
        self._max_daily_submissions = max_daily_submissions
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS demo_submission (
                request_id TEXT PRIMARY KEY,
                created_utc TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                volume_lots TEXT NOT NULL,
                stop_loss TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('PREPARED','ACKNOWLEDGED','UNCERTAIN')
                ),
                mt5_retcode INTEGER,
                order_ticket TEXT,
                detail TEXT
            ) STRICT;
            """
        )

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> DemoSubmissionLedger:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def reserve(self, request: DemoOrderRequest, *, now: datetime) -> None:
        request.validate()
        if now.tzinfo is None or now.utcoffset() is None:
            raise DemoSafetyError("ledger timestamp must be timezone-aware")
        utc = now.astimezone(UTC)
        date_prefix = utc.date().isoformat()

        self._connection.execute("BEGIN IMMEDIATE")
        try:
            uncertain = self._connection.execute(
                "SELECT request_id FROM demo_submission WHERE status='UNCERTAIN' LIMIT 1"
            ).fetchone()
            if uncertain is not None:
                raise DemoSafetyError(
                    "uncertain prior submission requires reconciliation before new risk"
                )

            duplicate = self._connection.execute(
                "SELECT status FROM demo_submission WHERE request_id=?",
                (request.request_id,),
            ).fetchone()
            if duplicate is not None:
                raise DemoSafetyError("duplicate request_id is forbidden")

            count = self._connection.execute(
                """
                SELECT COUNT(*) FROM demo_submission
                WHERE substr(created_utc,1,10)=?
                """,
                (date_prefix,),
            ).fetchone()[0]
            if int(count) >= self._max_daily_submissions:
                raise DemoSafetyError("daily demo submission budget exhausted")

            self._connection.execute(
                """
                INSERT INTO demo_submission(
                    request_id, created_utc, symbol, side,
                    volume_lots, stop_loss, status
                ) VALUES (?, ?, ?, ?, ?, ?, 'PREPARED')
                """,
                (
                    request.request_id,
                    utc.isoformat().replace("+00:00", "Z"),
                    request.symbol,
                    request.side.value,
                    str(request.volume_lots),
                    str(request.stop_loss),
                ),
            )
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def mark_uncertain(self, request_id: str, *, detail: str) -> None:
        cursor = self._connection.execute(
            """
            UPDATE demo_submission
            SET status='UNCERTAIN', detail=?
            WHERE request_id=? AND status='PREPARED'
            """,
            (detail[:1000], request_id),
        )
        if cursor.rowcount != 1:
            self._connection.rollback()
            raise DemoSafetyError("cannot mark unknown or finalized request uncertain")
        self._connection.commit()

    def mark_acknowledged(
        self,
        request_id: str,
        *,
        mt5_retcode: int,
        order_ticket: str,
    ) -> None:
        cursor = self._connection.execute(
            """
            UPDATE demo_submission
            SET status='ACKNOWLEDGED', mt5_retcode=?, order_ticket=?
            WHERE request_id=? AND status='PREPARED'
            """,
            (mt5_retcode, order_ticket, request_id),
        )
        if cursor.rowcount != 1:
            self._connection.rollback()
            raise DemoSafetyError("cannot acknowledge unknown or finalized request")
        self._connection.commit()

    def status(self, request_id: str) -> str | None:
        row = self._connection.execute(
            "SELECT status FROM demo_submission WHERE request_id=?",
            (request_id,),
        ).fetchone()
        return None if row is None else str(row["status"])
