"""Offline-testable, private immutable-attempt lifecycle for XAUUSD read-only runs.

EXCLUSIVELY creates v12-attempt-<registration SHA>.jsonl beside private output.
First durable START is created before MT5.initialize. Every recorded poll / tick
chunk is flushed and fsynced. An unexpected interruption or missing terminal
event is INCOMPLETE_FAIL_CLOSED; explicit failure is FAIL_CLOSED. Neither is a
capture/calibration admission, and neither permits reuse of the registration.
Hash chaining detects accidental edits, NOT independently authentic broker data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

INITIAL_CHAIN = "0" * 64
_SUCCESS = "COMPLETED_RAW_NOT_ADMITTED"
_FAILURE = "FAIL_CLOSED"
_INCOMPLETE = "INCOMPLETE_FAIL_CLOSED"


class AttemptJournalError(ValueError):
    """Unknown/tampered/incomplete attempt; never auto-retry."""


def _sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(
        c in "0123456789abcdef" for c in value
    )


def _canonical(obj: dict[str, Any]) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _stamp() -> str:
    return datetime.now(UTC).isoformat()


def attempt_path(private_dir: Path, registration_sha256: str) -> Path:
    if not _sha(registration_sha256) or not private_dir.is_dir():
        raise AttemptJournalError("registered identity or PRIVATE directory absent")
    return private_dir.resolve() / ("v12-attempt-" + registration_sha256 + ".jsonl")


class AttemptJournal:
    def __init__(
        self, path: Path, registration_sha256: str, source: Any,
        clock: Callable[[], str] = _stamp,
    ) -> None:
        if not _sha(registration_sha256):
            raise AttemptJournalError("registration SHA-256 missing")
        if path.exists() or not path.parent.is_dir():
            raise AttemptJournalError("attempt already exists or private directory unknown")
        self._path = path
        self._clock = clock
        self._registration = registration_sha256
        self._next = 0
        self._previous = INITIAL_CHAIN
        self._final = False
        self._fd = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o600,
        )
        try:
            self.append("ATTEMPT_STARTED", {
                "registration_sha256": registration_sha256,
                "mode": "EXNESS_XAUUSD_DEMO_READ_ONLY_NOT_ADMITTED",
                "source": str(source),
            })
        except BaseException:
            os.close(self._fd)
            raise

    @property
    def path(self) -> Path:
        return self._path

    @property
    def final(self) -> bool:
        return self._final

    def append(self, kind: str, details: dict[str, Any]) -> str:
        if self._final or type(kind) is not str or not kind:
            raise AttemptJournalError("closed or malformed attempt event")
        event = {
            "seq": self._next,
            "prev_sha256": self._previous,
            "timestamp_utc": self._clock(),
            "kind": kind,
            "details": details,
        }
        checksum = hashlib.sha256(_canonical(event)).hexdigest()
        payload = _canonical({**event, "entry_sha256": checksum}) + b"\n"
        # One append, fail closed on short write/partial line.
        if os.write(self._fd, payload) != len(payload):
            raise AttemptJournalError("partial immutable journal write")
        os.fsync(self._fd)
        self._next += 1
        self._previous = checksum
        return checksum

    def failed(self, exception_name: str) -> None:
        if not self._final:
            # Never write raw exception text: it could contain private account
            # paths, secrets or unintended broker data.
            self.append(_FAILURE, {"exception_type": str(exception_name)})
            self._final = True

    def success(self, private_raw_sha256: str) -> None:
        if not _sha(private_raw_sha256):
            raise AttemptJournalError("private raw evidence digest absent")
        self.append(_SUCCESS, {
            "private_raw_sha256": private_raw_sha256,
            "registration_sha256": self._registration,
            "execution_or_costs_admitted": False,
        })
        self._final = True

    def close(self) -> None:
        os.close(self._fd)
        # Read-only flag is defense in depth only, NOT independent tamper-proof
        # provenance. An admin may still alter the file.
        try:
            self._path.chmod(0o400)
        except OSError:
            pass


def verify_attempt(
    path: Path, expected_registration_sha256: str,
    expected_private_raw_sha256: str | None = None,
) -> str:
    if not _sha(expected_registration_sha256) or not path.is_file():
        raise AttemptJournalError("original attempt or registration missing")
    if path.name != "v12-attempt-" + expected_registration_sha256 + ".jsonl":
        raise AttemptJournalError("attempt filename disagrees with registration")
    chain = INITIAL_CHAIN
    kinds: list[str] = []
    last: dict[str, Any] | None = None
    try:
        with path.open("rb") as stream:
            for number, raw in enumerate(stream):
                if not raw.endswith(b"\n"):
                    raise AttemptJournalError("truncated immutable attempt line")
                record = json.loads(raw)
                if type(record) is not dict or record.get("seq") != number:
                    raise AttemptJournalError("attempt reordered/duplicated")
                if record.get("prev_sha256") != chain:
                    raise AttemptJournalError("attempt SHA chain broken")
                payload = dict(record)
                digest = payload.pop("entry_sha256", None)
                if not _sha(digest) or digest != hashlib.sha256(
                    _canonical(payload)
                ).hexdigest():
                    raise AttemptJournalError("attempt payload tampered")
                if raw != _canonical(record) + b"\n":
                    raise AttemptJournalError("noncanonical attempt serialization")
                chain = digest
                kinds.append(record["kind"])
                if record["kind"] in (_SUCCESS, _FAILURE) and number != 0:
                    # Never silently append a different conclusion after
                    # failure or after a successful attempt.
                    remainder = stream.read()
                    if remainder:
                        raise AttemptJournalError("events after terminal result")
                last = record
    except (UnicodeDecodeError, json.JSONDecodeError, OSError) as exc:
        raise AttemptJournalError("unreadable or truncated private attempt") from exc
    if not kinds or kinds[0] != "ATTEMPT_STARTED" or last is None:
        raise AttemptJournalError("no durable ATTEMPT_STARTED")
    with path.open("rb") as stream:
        first = json.loads(stream.readline())
    if first["details"].get("registration_sha256") != expected_registration_sha256:
        raise AttemptJournalError("attempt bound to wrong registration")
    if last["kind"] == _FAILURE:
        return _FAILURE
    if last["kind"] != _SUCCESS:
        return _INCOMPLETE
    expected = last["details"].get("private_raw_sha256")
    if not _sha(expected) or (
        expected_private_raw_sha256 is not None
        and expected_private_raw_sha256 != expected
    ):
        raise AttemptJournalError("private raw output SHA not independently matched")
    if last["details"].get("execution_or_costs_admitted") is not False:
        raise AttemptJournalError("attempt incorrectly claims trade admission")
    return _SUCCESS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OFFLINE attempt integrity only")
    parser.add_argument("--verify-only", action="store_true", required=True)
    parser.add_argument("--journal", required=True, type=Path)
    parser.add_argument("--registration-sha256", required=True)
    parser.add_argument("--raw-sha256", required=True)
    args = parser.parse_args(argv)
    state = verify_attempt(
        args.journal, args.registration_sha256, args.raw_sha256
    )
    print("READ_ONLY_ATTEMPT_STATUS=" + state)
    print("SOURCE_ORIGIN_AND_COST_CALIBRATION_NOT_ADMITTED")
    return 0 if state == _SUCCESS else 17


if __name__ == "__main__":
    raise SystemExit(main())
