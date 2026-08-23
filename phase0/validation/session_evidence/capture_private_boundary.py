"""Append one read-only observation to a private session-boundary chain."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from readonly_mt5 import ReadOnlyMT5


def plain(value: Any) -> Any:
    if value is None or isinstance(value,(str,int,float,bool)): return value
    if hasattr(value,"_asdict"): return {str(k):plain(v) for k,v in value._asdict().items()}
    return str(value)


def private_target(path: Path) -> Path:
    target=path.resolve(); repo=Path(__file__).resolve().parents[3]
    if target==repo or repo in target.parents: raise ValueError("private output must be outside repository")
    return target


def chain_tail(path: Path) -> tuple[int,str]:
    prior="0"*64; count=0
    if not path.exists(): return count,prior
    for line in path.read_text(encoding="utf-8").splitlines():
        row=json.loads(line); recorded=row.pop("record_sha256",None)
        actual=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        if row.get("prior_record_sha256")!=prior or recorded!=actual: raise ValueError("existing chain invalid")
        prior=actual; count+=1
    return count,prior


def capture(api: Any, output: Path, boundary_id: str, phase: str) -> dict[str,Any]:
    if not boundary_id or phase not in {"BEFORE","INSIDE","AFTER"}: raise ValueError("invalid boundary label")
    output=private_target(output); output.mkdir(parents=True,exist_ok=True)
    key_path=output/"PRIVATE_HMAC_KEY.bin"
    if not key_path.exists(): key_path.write_bytes(secrets.token_bytes(32))
    key=key_path.read_bytes()
    if len(key)!=32: raise ValueError("private key invalid")
    path=output/"session_boundary_records.jsonl"; _,prior=chain_tail(path)
    if not api.initialize(): raise ValueError(f"MT5 attach failed: {api.last_error()}")
    try:
        terminal=plain(api.terminal_info()); account=plain(api.account_info())
        symbol=plain(api.symbol_info("XAUUSD")); tick=plain(api.symbol_info_tick("XAUUSD"))
        observed=datetime.now(timezone.utc)
    finally: api.shutdown()
    if not isinstance(terminal,dict) or terminal.get("tradeapi_disabled") is not True:
        raise ValueError("external Python trading is not disabled")
    if not all(isinstance(value,dict) for value in (account,symbol,tick)):
        raise ValueError("required read-only snapshot missing")
    tick_age=observed.timestamp()-tick.get("time_msc",0)/1000 if tick.get("time_msc") else None
    identity=hmac.new(key,f"{account.get('login')}|{account.get('server')}|XAUUSD".encode(),hashlib.sha256).hexdigest()
    row={"schema":"xauusd-private-boundary-observation-1.0","boundary_id":boundary_id,"phase":phase,
         "observed_utc":observed.isoformat().replace("+00:00","Z"),"connected":terminal.get("connected"),
         "tradeapi_disabled":True,"tick_age_seconds":round(tick_age,3) if tick_age is not None else None,
         "identity_token":identity,"terminal_build":terminal.get("build"),"symbol_trade_mode":symbol.get("trade_mode"),
         "prior_record_sha256":prior,"claim_limit":"Private read-only boundary observation; not trading authorization."}
    digest=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(",",":")).encode()).hexdigest(); row["record_sha256"]=digest
    with path.open("a",encoding="utf-8",newline="\n") as handle:
        handle.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n"); handle.flush(); os.fsync(handle.fileno())
    return {"status":"CAPTURED","boundary_id":boundary_id,"phase":phase,"record_sha256":digest}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--boundary-id",required=True); parser.add_argument("--phase",choices=["BEFORE","INSIDE","AFTER"],required=True)
    args=parser.parse_args()
    try: print(json.dumps(capture(ReadOnlyMT5,args.output,args.boundary_id,args.phase),sort_keys=True)); return 0
    except (OSError,ValueError,json.JSONDecodeError) as exc: print(f"FAIL CLOSED: {exc}",file=sys.stderr); return 2


if __name__=="__main__": raise SystemExit(main())

