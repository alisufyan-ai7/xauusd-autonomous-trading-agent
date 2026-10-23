"""Durable DEMO watchdog + dual-channel incident outbox, broker-free.

No credentials, networks, trading or background tasks. The VPS worker must
call heartbeat() and check_fresh() through its own supervised loop. Staleness
latches QUARANTINED; no automatic recovery or unknown-position closure.
Incident delivery is at-least-once; provider ambiguity may duplicate alerts,
never enable trading. SMTP/Telegram adapters need independent delivery drills.
"""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

from .envelope import DemoSafetyError


class DualAlertTransport(Protocol):
    def send_email(self, incident_key: str, message: str) -> None: ...
    def send_telegram(self, incident_key: str, message: str) -> None: ...


@dataclass(frozen=True, slots=True)
class AlertReceipt:
    incident_key: str
    email_sent: bool
    telegram_sent: bool

    @property
    def delivered_both(self) -> bool:
        return self.email_sent and self.telegram_sent


class PersistentDemoSafetyWatchdog:
    def __init__(self, path: Path, *, max_age_seconds: int = 30) -> None:
        if not 5 <= max_age_seconds <= 3600:
            raise DemoSafetyError("watchdog threshold out of policy bounds")
        self.max_age_seconds = max_age_seconds
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, isolation_level=None)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS watchdog (
                id INTEGER PRIMARY KEY CHECK(id=1),
                last_utc TEXT, state TEXT NOT NULL,
                reason TEXT NOT NULL
            ) STRICT"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS incident_outbox (
                incident_key TEXT PRIMARY KEY,
                message TEXT NOT NULL, email_ok INTEGER NOT NULL,
                telegram_ok INTEGER NOT NULL
            ) STRICT"""
        )
        self.conn.execute(
            "INSERT OR IGNORE INTO watchdog VALUES(1,NULL,'KILLED','DEFAULT')"
        )

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> PersistentDemoSafetyWatchdog:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _utc(t: datetime) -> str:
        if t.tzinfo is None or t.utcoffset() != timedelta(0):
            raise DemoSafetyError("watchdog requires exact UTC")
        return t.astimezone(UTC).isoformat()

    def status(self) -> str:
        row = self.conn.execute("SELECT state FROM watchdog WHERE id=1").fetchone()
        if row is None:
            raise DemoSafetyError("watchdog state unavailable")
        return str(row[0])

    def arm_attended(self, *, now: datetime, operator_token: str) -> None:
        if operator_token != "P1-ARM-DEMO-WATCHDOG":
            raise DemoSafetyError("human P1 watchdog activation required")
        if self.status() != "KILLED":
            raise DemoSafetyError("unsafe watchdog recovery requires P1 review")
        instant = self._utc(now)
        self.conn.execute(
            "UPDATE watchdog SET state='ACTIVE',last_utc=?,reason='P1_ARM' WHERE id=1",
            (instant,),
        )

    def kill(self, *, now: datetime, reason: str) -> None:
        self._utc(now)
        if not reason.strip():
            raise DemoSafetyError("kill reason empty")
        self.conn.execute(
            "UPDATE watchdog SET state='KILLED',reason=? WHERE id=1",
            (reason[:150],),
        )
        self.queue_incident(
            observed_utc=now, code="E1_KILL", explanation=reason
        )

    def heartbeat(self, *, now: datetime) -> None:
        instant = self._utc(now)
        row = self.conn.execute(
            "SELECT last_utc,state FROM watchdog WHERE id=1"
        ).fetchone()
        if row is None or row[1] != "ACTIVE":
            raise DemoSafetyError("watchdog not active")
        if row[0] is not None:
            old = datetime.fromisoformat(row[0])
            if now < old or now - old > timedelta(seconds=self.max_age_seconds):
                self._quarantine(now, "HEARTBEAT_STALE_OR_ROLLBACK")
                raise DemoSafetyError("watchdog stale, human recovery only")
        self.conn.execute(
            "UPDATE watchdog SET last_utc=? WHERE id=1", (instant,)
        )

    def check_fresh(self, *, now: datetime) -> bool:
        self._utc(now)
        row = self.conn.execute(
            "SELECT last_utc,state FROM watchdog WHERE id=1"
        ).fetchone()
        if row is None or row[1] != "ACTIVE" or row[0] is None:
            return False
        previous = datetime.fromisoformat(row[0])
        if now < previous or now - previous > timedelta(seconds=self.max_age_seconds):
            self._quarantine(now, "HEARTBEAT_STALE_OR_ROLLBACK")
            return False
        return True

    def _quarantine(self, when: datetime, reason: str) -> None:
        self.conn.execute(
            "UPDATE watchdog SET state='QUARANTINED',reason=? WHERE id=1",
            (reason,),
        )
        self.queue_incident(
            observed_utc=when, code="WATCHDOG_QUARANTINED", explanation=reason
        )

    def queue_incident(
        self, *, observed_utc: datetime, code: str, explanation: str
    ) -> str:
        instant = self._utc(observed_utc)
        if (
            not code or len(code) > 60 or len(explanation) > 300
            or not explanation or "\n" in explanation or "\r" in explanation
        ):
            raise DemoSafetyError("incident contains invalid unbounded text")
        # Operator supplies sanitized explanations, never raw MT5 login,
        # password, access token or broker request payload.
        message = f"[XAUUSD DEMO] {instant} {code}: {explanation}"
        ident = hashlib.sha256(message.encode()).hexdigest()
        self.conn.execute(
            "INSERT OR IGNORE INTO incident_outbox VALUES (?,?,0,0)",
            (ident, message),
        )
        return ident

    def deliver(self, key: str, transport: DualAlertTransport) -> AlertReceipt:
        """Require two independent acknowledgements; no implied success."""
        row = self.conn.execute(
            "SELECT message,email_ok,telegram_ok FROM incident_outbox "
            "WHERE incident_key=?", (key,),
        ).fetchone()
        if row is None:
            raise DemoSafetyError("unknown incident key")
        message, mail, telegram = str(row[0]), bool(row[1]), bool(row[2])
        if not mail:
            transport.send_email(key, message)
            self.conn.execute(
                "UPDATE incident_outbox SET email_ok=1 WHERE incident_key=?",
                (key,),
            )
            mail = True
        if not telegram:
            transport.send_telegram(key, message)
            self.conn.execute(
                "UPDATE incident_outbox SET telegram_ok=1 WHERE incident_key=?",
                (key,),
            )
            telegram = True
        return AlertReceipt(key, mail, telegram)

    def undelivered_count(self) -> int:
        return int(self.conn.execute(
            "SELECT COUNT(*) FROM incident_outbox "
            "WHERE email_ok=0 OR telegram_ok=0"
        ).fetchone()[0])
