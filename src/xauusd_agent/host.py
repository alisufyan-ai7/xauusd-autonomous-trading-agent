"""PCR-3 read-only host for continuous execution-disabled XAUUSD shadowing."""

from __future__ import annotations

import json
import os
import socket
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from xauusd_agent.analyst import AnalystDecision, AnalystVerdict
from xauusd_agent.broker.mt5_readonly import MT5ReadOnlyAdapter
from xauusd_agent.core.model import AuditEventType
from xauusd_agent.guards import EventGuardDecision, EventGuardState, GateDecision, GateState
from xauusd_agent.market import collect_snapshot
from xauusd_agent.market.admission import DEFAULT_ADMISSION_POLICY
from xauusd_agent.reconciliation import reconcile_exposure
from xauusd_agent.risk import ExposureKnowledge, PolicyAInput, evaluate_policy_a
from xauusd_agent.runtime import ShadowCycleInput, ShadowCycleResult, evaluate_shadow_cycle
from xauusd_agent.storage import (
    AuditJournal,
    LeaseToken,
    WriterLease,
    create_database,
    verify_startup,
)


class HostSafetyError(RuntimeError):
    """Raised when the host cannot preserve the execution-disabled boundary."""


@dataclass(frozen=True, slots=True)
class LiveCycle:
    decision_id: str
    result: ShadowCycleResult
    account_id_sha256: str
    position_count: int
    order_count: int
    bar_counts: dict[str, int]
    bid: str | None
    ask: str | None


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".next")
    temporary.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def broker_preflight(adapter: MT5ReadOnlyAdapter | None = None) -> dict[str, object]:
    """Verify live MT5 is connected, guarded, XAUUSD-readable, and exposure-free."""

    owns_adapter = adapter is None
    active = adapter or MT5ReadOnlyAdapter()
    if owns_adapter:
        active.initialize()
    try:
        payload = active.preflight()
        if payload["open_positions"] != 0 or payload["pending_orders"] != 0:
            raise HostSafetyError(
                "PCR-3 start requires zero broker positions and zero pending orders"
            )
        if payload["execution_enabled"] is not False or payload["broker_action_count"] != 0:
            raise HostSafetyError("broker preflight violated the execution-disabled boundary")
        if payload["trading_api_disabled"] is not True:
            raise HostSafetyError("MT5 external-Python trading protection is not enabled")
        return payload
    finally:
        if owns_adapter:
            active.close()


def evaluate_live_cycle(
    adapter: MT5ReadOnlyAdapter,
    *,
    decision_time: datetime,
) -> LiveCycle:
    """Collect one live read-only information set and terminate at null execution."""

    if decision_time.tzinfo is None or decision_time.utcoffset() is None:
        raise HostSafetyError("decision_time must be timezone-aware")
    decision_time = decision_time.astimezone(UTC)
    account = adapter.observe_account()
    symbol = adapter.observe_symbol_fingerprint("XAUUSD")
    positions = adapter.observe_positions()
    orders = adapter.observe_orders()
    reconciliation = reconcile_exposure((), positions, orders)
    snapshot = collect_snapshot(
        adapter,
        decision_time=decision_time,
        account_symbol_known=True,
        precision_known=symbol.point > 0,
        session_state_known=None,
    )

    exposure = (
        ExposureKnowledge.CONFIRMED_ZERO
        if not positions and not orders
        else ExposureKnowledge.CONFIRMED_NONZERO
    )
    risk = evaluate_policy_a(
        PolicyAInput(
            symbol="XAUUSD",
            requested_volume_lots=Decimal("0.01"),
            account_equity=account.equity,
            account_free_margin=account.free_margin,
            account_margin_used=account.margin_used,
            incremental_margin=None,
            current_adverse_cost=None,
            stressed_adverse_cost=None,
            exposure=exposure,
            fingerprint_matches=True,
            protective_stop_present=None,
        )
    )
    event_guard = EventGuardDecision(
        EventGuardState.UNKNOWN,
        ("EVENT_INVENTORY_NOT_ADMITTED_FOR_PCR3_SHADOW",),
    )
    market_gate = GateDecision(
        GateState.UNKNOWN,
        ("SESSION_AND_SHOCK_STATE_NOT_ADMITTED_FOR_PCR3_SHADOW",),
    )
    analyst = AnalystVerdict(
        AnalystDecision.NO_TRADE,
        False,
        ("ANALYST_TRANSPORT_DISABLED",),
    )
    decision_id = str(uuid.uuid4())
    result = evaluate_shadow_cycle(
        ShadowCycleInput(
            decision_id=decision_id,
            observed_at=decision_time,
            market=snapshot,
            event_guard=event_guard,
            market_gates=(market_gate,),
            reconciliation=reconciliation,
            risk=risk,
            analyst=analyst,
            setup_id=None,
            admission_policy=DEFAULT_ADMISSION_POLICY,
        )
    )
    if result.broker_action_count != 0 or result.execution_capability.value != "ABSENT":
        raise HostSafetyError("shadow cycle violated the null-execution boundary")

    quote = snapshot.quote
    return LiveCycle(
        decision_id=decision_id,
        result=result,
        account_id_sha256=account.fingerprint.account_id_sha256,
        position_count=len(positions),
        order_count=len(orders),
        bar_counts={timeframe.value: len(rows) for timeframe, rows in snapshot.bars.items()},
        bid=None if quote is None else str(quote.bid),
        ask=None if quote is None else str(quote.ask),
    )


def _append_cycle(journal: AuditJournal, token: LeaseToken, cycle: LiveCycle) -> None:
    journal.append(
        token,
        "pcr3-shadow",
        AuditEventType.INPUT_OBSERVED,
        {
            "decision_id": cycle.decision_id,
            "account_id_sha256": cycle.account_id_sha256,
            "position_count": cycle.position_count,
            "order_count": cycle.order_count,
            "bar_counts": cycle.bar_counts,
            "bid": cycle.bid,
            "ask": cycle.ask,
            "execution_enabled": False,
            "broker_action_count": 0,
        },
    )
    journal.append(
        token,
        "pcr3-shadow",
        AuditEventType.RECONCILIATION_RECORDED,
        {
            "decision_id": cycle.decision_id,
            "position_count": cycle.position_count,
            "order_count": cycle.order_count,
            "quarantined_for_exposure": bool(cycle.position_count or cycle.order_count),
            "automatic_close_permitted": False,
        },
    )
    journal.append(
        token,
        "pcr3-shadow",
        AuditEventType.DECISION_RECORDED,
        {
            "decision_id": cycle.decision_id,
            "state": cycle.result.state.value,
            "decision": cycle.result.decision.value,
            "reason_codes": list(cycle.result.reason_codes),
            "state_hash": cycle.result.state_hash,
            "execution_capability": cycle.result.execution_capability.value,
            "broker_action_count": cycle.result.broker_action_count,
        },
    )


def run_shadow_host(
    state_directory: Path,
    *,
    interval_seconds: int = 15,
    once: bool = False,
    adapter: MT5ReadOnlyAdapter | None = None,
) -> int:
    """Run the execution-disabled live host; all broker observations are read-only."""

    if interval_seconds < 5:
        raise HostSafetyError("interval_seconds must be at least 5")
    state_directory = state_directory.resolve()
    state_directory.mkdir(parents=True, exist_ok=True)
    database_path = state_directory / "state.sqlite3"
    heartbeat_path = state_directory / "heartbeat.json"
    connection = create_database(database_path)
    verify_startup(connection)

    active = adapter or MT5ReadOnlyAdapter()
    owns_adapter = adapter is None
    token: LeaseToken | None = None
    lease = WriterLease(connection)
    journal = AuditJournal(connection)
    ttl = timedelta(seconds=max(60, interval_seconds * 4))
    holder = f"{socket.gethostname()}-{os.getpid()}".replace("_", "-")[:120]
    try:
        if owns_adapter:
            active.initialize()
        preflight = broker_preflight(active)
        token = lease.acquire("pcr3-shadow", holder, ttl)
        journal.append(
            token,
            "pcr3-shadow",
            AuditEventType.STARTUP,
            {
                "mode": "SHADOW",
                "execution_enabled": False,
                "broker_action_count": 0,
                "analyst_transport": "DISABLED",
                "alert_delivery": "DISABLED",
                "broker_preflight": preflight,
            },
        )

        while True:
            token = lease.renew(token, ttl)
            now = datetime.now(UTC)
            try:
                cycle = evaluate_live_cycle(active, decision_time=now)
                _append_cycle(journal, token, cycle)
                _write_json_atomic(
                    heartbeat_path,
                    {
                        "observed_at": _utc_text(now),
                        "decision_id": cycle.decision_id,
                        "runtime_state": cycle.result.state.value,
                        "decision": cycle.result.decision.value,
                        "reason_codes": list(cycle.result.reason_codes),
                        "execution_enabled": False,
                        "execution_capability": "ABSENT",
                        "broker_action_count": 0,
                        "open_positions": cycle.position_count,
                        "pending_orders": cycle.order_count,
                    },
                )
            except Exception as exc:
                journal.append(
                    token,
                    "pcr3-shadow",
                    AuditEventType.FAULT_RECORDED,
                    {
                        "fault": type(exc).__name__,
                        "detail": str(exc),
                        "execution_enabled": False,
                        "broker_action_count": 0,
                    },
                )
                _write_json_atomic(
                    heartbeat_path,
                    {
                        "observed_at": _utc_text(now),
                        "runtime_state": "QUARANTINED",
                        "fault": type(exc).__name__,
                        "execution_enabled": False,
                        "execution_capability": "ABSENT",
                        "broker_action_count": 0,
                    },
                )
                raise
            if once:
                return 0
            time.sleep(interval_seconds)
    finally:
        if token is not None:
            try:
                journal.append(
                    token,
                    "pcr3-shadow",
                    AuditEventType.SHUTDOWN,
                    {"execution_enabled": False, "broker_action_count": 0},
                )
                lease.release(token)
            except Exception:  # noqa: S110 -- shutdown is best-effort after primary work
                pass
        if owns_adapter:
            active.close()
        connection.close()
