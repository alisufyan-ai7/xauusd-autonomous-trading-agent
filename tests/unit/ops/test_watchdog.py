from datetime import UTC, datetime, timedelta

from xauusd_agent.ops.watchdog import (
    SupervisorAction,
    SupervisorConfig,
    SupervisorState,
    WatchdogSupervisor,
)


def test_stale_heartbeat_requests_bounded_restart_then_quarantines():
    config = SupervisorConfig(timedelta(seconds=1), timedelta(seconds=2), timedelta(minutes=5), 1)
    watchdog = WatchdogSupervisor(config)
    now = datetime.now(UTC)
    assert watchdog.observe(now=now, last_heartbeat=None).state is SupervisorState.DEGRADED
    first = watchdog.observe(now=now + timedelta(seconds=3), last_heartbeat=None)
    assert first.action is SupervisorAction.REQUEST_RESTART
    second = watchdog.observe(now=now + timedelta(seconds=6), last_heartbeat=None)
    assert second.action is SupervisorAction.ENTER_QUARANTINE
    assert second.state is SupervisorState.QUARANTINED


def test_fatal_condition_quarantines_without_restart():
    result = WatchdogSupervisor().observe(now=datetime.now(UTC), last_heartbeat=None, fatal=True)
    assert result.action is SupervisorAction.ENTER_QUARANTINE


def test_future_heartbeat_quarantines_clock_anomaly():
    now = datetime.now(UTC)
    result = WatchdogSupervisor().observe(now=now, last_heartbeat=now + timedelta(seconds=1))
    assert result.action is SupervisorAction.ENTER_QUARANTINE
    assert result.code == "HEARTBEAT_FROM_FUTURE"
