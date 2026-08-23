import hashlib
import ast
import json
import unittest
from datetime import datetime, timezone

from phase0.validation.session_evidence.session_oracle import (
    EvidenceError, scheduled_open, validate_schedule, verify_observations,
)


def schedule():
    return {
        "schema":"xauusd-account-session-schedule-1.0", "symbol":"XAUUSD",
        "timezone":"America/New_York",
        "source":{"authority":"BROKER_ACCOUNT_SPECIFICATION", "account_specific":True,
                  "url":"https://get.exness.help/hc/en-us/articles/4405235684498-Instrument-trading-hours", "raw_sha256":"a"*64,
                  "retrieved_utc":"2026-08-23T00:00:00Z"},
        "weekly_intervals":[
            {"weekday":6,"start":"18:00","end":"23:59"},
            *({"weekday":day,"start":"00:01","end":"23:59"} for day in range(0,4)),
            {"weekday":4,"start":"00:01","end":"17:00"},
        ],
        "holiday_source":{"url":"https://get.exness.help/hc/en-us/articles/17923046759836-Holiday-trading-hours","raw_sha256":"b"*64,"retrieved_utc":"2026-08-23T00:00:00Z"},
        "holiday_overrides":[{"date":"2026-12-25","closed":True,"intervals":[]}],
    }


def chain(rows):
    prior = "0"*64
    result=[]
    for supplied in rows:
        row={**supplied,"prior_record_sha256":prior}
        digest=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        row["record_sha256"]=digest
        result.append(row); prior=digest
    return result


class SessionEvidenceTests(unittest.TestCase):
    def test_authoritative_fresh_account_specific_schedule_required(self):
        validate_schedule(schedule(), now_utc=datetime(2026,8,23,tzinfo=timezone.utc))
        broken=schedule(); broken["source"]["account_specific"]=False
        with self.assertRaises(EvidenceError): validate_schedule(broken, now_utc=datetime(2026,8,23,tzinfo=timezone.utc))

    def test_dst_and_overnight_schedule(self):
        self.assertTrue(scheduled_open(schedule(), "2026-08-24T02:30:00Z"))
        self.assertFalse(scheduled_open(schedule(), "2026-08-22T02:30:00Z"))

    def test_holiday_override_closes(self):
        self.assertFalse(scheduled_open(schedule(), "2026-12-25T15:00:00Z"))

    def test_open_holiday_override_replaces_prior_overnight_weekly_interval(self):
        row=schedule()
        row["weekly_intervals"].append({"weekday":3,"start":"22:00","end":"04:00"})
        row["holiday_overrides"]=[{"date":"2026-12-25","closed":False,"intervals":[{"start":"08:00","end":"12:00"}]}]
        self.assertFalse(scheduled_open(row,"2026-12-25T06:00:00Z"))
        self.assertTrue(scheduled_open(row,"2026-12-25T15:00:00Z"))

    def test_complete_boundary_chain_passes(self):
        base={"boundary_id":"B1","tradeapi_disabled":True,"connected":True,"tick_age_seconds":1}
        rows=chain([
            {**base,"phase":"BEFORE","observed_utc":"2026-08-24T02:30:00Z"},
            {**base,"phase":"INSIDE","observed_utc":"2026-08-24T03:30:00Z"},
            {**base,"phase":"AFTER","observed_utc":"2026-08-24T04:30:00Z"},
        ])
        self.assertEqual("PASS", verify_observations(schedule(),rows)["status"])

    def test_mismatch_and_tamper_fail_closed(self):
        rows=chain([{"boundary_id":"B1","phase":"BEFORE","observed_utc":"2026-08-22T02:30:00Z","tradeapi_disabled":True,"connected":True,"tick_age_seconds":1}])
        self.assertIn("SCHEDULE_TICK_DISCREPANCY",verify_observations(schedule(),rows)["reasons"])
        rows[0]["connected"]=False
        self.assertIn("HASH_CHAIN_INVALID",verify_observations(schedule(),rows)["reasons"])

    def test_capture_adapter_has_no_order_login_selection_or_process_capability(self):
        directory=__import__("pathlib").Path(__file__).resolve().parent
        forbidden={"order_send","order_check","order_calc_margin","login","symbol_select","positions_get","orders_get","system","popen","Popen"}
        for name in ("readonly_mt5.py","capture_private_boundary.py"):
            tree=ast.parse((directory/name).read_text(encoding="utf-8")); calls=set()
            for node in ast.walk(tree):
                if isinstance(node,ast.Call): calls.add(node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else "")
            self.assertFalse(calls & forbidden)
        adapter=(directory/"readonly_mt5.py").read_text(encoding="utf-8")
        for item in forbidden: self.assertNotIn(item,adapter)
        runner=(directory/"run_private_boundary.ps1").read_text(encoding="utf-8")
        for item in ("order_send","order_check","Restart-Computer","Stop-Process","Send-MailMessage"):
            self.assertNotIn(item,runner)


if __name__ == "__main__": unittest.main()
