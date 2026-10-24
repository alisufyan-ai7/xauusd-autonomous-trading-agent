"""Single-process, long-running Exness DEMO supervisor host.

The durable coordinator is reused on every cycle and persists setup keys,
pending order tickets, fills, closures and error quarantine. A cross-process
OS file lock prevents duplicate writers, while the broker-confirmed pending
and known-position state survives restart. No second order sender exists.
"""
from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from importlib import import_module
from pathlib import Path
from typing import Any

from .continuous_coordinator import ContinuousDemoCoordinator, QualifiedDemoBrokerPort
from .daily_broker_research import DailyBrokerResearch
from .envelope import DemoSafetyError
from .ops_safety_watchdog import PersistentDemoSafetyWatchdog
from .vps_alert_delivery import VPSDualAlertTransport


@contextmanager
def one_os_process_lock(path: Path) -> Iterator[None]:
    """Nonblocking kernel lock, released on process death on Windows/Linux."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as file:
        file.seek(0)
        if file.read(1) == b"":
            file.seek(0)
            file.write(b"1")
            file.flush()
            os.fsync(file.fileno())
        file.seek(0)
        if os.name == "nt":
            windows_lock: Any = import_module("msvcrt")

            try:
                windows_lock.locking(
                    file.fileno(), windows_lock.LK_NBLCK, 1
                )
            except OSError as exc:
                raise DemoSafetyError("another DEMO writer is already running") from exc
            try:
                yield
            finally:
                file.seek(0)
                windows_lock.locking(
                    file.fileno(), windows_lock.LK_UNLCK, 1
                )
        else:
            posix_lock: Any = import_module("fcntl")

            try:
                posix_lock.flock(
                    file.fileno(), posix_lock.LOCK_EX | posix_lock.LOCK_NB
                )
            except OSError as exc:
                raise DemoSafetyError("another DEMO writer is already running") from exc
            try:
                yield
            finally:
                posix_lock.flock(file.fileno(), posix_lock.LOCK_UN)


class ContinuousDemoWorker:
    """Multiple orders across days, one at a time; never a one-order canary."""

    def __init__(
        self,
        *,
        coordinator: ContinuousDemoCoordinator,
        port: QualifiedDemoBrokerPort,
        watchdog: PersistentDemoSafetyWatchdog,
        state_directory: Path,
        polling_seconds: float = 5.0,
        research: DailyBrokerResearch | None = None,
        transport: VPSDualAlertTransport | None = None,
    ) -> None:
        if not 1 <= polling_seconds <= 60:
            raise DemoSafetyError("worker poll interval must be 1..60 seconds")
        self._coordinator = coordinator
        self._port = port
        self._watchdog = watchdog
        self._folder = state_directory
        self._poll = polling_seconds
        self._research = research
        self._transport = transport
        self._last_status: datetime | None = None
        self._last_alert_attempt: datetime | None = None
        self._last_audit: tuple[str, ...] | None = None
        self._last_written: datetime | None = None

    def _write_audit(self, record: dict[str, object]) -> None:
        """Log state transitions and 15-minute heartbeat, not every 5s poll.

        Limit recent operator logs to about 16 MiB. Broker cash, order,
        position and risk receipts remain in the durable SQLite ledger.
        A heartbeat never replaces those immutable transaction records.
        """
        now = datetime.fromisoformat(str(record["utc"]))
        identity = tuple(str(record.get(k, "")) for k in (
            "state", "action", "reason", "strategy_status",
        ))
        critical = identity[0] != "ACTIVE" or identity[1] not in (
            "NO_ORDER", "MONITOR_PENDING_ORDER", "MONITOR_KNOWN_POSITION",
        )
        if (
            not critical
            and identity == self._last_audit
            and self._last_written is not None
            and now - self._last_written < timedelta(minutes=15)
        ):
            return
        self._folder.mkdir(parents=True, exist_ok=True)
        path = self._folder / "cycles.jsonl"
        if path.exists() and path.stat().st_size >= 4 * 1024 * 1024:
            for i in range(3, 0, -1):
                old = self._folder / f"cycles.{i}.jsonl"
                newer = self._folder / f"cycles.{i+1}.jsonl"
                if old.exists():
                    if i == 3:
                        old.unlink()
                    else:
                        old.replace(newer)
            path.replace(self._folder / "cycles.1.jsonl")
        entry = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        with path.open("a", encoding="utf-8") as log:
            log.write(entry)
            log.flush()
            os.fsync(log.fileno())
        self._last_audit = identity
        self._last_written = now


    def _status(self, data: dict[str, object], now: datetime) -> None:
        if (
            self._last_status is not None
            and now-self._last_status < timedelta(seconds=30)
        ):
            return
        self._folder.mkdir(parents=True, exist_ok=True)
        final = self._folder / "health.json"
        tmp = self._folder / "health.json.tmp"
        with tmp.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        tmp.replace(final)
        self._last_status = now

    def _alert_pending(self, now: datetime) -> None:
        if self._transport is None or not self._transport.configured:
            return
        if (
            self._last_alert_attempt is not None
            and now-self._last_alert_attempt < timedelta(minutes=2)
        ):
            return
        self._last_alert_attempt = now
        for key in self._watchdog.pending_incident_keys():
            try:
                self._watchdog.deliver(key, self._transport)
            except Exception:
                break

    def cycle(self, now: datetime) -> str:
        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise DemoSafetyError("service clock is not UTC")
        # The watchdog monitors the last successful main-loop heartbeat; it
        # cannot grant broker execution. A stale process halts rather than
        # silently resuming after unknown activity.
        if not self._watchdog.check_fresh(now=now):
            raise DemoSafetyError("watchdog stale or killed")
        outcome = self._coordinator.cycle(self._port, now=now)
        self._write_audit({
            "utc": now.astimezone(UTC).isoformat(),
            "state": outcome.state, "action": outcome.action,
            "reason": outcome.reason,
            "strategy_status": str(getattr(
                self._port, "last_reason", "NOT_AVAILABLE"
            ))[:120],
            "mode": "REAL_EXNESS_DEMO_SERVER_VIRTUAL_MONEY",
            "live_allowed": False,
        })
        if outcome.state != "ACTIVE":
            raise DemoSafetyError(f"coordinator quarantined: {outcome.reason}")
        self._watchdog.heartbeat(now=now)
        self._status({
            "utc": now.isoformat(), "state": outcome.state,
            "action": outcome.action, "reason": outcome.reason,
            "strategy_status": str(getattr(self._port, "last_reason", ""))[:120],
            "broker_mode": "EXNESS_DEMO_ONLY",
        }, now)
        self._alert_pending(now)
        if self._research is not None and now.minute == 1 and now.second < 10:
            # Daily research only; broker fills remain the source of truth.
            self._research.checkpoint(now)
        return outcome.action

    def serve(self) -> None:
        # Unlike the earlier sticky forever-lease, an OS lock is released by
        # the kernel after a crash. Durable PREPARING/UNCERTAIN order state
        # STILL prevents a duplicate retry when this process restarts.
        with one_os_process_lock(self._folder / "writer.lock"):
            if self._coordinator.status() != "ACTIVE":
                raise DemoSafetyError("coordinator not in ACTIVE state")
            if self._watchdog.status() != "ACTIVE":
                raise DemoSafetyError("watchdog not in ACTIVE state")
            while True:
                try:
                    self.cycle(datetime.now(UTC))
                except Exception as exc:
                    instant = datetime.now(UTC)
                    self._watchdog.queue_incident(
                        observed_utc=instant, code="CONTINUOUS_WORKER_HALTED",
                        explanation=type(exc).__name__,
                    )
                    self._alert_pending(instant)
                    raise
                time.sleep(self._poll)
