from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from xauusd_agent.analyst import (
    AnalystClient,
    AnalystDecision,
    AnalystRequest,
    FakeAnalystTransport,
)
from xauusd_agent.config import ConfigurationError, RuntimeConfig
from xauusd_agent.core import AuditEventType, IntegrityError, TimeObservation
from xauusd_agent.features.setups import SetupLifecycle, SetupState, transition
from xauusd_agent.guards.event_guard import (
    EventGuardState,
    EventObservation,
    evaluate_event_guard,
)
from xauusd_agent.guards.market_gates import (
    GateState,
    SessionObservation,
    evaluate_session_gate,
)
from xauusd_agent.market import (
    AdmissionPolicy,
    AdmissionState,
    Bar,
    MarketSnapshot,
    Quote,
    Timeframe,
    admit_market_snapshot,
)
from xauusd_agent.ops.release import build_manifest, scan_capabilities
from xauusd_agent.ops.watchdog import SupervisorAction, SupervisorConfig, WatchdogSupervisor
from xauusd_agent.reconciliation.exposure import (
    ReconciliationDisposition,
    ReconciliationStatus,
    reconcile_exposure,
)
from xauusd_agent.reconciliation.uncertainty import (
    SubmissionUncertainty,
    UncertaintyResolution,
    UncertaintyState,
)
from xauusd_agent.risk.policy_a import (
    ExposureKnowledge,
    PolicyAInput,
    RiskDisposition,
    evaluate_policy_a,
)
from xauusd_agent.storage import AuditJournal, WriterLease, create_database, verify_startup
from xauusd_agent.storage.schema import initialize_schema

NOW = datetime(2026, 10, 8, 0, 0, tzinfo=UTC)
HASH = "a" * 64


class _Clock:
    def __init__(self) -> None:
        self.monotonic_ns = 1

    def observe(self) -> TimeObservation:
        result = TimeObservation(NOW, self.monotonic_ns)
        self.monotonic_ns += 1
        return result


def _bar(timeframe: Timeframe) -> Bar:
    return Bar(
        "XAUUSD",
        timeframe,
        NOW - timeframe.duration,
        Decimal("2700"),
        Decimal("2701"),
        Decimal("2699"),
        Decimal("2700.5"),
        10,
    )


def test_g2_state_rejects_duplicate_out_of_order_and_terminal_reactivation() -> None:
    """G2-STATE-REGISTERED."""
    proposed = transition(SetupLifecycle("s1"), "PROPOSE", NOW)
    cancelled = transition(proposed, "EVENT_LOCK", NOW + timedelta(seconds=1))
    assert cancelled.state is SetupState.CANCELLED
    with pytest.raises(ValueError, match="terminal lifecycle cannot reactivate"):
        transition(cancelled, "PROPOSE", NOW + timedelta(seconds=2))
    with pytest.raises(ValueError, match="event time must increase"):
        transition(proposed, "RESERVE", NOW)


def test_g2_submit_uncertainty_never_retries_or_duplicates() -> None:
    """G2-SUBMIT-REGISTERED."""
    uncertain = SubmissionUncertainty("i1", "2026-10-08T00:00:00Z", "timeout-after-send")
    assert uncertain.retry_permitted is False
    terminal = uncertain.reconcile(UncertaintyResolution.OBSERVATION_INCONCLUSIVE)
    assert terminal.state is UncertaintyState.HUMAN_ESCALATION
    assert terminal.retry_permitted is False
    with pytest.raises(ValueError, match="already terminal"):
        terminal.reconcile(UncertaintyResolution.BROKER_ABSENT)


def test_g2_store_tamper_and_missing_immutability_trigger_fail_startup(tmp_path) -> None:
    """G2-STORE-REGISTERED."""
    connection = create_database(tmp_path / "fault.sqlite3")
    clock = _Clock()
    token = WriterLease(connection, clock).acquire("runtime", "p1", timedelta(seconds=10))
    AuditJournal(connection, clock).append(
        token, "runtime", AuditEventType.STARTUP, {"mode": "shadow"}
    )
    connection.execute("DROP TRIGGER audit_journal_no_update")
    connection.execute("UPDATE audit_journal SET payload_canonical=x'FF' WHERE sequence=1")
    initialize_schema(connection)
    with pytest.raises(IntegrityError):
        verify_startup(connection)
    connection.close()


def test_g2_identity_drift_and_unknown_exposure_quarantine(tmp_path) -> None:
    """G2-IDENTITY-REGISTERED."""
    with pytest.raises(ConfigurationError):
        RuntimeConfig(state_directory=tmp_path, symbol="EURUSD")
    reconciliation = reconcile_exposure((), None, None)
    assert reconciliation.status is ReconciliationStatus.UNKNOWN_EXPOSURE
    assert reconciliation.disposition is ReconciliationDisposition.QUARANTINE_HUMAN_REVIEW
    assert reconciliation.automatic_close_permitted is False


def test_g2_time_future_heartbeat_quarantines_without_restart() -> None:
    """G2-TIME-REGISTERED."""
    result = WatchdogSupervisor().observe(
        now=NOW,
        last_heartbeat=NOW + timedelta(seconds=1),
    )
    assert result.action is SupervisorAction.ENTER_QUARANTINE
    assert result.code == "HEARTBEAT_FROM_FUTURE"


def test_g2_data_forming_bar_and_stale_quote_are_locked() -> None:
    """G2-DATA-REGISTERED."""
    quote = Quote(
        "XAUUSD",
        NOW - timedelta(seconds=10),
        NOW - timedelta(seconds=10),
        Decimal("2700"),
        Decimal("2700.1"),
        Decimal("0.1"),
        1,
    )
    forming = _bar(Timeframe.M15)
    forming = forming.__class__(
        forming.symbol,
        forming.timeframe,
        NOW,
        forming.open,
        forming.high,
        forming.low,
        forming.close,
        forming.tick_volume,
    )
    snapshot = MarketSnapshot(
        NOW,
        quote,
        {
            Timeframe.H4: (_bar(Timeframe.H4),),
            Timeframe.H1: (_bar(Timeframe.H1),),
            Timeframe.M15: (forming,),
        },
        {},
        True,
        True,
        True,
    )
    decision = admit_market_snapshot(
        snapshot,
        AdmissionPolicy(minima={Timeframe.H4: 1, Timeframe.H1: 1, Timeframe.M15: 1}),
    )
    assert decision.state is AdmissionState.LOCK
    assert "QUOTE_STALE" in decision.reasons
    assert "M15_FORMING_BAR_PRESENT" in decision.reasons


def test_g2_risk_unknown_exposure_and_over_cap_never_allow() -> None:
    """G2-RISK-REGISTERED."""
    base = dict(
        symbol="XAUUSD",
        requested_volume_lots=Decimal("0.02"),
        account_equity=Decimal("10000"),
        account_free_margin=Decimal("10000"),
        account_margin_used=Decimal("0"),
        incremental_margin=Decimal("100"),
        current_adverse_cost=Decimal("5"),
        stressed_adverse_cost=Decimal("10"),
        exposure=ExposureKnowledge.UNKNOWN,
        fingerprint_matches=True,
        protective_stop_present=True,
    )
    unknown = evaluate_policy_a(PolicyAInput(**base))
    assert unknown.disposition is RiskDisposition.QUARANTINE
    base["exposure"] = ExposureKnowledge.CONFIRMED_ZERO
    over_cap = evaluate_policy_a(PolicyAInput(**base))
    assert over_cap.disposition is RiskDisposition.REJECT
    assert over_cap.allowed is False


def test_g2_guard_unknown_session_and_source_conflict_stay_locked() -> None:
    """G2-GUARD-REGISTERED."""
    session = evaluate_session_gate(
        SessionObservation(NOW, True, True, None, True, True, 3600, 60)
    )
    assert session.state is GateState.UNKNOWN
    event = evaluate_event_guard(EventObservation(NOW, (), True, False, True, False, True))
    assert event.state is EventGuardState.SOURCE_UNHEALTHY
    assert event.entry_allowed is False


def test_g2_analyst_extra_key_and_disabled_transport_reject_without_authority() -> None:
    """G2-ANALYST-REGISTERED."""
    request = AnalystRequest(
        "r1", NOW, NOW + timedelta(seconds=10), "XAUUSD", HASH, HASH, HASH, {"rsi": 42}
    )
    payload = (
        '{"schema_version":"analyst-response-v1","request_id":"r1","state_hash":"'
        + HASH
        + '","decision":"SETUP","reason_codes":["OK"],"extra":true}'
    )
    rejected = AnalystClient(FakeAnalystTransport(payload)).evaluate(request, now=NOW)
    assert rejected.decision is AnalystDecision.NO_TRADE
    assert rejected.admissible is False
    disabled = AnalystClient().evaluate(request, now=NOW)
    assert disabled.decision is AnalystDecision.NO_TRADE
    assert disabled.admissible is False


def test_g2_service_restart_budget_exhaustion_latches_quarantine() -> None:
    """G2-SERVICE-REGISTERED."""
    supervisor = WatchdogSupervisor(
        SupervisorConfig(timedelta(seconds=1), timedelta(seconds=1), timedelta(minutes=5), 1)
    )
    supervisor.observe(now=NOW, last_heartbeat=None)
    first = supervisor.observe(now=NOW + timedelta(seconds=2), last_heartbeat=None)
    assert first.action is SupervisorAction.REQUEST_RESTART
    final = supervisor.observe(now=NOW + timedelta(seconds=4), last_heartbeat=None)
    assert final.action is SupervisorAction.ENTER_QUARANTINE
    latched = supervisor.observe(now=NOW + timedelta(seconds=5), last_heartbeat=NOW)
    assert latched.code == "QUARANTINE_LATCHED"
    assert latched.action is SupervisorAction.NONE


def test_g2_evidence_forbidden_capability_and_post_manifest_tamper_fail_closed(
    tmp_path,
) -> None:
    """G2-EVIDENCE-REGISTERED."""
    unsafe = tmp_path / "unsafe.py"
    unsafe.write_text("client.order" + "_send(request)\n", encoding="utf-8")
    assert scan_capabilities(tmp_path)
    unsafe.unlink()
    safe = tmp_path / "safe.py"
    safe.write_text("VALUE = 1\n", encoding="utf-8")
    manifest = build_manifest(tmp_path, release_id="fault-seal", created_at=NOW)
    safe.write_text("VALUE = 2\n", encoding="utf-8")
    observed = hashlib.sha256(safe.read_bytes()).hexdigest()
    assert observed != manifest.files[0].sha256
