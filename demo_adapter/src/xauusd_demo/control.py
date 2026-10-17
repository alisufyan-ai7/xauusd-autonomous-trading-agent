"""Durable deterministic kill/quarantine control for bounded demo execution."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from .envelope import DemoActivationPermit, DemoIdentity, DemoSafetyError

ARM_CONFIRMATION = "ARM-BOUNDED-DEMO-XAUUSD"
RESET_CONFIRMATION = "RESET-DEMO-QUARANTINE-TO-KILLED"


class DemoControlState(StrEnum):
    KILLED = "KILLED"
    ACTIVE = "ACTIVE"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True, slots=True)
class DemoControlSnapshot:
    state: DemoControlState
    activation_id: str | None
    account_id_sha256: str | None
    server: str | None
    max_daily_submissions: int | None
    reason: str
    updated_utc: str


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DemoSafetyError("control timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class DemoControlStore:
    """Single-writer durable control state.

    The store defaults to KILLED. QUARANTINED cannot transition directly back
    to ACTIVE; an explicit reset to KILLED is required before a fresh arm.
    """

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS demo_control (
                singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
                state TEXT NOT NULL CHECK(state IN ('KILLED','ACTIVE','QUARANTINED')),
                activation_id TEXT,
                account_id_sha256 TEXT,
                server TEXT,
                max_daily_submissions INTEGER,
                reason TEXT NOT NULL,
                updated_utc TEXT NOT NULL
            ) STRICT;
            """
        )
        row = self._connection.execute(
            "SELECT singleton_id FROM demo_control WHERE singleton_id=1"
        ).fetchone()
        if row is None:
            self._connection.execute(
                """
                INSERT INTO demo_control(
                    singleton_id, state, activation_id, account_id_sha256,
                    server, max_daily_submissions, reason, updated_utc
                ) VALUES (1,'KILLED',NULL,NULL,NULL,NULL,'INITIAL_DEFAULT',?)
                """,
                ("1970-01-01T00:00:00Z",),
            )
            self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> DemoControlStore:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def snapshot(self) -> DemoControlSnapshot:
        row = self._connection.execute(
            """
            SELECT state, activation_id, account_id_sha256, server,
                   max_daily_submissions, reason, updated_utc
            FROM demo_control WHERE singleton_id=1
            """
        ).fetchone()
        if row is None:
            raise DemoSafetyError("demo control row is missing")
        return DemoControlSnapshot(
            state=DemoControlState(str(row["state"])),
            activation_id=None if row["activation_id"] is None else str(row["activation_id"]),
            account_id_sha256=(
                None if row["account_id_sha256"] is None else str(row["account_id_sha256"])
            ),
            server=None if row["server"] is None else str(row["server"]),
            max_daily_submissions=(
                None
                if row["max_daily_submissions"] is None
                else int(row["max_daily_submissions"])
            ),
            reason=str(row["reason"]),
            updated_utc=str(row["updated_utc"]),
        )

    def arm(
        self,
        *,
        permit: DemoActivationPermit,
        identity: DemoIdentity,
        now: datetime,
        confirmation_phrase: str,
    ) -> None:
        if confirmation_phrase != ARM_CONFIRMATION:
            raise DemoSafetyError("exact demo arm confirmation phrase required")
        identity.validate()
        permit.validate(now=now)
        if permit.account_id_sha256 != identity.account_id_sha256:
            raise DemoSafetyError("arm account fingerprint mismatch")
        if permit.server != identity.server:
            raise DemoSafetyError("arm server mismatch")

        current = self.snapshot()
        if current.state is DemoControlState.QUARANTINED:
            raise DemoSafetyError("quarantined control requires explicit reset before re-arm")

        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._connection.execute(
                """
                UPDATE demo_control
                SET state='ACTIVE',
                    activation_id=?,
                    account_id_sha256=?,
                    server=?,
                    max_daily_submissions=?,
                    reason='OWNER_GATED_ACTIVATION',
                    updated_utc=?
                WHERE singleton_id=1
                """,
                (
                    permit.activation_id,
                    permit.account_id_sha256,
                    permit.server,
                    permit.max_daily_submissions,
                    _utc_text(now),
                ),
            )
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def kill(self, *, reason: str, now: datetime) -> None:
        clean_reason = reason.strip()
        if not clean_reason:
            raise DemoSafetyError("kill reason must be non-empty")
        self._connection.execute(
            """
            UPDATE demo_control
            SET state='KILLED',
                activation_id=NULL,
                account_id_sha256=NULL,
                server=NULL,
                max_daily_submissions=NULL,
                reason=?,
                updated_utc=?
            WHERE singleton_id=1
            """,
            (clean_reason[:500], _utc_text(now)),
        )
        self._connection.commit()

    def quarantine(self, *, reason: str, now: datetime) -> None:
        clean_reason = reason.strip()
        if not clean_reason:
            raise DemoSafetyError("quarantine reason must be non-empty")
        self._connection.execute(
            """
            UPDATE demo_control
            SET state='QUARANTINED',
                activation_id=NULL,
                account_id_sha256=NULL,
                server=NULL,
                max_daily_submissions=NULL,
                reason=?,
                updated_utc=?
            WHERE singleton_id=1
            """,
            (clean_reason[:500], _utc_text(now)),
        )
        self._connection.commit()

    def reset_quarantine_to_killed(
        self,
        *,
        confirmation_phrase: str,
        reason: str,
        now: datetime,
    ) -> None:
        if confirmation_phrase != RESET_CONFIRMATION:
            raise DemoSafetyError("exact quarantine reset confirmation phrase required")
        current = self.snapshot()
        if current.state is not DemoControlState.QUARANTINED:
            raise DemoSafetyError("quarantine reset is only valid from QUARANTINED")
        self.kill(reason=f"RESET_TO_KILLED:{reason.strip()}", now=now)

    def assert_active(
        self,
        *,
        permit: DemoActivationPermit,
        identity: DemoIdentity,
        now: datetime,
    ) -> None:
        identity.validate()
        try:
            permit.validate(now=now)
        except DemoSafetyError:
            self.kill(reason="ACTIVATION_PERMIT_INVALID_OR_EXPIRED", now=now)
            raise

        current = self.snapshot()
        if current.state is not DemoControlState.ACTIVE:
            raise DemoSafetyError(f"demo control is not ACTIVE: {current.state.value}")

        matches = (
            current.activation_id == permit.activation_id
            and current.account_id_sha256 == identity.account_id_sha256
            and current.account_id_sha256 == permit.account_id_sha256
            and current.server == identity.server
            and current.server == permit.server
            and current.max_daily_submissions == permit.max_daily_submissions
        )
        if not matches:
            self.quarantine(reason="ACTIVE_CONTROL_BINDING_MISMATCH", now=now)
            raise DemoSafetyError("active demo control binding mismatch")
