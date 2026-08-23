import ast
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from phase0.validation.vps_reliability.private_probe_oracle import verify_private_matrix


class Rec:
    def __init__(self, **values): self.values=values
    def _asdict(self): return self.values


class FakeAPI:
    connected=True; boot="2026-08-23T00:00:00Z"; build=6104
    @classmethod
    def initialize(cls): return True
    @classmethod
    def shutdown(cls): return True
    @classmethod
    def last_error(cls): return (0,"ok")
    @classmethod
    def version(cls): return (5,0,6104,"fixture")
    @classmethod
    def terminal_info(cls): return Rec(connected=cls.connected,tradeapi_disabled=True,build=cls.build)
    @classmethod
    def account_info(cls): return Rec(login="SYNTHETIC",server="private")
    @classmethod
    def symbol_info(cls,symbol): return Rec(trade_mode=4)
    @classmethod
    def symbol_info_tick(cls,symbol):
        from datetime import datetime, timezone
        return Rec(time_msc=int(datetime.now(timezone.utc).timestamp()*1000))


class PrivateProbeTests(unittest.TestCase):
    def _module(self):
        import sys
        directory=str(Path(__file__).resolve().parent)
        if directory not in sys.path: sys.path.insert(0,directory)
        import private_probe
        return private_probe

    def test_append_chain_and_full_matrix(self):
        probe=self._module()
        class StepClock:
            current=datetime.now(timezone.utc)+timedelta(seconds=1)
            @classmethod
            def now(cls,tz=None):
                value=cls.current
                cls.current+=timedelta(seconds=1)
                return value if tz is None else value.astimezone(tz)
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/"private"; output.mkdir()
            clock=output/"clock.txt"; clock.write_text("Source: fixture\n",encoding="utf-8")
            events=["BASELINE","DISCONNECT","RECONNECT","PYTHON_RESTART","MT5_RESTART","WINDOWS_RESTART","CLOCK_CHECK","BUILD_CHECK"]
            current_boot="2025-08-23T00:00:00Z"; current_mt5="2025-08-23T01:00:00Z"
            with patch.object(probe,"datetime",StepClock):
                for index,event in enumerate(events):
                    FakeAPI.connected=event!="DISCONNECT"
                    if event=="MT5_RESTART": current_mt5="2025-08-23T02:00:00Z"
                    if event=="WINDOWS_RESTART": current_boot="2026-01-24T00:00:00Z"; current_mt5="2026-01-24T00:05:00Z"
                    probe.append_probe(FakeAPI,output,event=event,scenario_id=f"S-{index}",os_boot_utc=current_boot,mt5_start_utc=current_mt5,
                                       w32tm_status_file=clock if event=="CLOCK_CHECK" else None,compatibility_sha256=None)
            records=[json.loads(line) for line in (output/"vps_probe_records.jsonl").read_text().splitlines()]
            result=verify_private_matrix(records)
            self.assertEqual("PASS",result["status"],result["reasons"])

    def test_chain_tamper_and_incomplete_matrix_fail_closed(self):
        probe=self._module()
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/"private"
            probe.append_probe(FakeAPI,output,event="BASELINE",scenario_id="B",os_boot_utc="2025-08-23T00:00:00Z",mt5_start_utc="2025-08-23T01:00:00Z",w32tm_status_file=None,compatibility_sha256=None)
            records=[json.loads(line) for line in (output/"vps_probe_records.jsonl").read_text().splitlines()]
            self.assertIn("REQUIRED_SCENARIOS_INCOMPLETE",verify_private_matrix(records)["reasons"])
            records[0]["terminal_build"]=9999
            self.assertIn("HASH_CHAIN_INVALID",verify_private_matrix(records)["reasons"])

    def test_duplicate_scenario_and_invalid_compatibility_digest_fail(self):
        probe=self._module()
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/"private"
            probe.append_probe(FakeAPI,output,event="BASELINE",scenario_id="B",os_boot_utc="2025-08-23T00:00:00Z",mt5_start_utc="2025-08-23T01:00:00Z",w32tm_status_file=None,compatibility_sha256=None)
            probe.append_probe(FakeAPI,output,event="BASELINE",scenario_id="B",os_boot_utc="2025-08-23T00:00:00Z",mt5_start_utc="2025-08-23T01:00:00Z",w32tm_status_file=None,compatibility_sha256=None)
            records=[json.loads(line) for line in (output/"vps_probe_records.jsonl").read_text().splitlines()]
            self.assertIn("SCENARIO_ID_INVALID_OR_DUPLICATE",verify_private_matrix(records)["reasons"])
            self.assertIn("EVENT_DUPLICATE_OR_INVALID", verify_private_matrix(records)["reasons"])
            with self.assertRaisesRegex(ValueError,"lowercase SHA-256"):
                probe.append_probe(FakeAPI,output,event="BUILD_CHECK",scenario_id="C",os_boot_utc="2025-08-23T00:00:00Z",mt5_start_utc="2025-08-23T01:00:00Z",w32tm_status_file=None,compatibility_sha256="BAD")

    def test_barrier_unknown_and_nonbaseline_first_fail_closed(self):
        probe=self._module()
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/"private"
            probe.append_probe(FakeAPI,output,event="RECONNECT",scenario_id="R",os_boot_utc="2025-08-23T00:00:00Z",mt5_start_utc="2025-08-23T01:00:00Z",w32tm_status_file=None,compatibility_sha256=None)
            records=[json.loads(line) for line in (output/"vps_probe_records.jsonl").read_text().splitlines()]
            records[0]["tradeapi_disabled"]=None
            unsigned={key:value for key,value in records[0].items() if key!="record_sha256"}
            import hashlib
            records[0]["record_sha256"]=hashlib.sha256(json.dumps(unsigned,sort_keys=True,separators=(",",":")).encode()).hexdigest()
            result=verify_private_matrix(records)
            self.assertIn("BASELINE_NOT_FIRST",result["reasons"])
            self.assertIn("EXTERNAL_PYTHON_TRADING_NOT_DISABLED",result["reasons"])

    def test_private_output_inside_repository_is_rejected(self):
        probe=self._module()
        with self.assertRaisesRegex(ValueError,"outside repository"):
            probe.private_target(Path(__file__).parent/"forbidden")

    def test_temporary_directories_are_platform_native(self):
        tree=ast.parse(Path(__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call): continue
            name=node.func.attr if isinstance(node.func,ast.Attribute) else node.func.id if isinstance(node.func,ast.Name) else ""
            if name!="TemporaryDirectory": continue
            hardcoded=[keyword.value.value for keyword in node.keywords
                       if keyword.arg=="dir" and isinstance(keyword.value,ast.Constant)]
            self.assertNotIn("/tmp",hardcoded)

    def test_adapter_and_probe_expose_no_order_or_process_control(self):
        directory=Path(__file__).resolve().parent
        forbidden_calls={"order_send","order_check","order_calc_margin","positions_get","orders_get","login","symbol_select","system","popen","run","Popen"}
        for name in ("readonly_mt5.py","private_probe.py"):
            tree=ast.parse((directory/name).read_text(encoding="utf-8")); calls=set()
            for node in ast.walk(tree):
                if isinstance(node,ast.Call): calls.add(node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else "")
            self.assertFalse(calls & forbidden_calls)
        adapter=(directory/"readonly_mt5.py").read_text(encoding="utf-8")
        for forbidden in ("order_send","order_check","order_calc_margin","login","symbol_select","positions_get","orders_get"):
            self.assertNotIn(forbidden,adapter)
        runner=(directory/"run_private_probe.ps1").read_text(encoding="utf-8")
        for forbidden in ("Restart-Computer","Stop-Process","Disable-NetAdapter","Enable-NetAdapter","taskkill"):
            self.assertNotIn(forbidden,runner)


if __name__=="__main__": unittest.main()
