"""Deterministic verifier for private XAUUSD session-boundary evidence."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SHA256 = re.compile(r"^[0-9a-f]{64}$")
WEEKDAYS = set(range(7))
FROZEN_SOURCE_HOSTS = {"get.exness.help"}


class EvidenceError(ValueError):
    pass


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise EvidenceError("timestamp must include an offset")
    return parsed.astimezone(timezone.utc)


def _clock(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise EvidenceError("invalid local session time") from exc


def validate_schedule(payload: dict[str, Any], *, now_utc: datetime) -> None:
    if payload.get("schema") != "xauusd-account-session-schedule-1.0":
        raise EvidenceError("unsupported schedule schema")
    if payload.get("symbol") != "XAUUSD":
        raise EvidenceError("schedule is not for XAUUSD")
    source = payload.get("source")
    if not isinstance(source, dict) or source.get("authority") != "BROKER_ACCOUNT_SPECIFICATION":
        raise EvidenceError("account-specific broker authority is required")
    if source.get("account_specific") is not True:
        raise EvidenceError("source is not declared account-specific")
    parsed_url = urlparse(str(source.get("url", "")))
    if parsed_url.scheme != "https" or parsed_url.hostname not in FROZEN_SOURCE_HOSTS:
        raise EvidenceError("source URL is outside the frozen official host policy")
    if not SHA256.fullmatch(str(source.get("raw_sha256", ""))):
        raise EvidenceError("raw source digest is missing")
    retrieved = _utc(str(source.get("retrieved_utc", "")))
    now = now_utc.astimezone(timezone.utc)
    if retrieved > now + timedelta(minutes=5) or now - retrieved > timedelta(days=7):
        raise EvidenceError("source retrieval is future-dated or stale")
    try:
        ZoneInfo(str(payload.get("timezone", "")))
    except ZoneInfoNotFoundError as exc:
        raise EvidenceError("IANA timezone is unavailable") from exc

    intervals = payload.get("weekly_intervals")
    if not isinstance(intervals, list) or not intervals:
        raise EvidenceError("weekly intervals are missing")
    normalized = set()
    for row in intervals:
        if not isinstance(row, dict) or row.get("weekday") not in WEEKDAYS:
            raise EvidenceError("invalid weekday")
        item = (row["weekday"], _clock(str(row.get("start", ""))), _clock(str(row.get("end", ""))))
        if item[1] == item[2] or item in normalized:
            raise EvidenceError("zero-duration or duplicate weekly interval")
        normalized.add(item)

    overrides = payload.get("holiday_overrides")
    if not isinstance(overrides, list):
        raise EvidenceError("holiday overrides must be explicit")
    if overrides:
        holiday_source=payload.get("holiday_source")
        if not isinstance(holiday_source,dict): raise EvidenceError("holiday source is missing")
        holiday_url=urlparse(str(holiday_source.get("url","")))
        if holiday_url.scheme!="https" or holiday_url.hostname not in FROZEN_SOURCE_HOSTS:
            raise EvidenceError("holiday source is outside frozen official host policy")
        if not SHA256.fullmatch(str(holiday_source.get("raw_sha256",""))):
            raise EvidenceError("holiday source digest is missing")
        holiday_retrieved=_utc(str(holiday_source.get("retrieved_utc","")))
        if holiday_retrieved>now+timedelta(minutes=5) or now-holiday_retrieved>timedelta(days=7):
            raise EvidenceError("holiday source retrieval is future-dated or stale")
    seen_dates: set[date] = set()
    for row in overrides:
        try:
            local_date = date.fromisoformat(str(row.get("date", "")))
        except ValueError as exc:
            raise EvidenceError("invalid holiday date") from exc
        if local_date in seen_dates:
            raise EvidenceError("duplicate holiday override")
        seen_dates.add(local_date)
        closed = row.get("closed")
        holiday_intervals = row.get("intervals")
        if closed is True:
            if holiday_intervals not in (None, []):
                raise EvidenceError("closed holiday cannot contain intervals")
        elif closed is False:
            if not isinstance(holiday_intervals, list) or not holiday_intervals:
                raise EvidenceError("open holiday requires explicit intervals")
            for interval in holiday_intervals:
                start, end = _clock(str(interval.get("start", ""))), _clock(str(interval.get("end", "")))
                if start == end:
                    raise EvidenceError("zero-duration holiday interval")
        else:
            raise EvidenceError("holiday closure state must be explicit")


def _contains(local_dt: datetime, local_date: date, start: time, end: time) -> bool:
    start_dt = datetime.combine(local_date, start, local_dt.tzinfo)
    end_date = local_date if end > start else local_date + timedelta(days=1)
    end_dt = datetime.combine(end_date, end, local_dt.tzinfo)
    return start_dt <= local_dt < end_dt


def scheduled_open(payload: dict[str, Any], observed_utc: str) -> bool:
    zone = ZoneInfo(payload["timezone"])
    local = _utc(observed_utc).astimezone(zone)
    overrides = {date.fromisoformat(row["date"]): row for row in payload["holiday_overrides"]}
    current_override = overrides.get(local.date())
    if current_override is not None:
        if current_override["closed"] is True: return False
        return any(_contains(local,local.date(),_clock(row["start"]),_clock(row["end"])) for row in current_override["intervals"])
    for candidate_date in (local.date(), local.date() - timedelta(days=1)):
        override = overrides.get(candidate_date)
        if override is not None:
            if override["closed"]:
                continue
            intervals = override["intervals"]
        else:
            intervals = [row for row in payload["weekly_intervals"] if row["weekday"] == candidate_date.weekday()]
        for row in intervals:
            if _contains(local, candidate_date, _clock(row["start"]), _clock(row["end"])):
                return True
    return False


def verify_observations(
    payload: dict[str, Any], observations: list[dict[str, Any]], *,
    expected_boundary_ids: tuple[str, ...],
) -> dict[str, Any]:
    if not observations:
        return {"status": "FAIL_CLOSED", "reasons": ["NO_BOUNDARY_OBSERVATIONS"]}
    reasons: list[str] = []
    if (not expected_boundary_ids or any(not isinstance(item, str) or not item
                                         for item in expected_boundary_ids)
            or len(expected_boundary_ids) != len(set(expected_boundary_ids))):
        reasons.append("EXPECTED_BOUNDARY_INVENTORY_INVALID")
    expected = set(expected_boundary_ids)
    phases: dict[str, set[str]] = {}
    prior = "0" * 64
    previous_observed: datetime | None = None
    identity_token: str | None = None
    for index, row in enumerate(observations):
        if not isinstance(row, dict):
            reasons.append("OBSERVATION_SCHEMA_INVALID")
            continue
        encoded = json.dumps({k: v for k, v in row.items() if k != "record_sha256"}, sort_keys=True, separators=(",", ":")).encode()
        actual = hashlib.sha256(encoded).hexdigest()
        if row.get("prior_record_sha256") != prior or row.get("record_sha256") != actual:
            reasons.append("HASH_CHAIN_INVALID")
            break
        prior = actual
        if (row.get("schema") != "xauusd-private-boundary-observation-1.0"
                or row.get("sequence") != index):
            reasons.append("OBSERVATION_SCHEMA_INVALID")
        boundary_id = row.get("boundary_id")
        phase = row.get("phase")
        if not isinstance(boundary_id, str) or phase not in {"BEFORE", "INSIDE", "AFTER"}:
            reasons.append("BOUNDARY_LABEL_INVALID")
            continue
        phases.setdefault(boundary_id, set()).add(phase)
        token = row.get("identity_token")
        if not SHA256.fullmatch(str(token or "")):
            reasons.append("IDENTITY_TOKEN_INVALID")
        elif identity_token is None:
            identity_token = token
        elif token != identity_token:
            reasons.append("IDENTITY_DRIFT")
        if row.get("tradeapi_disabled") is not True:
            reasons.append("EXTERNAL_PYTHON_TRADING_NOT_DISABLED")
        if row.get("connected") is not True:
            reasons.append("TERMINAL_DISCONNECTED")
        try:
            observed = _utc(row["observed_utc"])
        except (KeyError, TypeError, ValueError):
            reasons.append("OBSERVATION_TIME_INVALID")
            continue
        if previous_observed is not None and observed <= previous_observed:
            reasons.append("OBSERVATION_TIME_NOT_STRICTLY_INCREASING")
        previous_observed = observed
        expected_open = scheduled_open(payload, row["observed_utc"])
        if expected_open != (phase in {"BEFORE", "AFTER"}):
            reasons.append("BOUNDARY_PHASE_TIME_MISMATCH")
        fresh_tick = row.get("connected") is True and isinstance(row.get("tick_age_seconds"), (int, float)) and -2 <= row["tick_age_seconds"] <= 30
        if expected_open != fresh_tick:
            reasons.append("SCHEDULE_TICK_DISCREPANCY")
    if any(value != {"BEFORE", "INSIDE", "AFTER"} for value in phases.values()):
        reasons.append("BOUNDARY_PHASE_INCOMPLETE")
    if set(phases) != expected:
        reasons.append("EXPECTED_BOUNDARY_INVENTORY_INCOMPLETE")
    return {
        "status": "PASS" if not reasons else "FAIL_CLOSED",
        "reasons": sorted(set(reasons)),
        "boundaries_complete": len(phases) if set(phases) == expected else 0,
        "final_record_sha256": prior,
        "claim_limit": "Point-in-time session evidence only; not trading authorization.",
    }
