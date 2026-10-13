from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from xauusd_agent.core import (
    AuditEventType,
    ConcurrentWriteError,
    IntegrityError,
    InternalEventType,
    LeaseError,
    TimeObservation,
    ValidationError,
)
from xauusd_agent.storage import (
    AuditJournal,
    InternalOutbox,
    WriterLease,
    create_database,
    open_database,
    verify_startup,
)
from xauusd_agent.storage.schema import initialize_schema


class FakeClock:
    def __init__(self) -> None:
        self.utc = datetime(2026, 10, 7, tzinfo=UTC)
        self.monotonic_ns = 1_000

    def observe(self) -> TimeObservation:
        result = TimeObservation(self.utc, self.monotonic_ns)
        self.monotonic_ns += 1
        return result

    def advance(self, value: timedelta) -> None:
        self.utc += value
        self.monotonic_ns += int(value.total_seconds() * 1_000_000_000)


class DurableStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "agent.sqlite3"
        self.clock = FakeClock()
        self.connection = create_database(self.path)

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary.cleanup()

    def _lease(self):
        return WriterLease(self.connection, self.clock).acquire(
            "runtime", "process-a", timedelta(seconds=10)
        )

    def test_empty_database_has_execution_disabled_identity(self) -> None:
        report = verify_startup(self.connection)
        self.assertEqual(report.journal_entries, 0)
        self.assertEqual(report.outbox_entries, 0)
        self.assertEqual(report.runtime_mode.value, "EXECUTION_DISABLED")
        self.assertEqual(report.execution_capability.value, "ABSENT")

    def test_journal_is_chained_immutable_and_survives_reopen(self) -> None:
        token = self._lease()
        journal = AuditJournal(self.connection, self.clock)
        first = journal.append(token, "runtime", AuditEventType.STARTUP, {"mode": "shadow"})
        second = journal.append(
            token,
            "runtime",
            AuditEventType.STATE_CHANGED,
            {"state": "READY_READ_ONLY"},
        )
        self.assertEqual(first.sequence, 1)
        self.assertEqual(second.previous_hash, first.entry_hash)
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("UPDATE audit_journal SET payload_json='{}' WHERE sequence=1")
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("DELETE FROM audit_journal WHERE sequence=1")

        self.connection.close()
        self.connection = open_database(self.path)
        report = verify_startup(self.connection)
        self.assertEqual(report.journal_entries, 2)

    def test_uncommitted_append_is_rolled_back_after_connection_loss(self) -> None:
        self._lease()
        self.connection.execute("BEGIN IMMEDIATE")
        self.connection.execute(
            """INSERT INTO audit_journal VALUES
               (1,'00000000-0000-0000-0000-000000000001','runtime','STARTUP',
                '2026-10-07T00:00:00.000000Z',1,'{}',x'00',
                '0000000000000000000000000000000000000000000000000000000000000000',
                '1111111111111111111111111111111111111111111111111111111111111111',1)"""
        )
        self.connection.close()  # Simulates process loss before COMMIT.
        self.connection = open_database(self.path)
        self.assertEqual(verify_startup(self.connection).journal_entries, 0)

    def test_offline_payload_tamper_fails_startup_even_if_trigger_is_restored(self) -> None:
        token = self._lease()
        AuditJournal(self.connection, self.clock).append(
            token, "runtime", AuditEventType.STARTUP, {"mode": "shadow"}
        )
        self.connection.execute("DROP TRIGGER audit_journal_no_update")
        self.connection.execute("UPDATE audit_journal SET payload_canonical=x'FF' WHERE sequence=1")
        initialize_schema(self.connection)  # Recreates the required trigger.
        with self.assertRaises(IntegrityError):
            verify_startup(self.connection)

    def test_expired_holder_is_fenced_after_takeover(self) -> None:
        lease = WriterLease(self.connection, self.clock)
        stale = lease.acquire("runtime", "process-a", timedelta(seconds=2))
        self.clock.advance(timedelta(seconds=3))
        current = lease.acquire("runtime", "process-b", timedelta(seconds=10))
        self.assertGreater(current.fencing_token, stale.fencing_token)
        with self.assertRaises(LeaseError):
            AuditJournal(self.connection, self.clock).append(
                stale, "runtime", AuditEventType.STARTUP, {"holder": "a"}
            )
        AuditJournal(self.connection, self.clock).append(
            current, "runtime", AuditEventType.STARTUP, {"holder": "b"}
        )

    def test_lease_renewal_invalidates_old_cas_version(self) -> None:
        lease = WriterLease(self.connection, self.clock)
        old = lease.acquire("runtime", "process-a", timedelta(seconds=10))
        renewed = lease.renew(old, timedelta(seconds=10))
        with self.assertRaises(LeaseError):
            lease.renew(old, timedelta(seconds=10))
        lease.release(renewed)

    def test_internal_outbox_reclaims_crashed_consumer_and_fences_old_claim(self) -> None:
        token = self._lease()
        outbox = InternalOutbox(self.connection, self.clock)
        pending = outbox.enqueue(token, InternalEventType.HEALTH_CHANGED, {"healthy": False})
        self.assertEqual(pending.status, "PENDING")
        abandoned = outbox.claim_next("consumer-a", timedelta(seconds=2))
        self.assertIsNotNone(abandoned)
        self.clock.advance(timedelta(seconds=3))
        recovered = outbox.claim_next("consumer-b", timedelta(seconds=10))
        self.assertIsNotNone(recovered)
        assert abandoned is not None and recovered is not None
        self.assertEqual(recovered.sequence, abandoned.sequence)
        self.assertEqual(recovered.attempts, 2)
        with self.assertRaises(ConcurrentWriteError):
            outbox.mark_delivered(abandoned)
        delivered = outbox.mark_delivered(recovered)
        self.assertEqual(delivered.status, "DELIVERED")
        self.assertEqual(verify_startup(self.connection).outbox_entries, 1)

    def test_outbox_rejects_open_text_event_types(self) -> None:
        token = self._lease()
        with self.assertRaises(ValidationError):
            InternalOutbox(self.connection, self.clock).enqueue(
                token,
                "ORDER_REQUESTED",  # type: ignore[arg-type]
                {"symbol": "XAUUSD"},
            )


if __name__ == "__main__":
    unittest.main()
