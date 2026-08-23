"""Capture one private account/symbol snapshot without using order APIs."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
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


def capture(api: Any, output: Path) -> dict[str,Any]:
    output=private_target(output); output.mkdir(parents=True,exist_ok=False)
    if not api.initialize(): raise ValueError(f"MT5 attach failed: {api.last_error()}")
    try:
        terminal=plain(api.terminal_info()); account=plain(api.account_info())
        symbol=plain(api.symbol_info("XAUUSD")); tick=plain(api.symbol_info_tick("XAUUSD"))
        observed=datetime.now(timezone.utc)
    finally: api.shutdown()
    if not isinstance(terminal,dict) or terminal.get("tradeapi_disabled") is not True:
        raise ValueError("external Python trading is not disabled")
    if not all(isinstance(value,dict) for value in (account,symbol,tick)):
        raise ValueError("required snapshot unavailable")
    key=secrets.token_bytes(32)
    token=hmac.new(key,f"{account.get('login')}|{account.get('server')}|XAUUSD".encode(),hashlib.sha256).hexdigest()
    snapshot={"schema":"m1-private-account-snapshot-1.0","observed_utc":observed.isoformat().replace("+00:00","Z"),
              "tradeapi_disabled":True,"identity_token":token,"account_currency":account.get("currency"),
              "leverage":account.get("leverage"),"equity":account.get("equity"),"margin":account.get("margin"),
              "margin_free":account.get("margin_free"),"margin_level":account.get("margin_level"),
              "trade_calc_mode":symbol.get("trade_calc_mode"),"trade_contract_size":symbol.get("trade_contract_size"),
              "currency_margin":symbol.get("currency_margin"),"currency_base":symbol.get("currency_base"),
              "currency_profit":symbol.get("currency_profit"),"volume_min":symbol.get("volume_min"),
              "volume_step":symbol.get("volume_step"),"bid":tick.get("bid"),"ask":tick.get("ask"),
              "tick_time_msc":tick.get("time_msc"),"claim_limit":"Private M1 inputs only; not trading authorization."}
    encoded=(json.dumps(snapshot,indent=2,sort_keys=True)+"\n").encode(); path=output/"PRIVATE_MARGIN_SNAPSHOT.json"
    path.write_bytes(encoded); (output/"PRIVATE_HMAC_KEY.bin").write_bytes(key)
    digest=hashlib.sha256(encoded).hexdigest()
    return {"status":"CAPTURED_PRIVATE","snapshot_sha256":digest,"claim_limit":"No M1 verdict without frozen stress inputs."}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,required=True); args=parser.parse_args()
    try: print(json.dumps(capture(ReadOnlyMT5,args.output),sort_keys=True)); return 0
    except (OSError,ValueError) as exc: print(f"FAIL CLOSED: {exc}",file=sys.stderr); return 2


if __name__=="__main__": raise SystemExit(main())

