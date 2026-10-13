"""Safe monitoring projection for the execution-disabled candidate."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .health import HealthRecord
from .watchdog import SupervisorState


@dataclass(frozen=True, slots=True)
class MonitoringSnapshot:
    observed_at: str
    overall_status: str
    supervisor_state: str
    execution_enabled: bool
    broker_action_count: int
    component_codes: tuple[str, ...]

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))


def build_monitoring_snapshot(
    health: HealthRecord, *, supervisor_state: SupervisorState
) -> MonitoringSnapshot:
    if health.execution_enabled or health.broker_action_count != 0:
        raise ValueError("monitoring refuses an execution-capable health record")
    return MonitoringSnapshot(
        observed_at=health.observed_at.isoformat().replace("+00:00", "Z"),
        overall_status=health.status.value,
        supervisor_state=supervisor_state.value,
        execution_enabled=False,
        broker_action_count=0,
        component_codes=tuple(f"{item.component}:{item.code}" for item in health.components),
    )
