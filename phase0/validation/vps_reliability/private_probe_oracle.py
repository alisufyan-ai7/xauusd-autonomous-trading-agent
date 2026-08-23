"""Offline closure verifier for private VPS probe records."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


REQUIRED={"BASELINE","DISCONNECT","RECONNECT","PYTHON_RESTART","MT5_RESTART","WINDOWS_RESTART","CLOCK_CHECK","BUILD_CHECK"}
SHA=re.compile(r"^[0-9a-f]{64}$")


def _utc(value: Any) -> datetime | None:
    try:
        parsed=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None: return None
    return parsed.astimezone(timezone.utc)


def verify_private_matrix(records: list[dict[str,Any]]) -> dict[str,Any]:
    reasons=[]; prior="0"*64; events=[]; baseline=None; saw_disconnect=False
    current_boot=None; current_mt5_start=None; previous_process=None
    previous_observed=None; scenario_ids=set()
    for index,supplied in enumerate(records):
        row=dict(supplied); recorded=row.pop("record_sha256",None)
        actual=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        if row.get("sequence")!=index or row.get("prior_record_sha256")!=prior or recorded!=actual:
            reasons.append("HASH_CHAIN_INVALID"); break
        prior=actual; event=row.get("event")
        if event not in REQUIRED or event in events:
            reasons.append("EVENT_DUPLICATE_OR_INVALID")
        events.append(event)
        if index == 0 and event != "BASELINE":
            reasons.append("BASELINE_NOT_FIRST")
        scenario=row.get("scenario_id")
        if not isinstance(scenario,str) or not scenario.strip() or scenario in scenario_ids:
            reasons.append("SCENARIO_ID_INVALID_OR_DUPLICATE")
        else: scenario_ids.add(scenario)
        observed=_utc(row.get("observed_utc")); boot=_utc(row.get("os_boot_utc")); mt5_start=_utc(row.get("mt5_start_utc"))
        if observed is None or boot is None or mt5_start is None or boot>mt5_start or mt5_start>observed:
            reasons.append("OBSERVATION_OR_START_TIME_INVALID")
        if observed is not None and previous_observed is not None and observed<=previous_observed:
            reasons.append("OBSERVATION_TIME_NOT_STRICTLY_INCREASING")
        if observed is not None: previous_observed=observed
        if event=="BASELINE" and baseline is None:
            baseline=row; current_boot=row.get("os_boot_utc"); current_mt5_start=row.get("mt5_start_utc")
        if event=="DISCONNECT":
            saw_disconnect=True
            if row.get("connected") is not False: reasons.append("DISCONNECT_NOT_OBSERVED")
        elif event=="RECONNECT":
            if not saw_disconnect: reasons.append("RECONNECT_WITHOUT_PRIOR_DISCONNECT")
            if row.get("connected") is not True or not isinstance(row.get("tick_age_seconds"),(int,float)) or not -2<=row["tick_age_seconds"]<=30:
                reasons.append("RECONNECT_NOT_HEALTHY")
        elif event in REQUIRED-{"DISCONNECT"}:
            if row.get("connected") is not True: reasons.append("EXPECTED_HEALTHY_PROBE_NOT_CONNECTED")
        if row.get("tradeapi_disabled") is not True:
            reasons.append("EXTERNAL_PYTHON_TRADING_NOT_DISABLED")
        if event != "DISCONNECT" and not SHA.fullmatch(str(row.get("identity_token", ""))):
            reasons.append("IDENTITY_TOKEN_MISSING")
        if not SHA.fullmatch(str(row.get("process_token", ""))):
            reasons.append("PROCESS_TOKEN_INVALID")
        if baseline and row.get("identity_token") not in (None,baseline.get("identity_token")):
            reasons.append("IDENTITY_DRIFT")
        if event=="WINDOWS_RESTART" and baseline:
            if row.get("os_boot_utc")==current_boot: reasons.append("WINDOWS_BOOT_ID_NOT_CHANGED")
            else: current_boot=row.get("os_boot_utc"); current_mt5_start=row.get("mt5_start_utc")
        elif current_boot is not None and row.get("os_boot_utc")!=current_boot:
            reasons.append("UNDECLARED_WINDOWS_RESTART")
        if event=="MT5_RESTART" and baseline:
            if row.get("mt5_start_utc")==current_mt5_start: reasons.append("MT5_START_TIME_NOT_CHANGED")
            else: current_mt5_start=row.get("mt5_start_utc")
        elif current_mt5_start is not None and row.get("mt5_start_utc")!=current_mt5_start and event!="WINDOWS_RESTART":
            reasons.append("UNDECLARED_MT5_RESTART")
        if event=="PYTHON_RESTART" and previous_process==row.get("process_token"):
            reasons.append("PYTHON_PROCESS_TOKEN_NOT_CHANGED")
        if event=="CLOCK_CHECK" and not SHA.fullmatch(str(row.get("w32tm_status_sha256", ""))):
            reasons.append("CLOCK_STATUS_MISSING")
        if event=="BUILD_CHECK" and baseline and row.get("terminal_build")!=baseline.get("terminal_build") and not SHA.fullmatch(str(row.get("compatibility_artifact_sha256", ""))):
            reasons.append("BUILD_CHANGE_NOT_REVALIDATED")
        supplied_compat=row.get("compatibility_artifact_sha256")
        if supplied_compat is not None and not SHA.fullmatch(str(supplied_compat)):
            reasons.append("COMPATIBILITY_DIGEST_INVALID")
        previous_process=row.get("process_token")
    missing=sorted(REQUIRED-set(events))
    if missing: reasons.append("REQUIRED_SCENARIOS_INCOMPLETE")
    return {"status":"PASS" if not reasons else "FAIL_CLOSED","reasons":sorted(set(reasons)),
            "missing_events":missing,"final_record_sha256":prior,
            "claim_limit":"Point-in-time fault observations only; not trading authorization."}
