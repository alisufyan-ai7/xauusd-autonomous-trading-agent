# ruff: noqa: I001
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from xauusd_demo.envelope import DemoSafetyError
from xauusd_demo.ops_safety_watchdog import PersistentDemoSafetyWatchdog

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)


class FakeTwoChannelAlerts:
    def __init__(self):
        self.emails = []
        self.telegrams = []
        self.fail_telegram = False

    def send_email(self, key, message):
        self.emails.append((key, message))

    def send_telegram(self, key, message):
        if self.fail_telegram:
            raise ConnectionError("synthetic Telegram failure")
        self.telegrams.append((key, message))


def test_killed_by_default_and_requires_exact_human_p1(tmp_path: Path):
    with PersistentDemoSafetyWatchdog(tmp_path / "watch.sqlite") as w:
        assert w.status() == "KILLED"
        assert not w.check_fresh(now=NOW)
        with pytest.raises(DemoSafetyError, match="P1"):
            w.arm_attended(now=NOW, operator_token="activate")
        w.arm_attended(now=NOW, operator_token="P1-ARM-DEMO-WATCHDOG")
        assert w.check_fresh(now=NOW + timedelta(seconds=3))


def test_durable_stale_watchdog_quarantine_requires_manual_restart(tmp_path: Path):
    path = tmp_path / "stale.sqlite"
    with PersistentDemoSafetyWatchdog(path) as w:
        w.arm_attended(now=NOW, operator_token="P1-ARM-DEMO-WATCHDOG")
        w.heartbeat(now=NOW + timedelta(seconds=5))
        assert not w.check_fresh(now=NOW + timedelta(minutes=1))
        assert w.status() == "QUARANTINED"
        assert w.undelivered_count() == 1
    with PersistentDemoSafetyWatchdog(path) as w:
        assert w.status() == "QUARANTINED"
        with pytest.raises(DemoSafetyError, match="P1"):
            w.arm_attended(now=NOW + timedelta(minutes=2),
                           operator_token="P1-ARM-DEMO-WATCHDOG")


def test_rollback_latches_and_incident_persists(tmp_path: Path):
    with PersistentDemoSafetyWatchdog(tmp_path / "rollback.sqlite") as w:
        w.arm_attended(now=NOW, operator_token="P1-ARM-DEMO-WATCHDOG")
        with pytest.raises(DemoSafetyError, match="stale"):
            w.heartbeat(now=NOW - timedelta(seconds=1))
        assert w.status() == "QUARANTINED"
        assert w.undelivered_count() == 1


def test_alert_email_then_telegram_partial_failure_is_durable(tmp_path: Path):
    path = tmp_path / "alert.sqlite"
    sender = FakeTwoChannelAlerts()
    sender.fail_telegram = True
    with PersistentDemoSafetyWatchdog(path) as w:
        key = w.queue_incident(
            observed_utc=NOW, code="BROKER_UNKNOWN",
            explanation="known-position reconciliation unavailable",
        )
        with pytest.raises(ConnectionError):
            w.deliver(key, sender)
        assert w.undelivered_count() == 1
        assert len(sender.emails) == 1
        assert sender.telegrams == []
    sender.fail_telegram = False
    with PersistentDemoSafetyWatchdog(path) as w:
        ack = w.deliver(key, sender)
        assert ack.delivered_both
        assert len(sender.emails) == 1
        assert len(sender.telegrams) == 1
        assert w.undelivered_count() == 0
        w.deliver(key, sender)
        assert len(sender.emails) == 1 and len(sender.telegrams) == 1


def test_e1_kill_does_not_close_positions_or_send_orders(tmp_path: Path):
    transport = FakeTwoChannelAlerts()
    with PersistentDemoSafetyWatchdog(tmp_path / "kill.sqlite") as w:
        w.arm_attended(now=NOW, operator_token="P1-ARM-DEMO-WATCHDOG")
        w.kill(now=NOW, reason="manual E1 operator control")
        assert w.status() == "KILLED"
        assert not w.check_fresh(now=NOW)
        assert w.undelivered_count() == 1
        row = w.conn.execute(
            "SELECT incident_key FROM incident_outbox"
        ).fetchone()
        assert row is not None
        w.deliver(row[0], transport)
        assert len(transport.emails) == len(transport.telegrams) == 1
        assert not hasattr(w, "order_send")
        assert not hasattr(w, "close_position")


@pytest.mark.parametrize("reason", ["", "x" * 301, "bad\ntext"])
def test_unbounded_or_invalid_alert_rejected(tmp_path: Path, reason: str):
    with PersistentDemoSafetyWatchdog(tmp_path / "invalid.sqlite") as w:
        with pytest.raises(DemoSafetyError):
            w.queue_incident(
                observed_utc=NOW, code="INVALID", explanation=reason
            )
