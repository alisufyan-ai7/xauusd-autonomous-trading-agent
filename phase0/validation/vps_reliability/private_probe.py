"""Append a private read-only VPS/MT5 observation; never causes a fault."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVENTS={"BASELINE","DISCONNECT","RECONNECT","PYTHON_RESTART","MT5_RESTART","WINDOWS_RESTART","CLOCK_CHECK","BUILD_CHECK"}
SHA256=set("0123456789abcdef")


def plain(value: Any) -> Any:
    if value is None or isinstance(value,(str,int,float,bool)): return value
    if hasattr(value,"_asdict"): return {str(k):plain(v) for k,v in value._asdict().items()}
    return str(value)


def private_target(path: Path) -> Path:
    target=path.resolve(); repo=Path(__file__).resolve().parents[3]
    if target==repo or repo in target.parents: raise ValueError("private output must be outside repository")
    return target


def validate_chain(path: Path) -> tuple[int,str]:
    prior="0"*64; sequence=0
    if not path.exists(): return sequence,prior
    for line in path.read_text(encoding="utf-8").splitlines():
        row=json.loads(line)
        recorded=row.pop("record_sha256",None)
        encoded=json.dumps(row,sort_keys=True,separators=(",",":")).encode()
        actual=hashlib.sha256(encoded).hexdigest()
        if row.get("prior_record_sha256")!=prior or recorded!=actual or row.get("sequence")!=sequence:
            raise ValueError("existing observation chain invalid")
        prior=actual; sequence+=1
    return sequence,prior


def append_probe(api: Any, output: Path, *, event: str, scenario_id: str, os_boot_utc: str,
                 mt5_start_utc: str, w32tm_status_file: Path | None,
                 compatibility_sha256: str | None) -> dict[str,Any]:
    if event not in EVENTS or not scenario_id: raise ValueError("invalid event or scenario id")
    if compatibility_sha256 is not None and (len(compatibility_sha256)!=64 or set(compatibility_sha256)-SHA256):
        raise ValueError("compatibility digest must be lowercase SHA-256")
    output=private_target(output); output.mkdir(parents=True,exist_ok=True)
    key_path=output/"PRIVATE_HMAC_KEY.bin"
    if not key_path.exists():
        key_path.write_bytes(secrets.token_bytes(32))
    key=key_path.read_bytes()
    if len(key)!=32: raise ValueError("invalid private HMAC key")
    records=output/"vps_probe_records.jsonl"
    sequence,prior=validate_chain(records)
    process_token=hmac.new(key,f"process:{uuid.uuid4()}".encode(),hashlib.sha256).hexdigest()
    attached=api.initialize()
    terminal=account=symbol=tick=terminal_version=None
    try:
        if attached:
            terminal=plain(api.terminal_info()); account=plain(api.account_info())
            symbol=plain(api.symbol_info("XAUUSD")); tick=plain(api.symbol_info_tick("XAUUSD"))
            terminal_version=plain(api.version())
    finally:
        if attached: api.shutdown()
    observed=datetime.now(timezone.utc)
    tick_age=None
    if isinstance(tick,dict) and isinstance(tick.get("time_msc"),(int,float)):
        tick_age=round(observed.timestamp()-tick["time_msc"]/1000,3)
    identity_source="|".join(str(v) for v in ((account or {}).get("login"),(account or {}).get("server"),"XAUUSD"))
    identity=hmac.new(key,identity_source.encode(),hashlib.sha256).hexdigest() if isinstance(account,dict) else None
    w32_hash=None
    if w32tm_status_file is not None:
        status_path=w32tm_status_file.resolve()
        if not status_path.is_file() or output not in status_path.parents: raise ValueError("clock evidence must be inside private output")
        w32_hash=hashlib.sha256(status_path.read_bytes()).hexdigest()
    record={"schema":"gate0-vps-private-probe-1.0","sequence":sequence,"prior_record_sha256":prior,
            "event":event,"scenario_id":scenario_id,"observed_utc":observed.isoformat().replace("+00:00","Z"),
            "os_boot_utc":os_boot_utc,"mt5_start_utc":mt5_start_utc,
            "process_token":process_token,"attached":attached,
            "connected":terminal.get("connected") if isinstance(terminal,dict) else None,
            "tradeapi_disabled":terminal.get("tradeapi_disabled") if isinstance(terminal,dict) else None,
            "terminal_build":terminal.get("build") if isinstance(terminal,dict) else None,
            "terminal_version":terminal_version,"identity_token":identity,
            "symbol_trade_mode":symbol.get("trade_mode") if isinstance(symbol,dict) else None,
            "tick_age_seconds":tick_age,"w32tm_status_sha256":w32_hash,
            "compatibility_artifact_sha256":compatibility_sha256,
            "claim_limit":"Read-only private fault observation; not trading authorization."}
    encoded=json.dumps(record,sort_keys=True,separators=(",",":")).encode(); digest=hashlib.sha256(encoded).hexdigest()
    record["record_sha256"]=digest
    with records.open("a",encoding="utf-8",newline="\n") as handle:
        handle.write(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n"); handle.flush(); os.fsync(handle.fileno())
    return {"status":"CAPTURED","event":event,"sequence":sequence,"record_sha256":digest,
            "connected":record["connected"],"tradeapi_disabled":record["tradeapi_disabled"]}


def main() -> int:
    from readonly_mt5 import ReadOnlyMT5
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--event",choices=sorted(EVENTS),required=True); parser.add_argument("--scenario-id",required=True)
    parser.add_argument("--os-boot-utc",required=True); parser.add_argument("--mt5-start-utc",required=True)
    parser.add_argument("--w32tm-status-file",type=Path)
    parser.add_argument("--compatibility-sha256")
    args=parser.parse_args()
    try:
        print(json.dumps(append_probe(ReadOnlyMT5,args.output,event=args.event,scenario_id=args.scenario_id,
              os_boot_utc=args.os_boot_utc,mt5_start_utc=args.mt5_start_utc,w32tm_status_file=args.w32tm_status_file,
              compatibility_sha256=args.compatibility_sha256),sort_keys=True)); return 0
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print(f"FAIL CLOSED: {exc}",file=sys.stderr); return 2


if __name__=="__main__": raise SystemExit(main())
