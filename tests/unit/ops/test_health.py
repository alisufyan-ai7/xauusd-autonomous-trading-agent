from datetime import UTC, datetime

import pytest

from xauusd_agent.ops.health import ComponentHealth, HealthRecord, HealthStatus, aggregate_health
from xauusd_agent.ops.monitoring import build_monitoring_snapshot
from xauusd_agent.ops.watchdog import SupervisorState


def test_aggregate_uses_worst_component_and_execution_is_off():
    now = datetime.now(UTC)
    record = aggregate_health(
        (
            ComponentHealth("ingestion", HealthStatus.HEALTHY, now, "OK"),
            ComponentHealth("journal", HealthStatus.DEGRADED, now, "SLOW"),
        ),
        observed_at=now,
    )
    assert record.status is HealthStatus.DEGRADED
    assert record.execution_enabled is False
    assert record.broker_action_count == 0


def test_nonzero_actions_are_rejected():
    with pytest.raises(ValueError):
        HealthRecord(HealthStatus.HEALTHY, datetime.now(UTC), (), broker_action_count=1)


def test_monitoring_projection_keeps_execution_barrier_visible():
    now = datetime.now(UTC)
    record = aggregate_health(
        (ComponentHealth("analyst", HealthStatus.DEGRADED, now, "TRANSPORT_DISABLED"),),
        observed_at=now,
    )
    snapshot = build_monitoring_snapshot(record, supervisor_state=SupervisorState.DEGRADED)
    assert snapshot.execution_enabled is False
    assert snapshot.broker_action_count == 0
    assert '"execution_enabled":false' in snapshot.to_json()
