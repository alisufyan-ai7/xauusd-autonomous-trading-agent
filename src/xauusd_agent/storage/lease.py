"""Single-writer lease with compare-and-swap and fencing tokens."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import timedelta

from xauusd_agent.core.clock import Clock, SystemClock, format_utc, parse_utc
from xauusd_agent.core.errors import ConcurrentWriteError, LeaseError, ValidationError

from .database import immediate_transaction

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


@dataclass(frozen=True, slots=True)
class LeaseToken:
    lease_name: str
    holder_id: str
    fencing_token: int
    version: int
    expires_utc: str


def _identifier(value: str, name: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ValidationError(f"invalid {name}")
    return value


def assert_lease(connection: sqlite3.Connection, token: LeaseToken, now_utc: str) -> None:
    row = connection.execute(
        """SELECT holder_id, fencing_token, version, expires_utc
           FROM writer_lease WHERE lease_name = ?""",
        (token.lease_name,),
    ).fetchone()
    if row is None:
        raise LeaseError("writer lease does not exist")
    if (
        row["holder_id"] != token.holder_id
        or row["fencing_token"] != token.fencing_token
        or row["version"] != token.version
    ):
        raise LeaseError("writer lease token is stale")
    if parse_utc(row["expires_utc"]) <= parse_utc(now_utc):
        raise LeaseError("writer lease has expired")


class WriterLease:
    def __init__(self, connection: sqlite3.Connection, clock: Clock | None = None) -> None:
        self._connection = connection
        self._clock = clock or SystemClock()

    def acquire(self, lease_name: str, holder_id: str, ttl: timedelta) -> LeaseToken:
        lease_name = _identifier(lease_name, "lease_name")
        holder_id = _identifier(holder_id, "holder_id")
        if ttl <= timedelta(0):
            raise ValidationError("lease ttl must be positive")
        observed = self._clock.observe()
        now = observed.utc
        expires = now + ttl
        with immediate_transaction(self._connection):
            row = self._connection.execute(
                "SELECT * FROM writer_lease WHERE lease_name = ?", (lease_name,)
            ).fetchone()
            if row is None:
                self._connection.execute(
                    "INSERT INTO writer_lease VALUES (?, ?, 1, 1, ?, ?, ?)",
                    (lease_name, holder_id, format_utc(now), format_utc(expires), format_utc(now)),
                )
                return LeaseToken(lease_name, holder_id, 1, 1, format_utc(expires))

            active = parse_utc(row["expires_utc"]) > now
            if active:
                raise LeaseError("writer lease is already held")
            cursor = self._connection.execute(
                """UPDATE writer_lease
                   SET holder_id = ?, fencing_token = fencing_token + 1,
                       version = version + 1, acquired_utc = ?, expires_utc = ?, updated_utc = ?
                   WHERE lease_name = ? AND version = ? AND expires_utc <= ?""",
                (
                    holder_id,
                    format_utc(now),
                    format_utc(expires),
                    format_utc(now),
                    lease_name,
                    row["version"],
                    format_utc(now),
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrentWriteError("writer lease acquisition lost compare-and-swap")
            return LeaseToken(
                lease_name,
                holder_id,
                row["fencing_token"] + 1,
                row["version"] + 1,
                format_utc(expires),
            )

    def renew(self, token: LeaseToken, ttl: timedelta) -> LeaseToken:
        if ttl <= timedelta(0):
            raise ValidationError("lease ttl must be positive")
        observed = self._clock.observe()
        now_text = format_utc(observed.utc)
        expires_text = format_utc(observed.utc + ttl)
        with immediate_transaction(self._connection):
            assert_lease(self._connection, token, now_text)
            cursor = self._connection.execute(
                """UPDATE writer_lease SET version = version + 1, expires_utc = ?, updated_utc = ?
                   WHERE lease_name = ? AND holder_id = ? AND fencing_token = ? AND version = ?""",
                (
                    expires_text,
                    now_text,
                    token.lease_name,
                    token.holder_id,
                    token.fencing_token,
                    token.version,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrentWriteError("writer lease renewal lost compare-and-swap")
        return LeaseToken(
            token.lease_name,
            token.holder_id,
            token.fencing_token,
            token.version + 1,
            expires_text,
        )

    def release(self, token: LeaseToken) -> None:
        observed = self._clock.observe()
        now_text = format_utc(observed.utc)
        with immediate_transaction(self._connection):
            assert_lease(self._connection, token, now_text)
            cursor = self._connection.execute(
                """UPDATE writer_lease SET version = version + 1, expires_utc = ?, updated_utc = ?
                   WHERE lease_name = ? AND holder_id = ? AND fencing_token = ? AND version = ?""",
                (
                    now_text,
                    now_text,
                    token.lease_name,
                    token.holder_id,
                    token.fencing_token,
                    token.version,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrentWriteError("writer lease release lost compare-and-swap")
