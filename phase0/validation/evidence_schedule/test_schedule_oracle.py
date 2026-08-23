from __future__ import annotations

import ast
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from schedule_oracle import (
    EVENT_SOURCES, CaptureTask, ScheduledEvent, SessionBoundary, build_schedule,
    schedule_hash, verify_transition_coverage,
)


UTC = timezone.utc


class EvidenceScheduleTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 9, 1, tzinfo=UTC)
        self.end = datetime(2026, 9, 4, tzinfo=UTC)
        self.event = ScheduledEvent(
            "BLS-CPI-202609", "BLS_ICS", datetime(2026, 9, 2, 12, 30, tzinfo=UTC),
        )
        self.boundary = SessionBoundary(
            "WEEKLY-20260904", datetime(2026, 9, 2, 22, tzinfo=UTC),
            datetime(2026, 9, 3, 1, tzinfo=UTC), False,
        )

    def test_complete_schedule_is_read_only_and_deterministic(self):
        result = build_schedule(self.start, self.end, (self.event,), (self.boundary,))
        self.assertEqual("PLANNED_READ_ONLY", result.status)
        self.assertEqual(schedule_hash(result.tasks), result.schedule_sha256)
        self.assertTrue(all(task.external_python_trading_disabled for task in result.tasks))
        self.assertFalse(any(task.deliberate_disruption or task.sends_message
                             or task.trading_action for task in result.tasks))

    def test_four_sources_have_adjacent_six_hour_transition_pairs(self):
        result = build_schedule(self.start, self.end, (), ())
        healthy, reasons = verify_transition_coverage(result.tasks)
        self.assertTrue(healthy, reasons)
        for source in EVENT_SOURCES:
            routine = [task for task in result.tasks
                       if task.target == source and task.phase == "ROUTINE_PAIRABLE"]
            self.assertEqual(12, len(routine))

    def test_event_dense_offsets_are_exact(self):
        result = build_schedule(self.start, self.end, (self.event,), ())
        rows = [task for task in result.tasks if task.task_id.startswith("EG-EVENT-")]
        self.assertEqual(
            {"T_MINUS_24H", "T_MINUS_6H", "T_MINUS_1H", "T_PLUS_15M", "T_PLUS_2H"},
            {task.phase for task in rows},
        )

    def test_session_boundary_has_before_inside_after(self):
        result = build_schedule(self.start, self.end, (), (self.boundary,))
        rows = [task for task in result.tasks if task.task_id.startswith("SESSION-MT5-")]
        self.assertEqual({"BEFORE", "INSIDE", "AFTER"}, {task.phase for task in rows})
        healthy, reasons = verify_transition_coverage(result.tasks)
        self.assertTrue(healthy, reasons)

    def test_holiday_boundary_adds_four_source_refresh_leads(self):
        start = self.start - timedelta(days=15)
        holiday = replace(self.boundary, holiday=True)
        result = build_schedule(start, self.end, (), (holiday,))
        rows = [task for task in result.tasks if task.task_id.startswith("SESSION-PRE-")]
        self.assertEqual(8, len(rows))

    def test_invalid_horizon_event_and_boundary_fail_closed(self):
        self.assertEqual("FAIL_CLOSED", build_schedule(
            self.end, self.start, (), ()).status)
        bad_event = replace(self.event, source="UNOFFICIAL")
        bad_boundary = replace(self.boundary, reopen_utc=self.boundary.close_utc)
        result = build_schedule(self.start, self.end, (bad_event,), (bad_boundary,))
        self.assertEqual("FAIL_CLOSED", result.status)
        self.assertEqual({"EVENT_INVALID", "BOUNDARY_INVALID"}, set(result.reason_codes))

    def test_transition_verifier_detects_missing_source_pair_and_boundary_phase(self):
        result = build_schedule(self.start, self.end, (), (self.boundary,))
        reduced = tuple(task for task in result.tasks
                        if not (task.target == "BLS_ICS" and task.phase == "ROUTINE_PAIRABLE")
                        and task.phase != "INSIDE")
        healthy, reasons = verify_transition_coverage(reduced)
        self.assertFalse(healthy)
        self.assertIn("BLS_ICS_NO_ADJACENT_TRANSITION_PAIR", reasons)
        self.assertIn("SESSION_BOUNDARY_PHASE_INCOMPLETE", reasons)

    def test_expected_inventory_cannot_pass_when_all_dense_tasks_are_absent(self):
        result = build_schedule(self.start, self.end, (), ())
        healthy, reasons = verify_transition_coverage(
            result.tasks, expected_boundary_ids=(self.boundary.boundary_id,),
            expected_event_ids=(self.event.event_id,),
        )
        self.assertFalse(healthy)
        self.assertIn(f"{self.boundary.boundary_id}_EXPECTED_BOUNDARY_INCOMPLETE", reasons)
        self.assertIn(f"{self.event.event_id}_EXPECTED_EVENT_INCOMPLETE", reasons)

    def test_expected_dense_event_and_boundary_inventory_passes_only_when_complete(self):
        result = build_schedule(self.start, self.end, (self.event,), (self.boundary,))
        healthy, reasons = verify_transition_coverage(
            result.tasks, expected_boundary_ids=(self.boundary.boundary_id,),
            expected_event_ids=(self.event.event_id,),
        )
        self.assertTrue(healthy, reasons)
        duplicate = result.tasks + (result.tasks[0],)
        self.assertIn("DUPLICATE_CAPTURE_TASK",
                      verify_transition_coverage(duplicate)[1])

    def test_capability_boundary_is_explicit(self):
        result = build_schedule(self.start, self.end, (), ())
        altered = list(result.tasks)
        altered[0] = replace(altered[0], deliberate_disruption=True)
        self.assertNotEqual(schedule_hash(result.tasks), schedule_hash(altered))

    def test_module_has_no_network_mt5_process_message_scheduler_or_write_capability(self):
        tree = ast.parse(Path(__file__).with_name("schedule_oracle.py").read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertTrue(imports.isdisjoint({
            "MetaTrader5", "requests", "urllib3", "socket", "subprocess", "openai",
            "pathlib", "os", "shutil", "schedule", "smtplib", "telegram",
        }))


if __name__ == "__main__":
    unittest.main(verbosity=2)
