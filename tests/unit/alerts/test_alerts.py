from datetime import UTC, datetime

from xauusd_agent.alerts import AlertEvent, AlertSeverity, AuditOnlyAlertSink


def test_audit_sink_records_without_delivery():
    sink = AuditOnlyAlertSink()
    event = AlertEvent(
        "e1",
        datetime.now(UTC),
        AlertSeverity.CRITICAL,
        "QUARANTINE",
        "candidate quarantined",
        "c1",
    )
    receipt = sink.emit(event)
    assert receipt.delivered is False
    assert receipt.status == "RECORDED_NOT_DELIVERED"
    assert sink.snapshot() == (event,)
