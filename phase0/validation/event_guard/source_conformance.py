"""Deterministic source-acquisition and revision conformance checks.

The module is intentionally network-free.  It validates records produced by a
separate read-only capture step and never imports broker, order, or model APIs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from urllib.parse import urlparse

from event_guard_oracle import Event, interval

UTC = timezone.utc
ZERO_HASH = "0" * 64


@dataclass(frozen=True)
class SourcePolicy:
    source: str
    role: str
    urls: tuple[str, ...]
    url_prefixes: tuple[str, ...]
    content_types: tuple[str, ...]
    parser_version: str
    schema_fingerprint: str
    max_age: timedelta
    max_bytes: int
    required_taxonomy_max_lag_days: tuple[tuple[str, int], ...] = ()
    admission: str = "CANDIDATE"


POLICIES = {
    "BLS_ICS": SourcePolicy(
        source="BLS_ICS",
        role="LOCK_AUTHORITATIVE",
        urls=("https://www.bls.gov/schedule/news_release/bls.ics",),
        url_prefixes=(),
        content_types=("text/calendar", "text/plain", "application/octet-stream"),
        parser_version="ics-subset-v1",
        schema_fingerprint="VCALENDAR/VEVENT/SUMMARY/DTSTART/UID@v1",
        max_age=timedelta(hours=26),
        max_bytes=4_000_000,
        required_taxonomy_max_lag_days=(("US_EMPLOYMENT", 45), ("US_CPI", 45)),
    ),
    "BEA_JSON": SourcePolicy(
        source="BEA_JSON",
        role="LOCK_AUTHORITATIVE",
        urls=("https://apps.bea.gov/API/signup/release_dates.json",),
        url_prefixes=(),
        content_types=("application/json", "text/json", "text/plain"),
        parser_version="bea-json-v1",
        schema_fingerprint="object/title/release_dates[]@v1",
        max_age=timedelta(hours=26),
        max_bytes=4_000_000,
        required_taxonomy_max_lag_days=(("US_PCE", 45),),
    ),
    "FED_CALENDAR": SourcePolicy(
        source="FED_CALENDAR",
        role="LOCK_AUTHORITATIVE",
        urls=("https://www.federalreserve.gov/monetarypolicy.htm",),
        url_prefixes=(
            "https://www.federalreserve.gov/newsevents/",
            "https://www.federalreserve.gov/monetarypolicy/",
        ),
        content_types=("text/html", "application/xhtml+xml"),
        parser_version="fed-calendar-html-v1",
        schema_fingerprint="FED/monthly-event/date/time/title@v1",
        max_age=timedelta(hours=26),
        max_bytes=6_000_000,
        required_taxonomy_max_lag_days=(
            ("FOMC_STATEMENT", 75),
            ("FOMC_PRESS_CONFERENCE", 75),
            ("FOMC_MINUTES", 75),
        ),
    ),
    "DOL_UI": SourcePolicy(
        source="DOL_UI",
        role="LOCK_AUTHORITATIVE",
        urls=("https://www.dol.gov/newsroom/economicdata",),
        url_prefixes=("https://www.dol.gov/newsroom/releases/eta",),
        content_types=("text/html", "application/pdf"),
        parser_version="dol-ui-schedule-v0",
        schema_fingerprint="UNRESOLVED_FORWARD_SCHEDULE_WITH_EXCEPTIONS",
        max_age=timedelta(hours=26),
        max_bytes=8_000_000,
        required_taxonomy_max_lag_days=(("US_JOBLESS_CLAIMS", 14),),
        admission="BLOCKED_NO_AUTHORITATIVE_FORWARD_SCHEDULE",
    ),
    "CENSUS_WATCH": SourcePolicy(
        source="CENSUS_WATCH",
        role="WATCH_ONLY",
        urls=("https://www.census.gov/economic-indicators/calendar-listview.html",),
        url_prefixes=(),
        content_types=("text/html",),
        parser_version="census-calendar-html-v1",
        schema_fingerprint="CENSUS/calendar/date/time/title/status@v1",
        max_age=timedelta(hours=26),
        max_bytes=8_000_000,
    ),
    "FRED_CROSSCHECK": SourcePolicy(
        source="FRED_CROSSCHECK",
        role="DATE_CROSSCHECK_ONLY",
        urls=("https://api.stlouisfed.org/fred/release/dates",),
        url_prefixes=(),
        content_types=("application/json", "application/xml", "text/xml"),
        parser_version="fred-date-crosscheck-v1",
        schema_fingerprint="FRED/release_date/date-only@v1",
        max_age=timedelta(hours=26),
        max_bytes=2_000_000,
    ),
}


@dataclass(frozen=True)
class AcquisitionRecord:
    source: str
    url: str
    retrieved_utc: str
    http_status: int
    content_type: str
    body_sha256: str
    byte_count: int
    parser_version: str
    schema_fingerprint: str
    etag: str = ""
    last_modified: str = ""
    cache_record_sha256: str = ""
    previous_record_sha256: str = ZERO_HASH
    record_sha256: str = ""


@dataclass(frozen=True)
class Revision:
    kind: str
    source: str
    source_id: str
    old_time_utc: str = ""
    new_time_utc: str = ""


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _record_payload(record: AcquisitionRecord) -> dict:
    value = asdict(record)
    value.pop("record_sha256", None)
    return value


def record_digest(record: AcquisitionRecord) -> str:
    return hashlib.sha256(_canonical(_record_payload(record)).encode("utf-8")).hexdigest()


def observed_schema_fingerprint(source: str, body: bytes) -> str:
    """Derive the admitted shape from body content; never trust caller metadata."""
    policy = POLICIES[source]
    if not body:
        return "EMPTY"
    text = body.decode("utf-8", errors="replace")
    lower = text.lower()
    if source == "BLS_ICS":
        required = ("BEGIN:VCALENDAR", "BEGIN:VEVENT", "SUMMARY:", "DTSTART", "UID:")
        return policy.schema_fingerprint if all(token in text for token in required) else "UNRECOGNIZED"
    if source == "BEA_JSON":
        try:
            value = json.loads(text)
            valid = (type(value) is dict and bool(value)
                     and all(type(title) is str and type(item) is dict
                             and type(item.get("release_dates")) is list
                             and all(type(date) is str for date in item["release_dates"])
                             for title, item in value.items()))
            return policy.schema_fingerprint if valid else "UNRECOGNIZED"
        except json.JSONDecodeError:
            return "UNRECOGNIZED"
    if source == "FED_CALENDAR":
        required_groups = (
            ("federal open market committee", "fomc"),
            ("upcoming dates", "fomc meeting", "fomc minutes"),
        )
        return policy.schema_fingerprint if all(any(token in lower for token in group)
                                                for group in required_groups) else "UNRECOGNIZED"
    if source == "CENSUS_WATCH":
        required_groups = (("economic indicators",), ("release",), ("time", "am", "pm"))
        return policy.schema_fingerprint if all(any(token in lower for token in group)
                                                for group in required_groups) else "UNRECOGNIZED"
    if source == "DOL_UI":
        # An observed publication page can never establish the unresolved
        # exception-aware forward-schedule contract.
        return "UNRESOLVED_FORWARD_SCHEDULE_WITH_EXCEPTIONS"
    if source == "FRED_CROSSCHECK":
        try:
            value = json.loads(text)
            return policy.schema_fingerprint if isinstance(value, dict) and "release_dates" in value else "UNRECOGNIZED"
        except json.JSONDecodeError:
            return "UNRECOGNIZED"
    return "UNRECOGNIZED"


def make_record(*, source: str, url: str, retrieved_utc: datetime, http_status: int,
                content_type: str, body: bytes, parser_version: str | None = None,
                etag: str = "", last_modified: str = "", previous_record_sha256: str = ZERO_HASH,
                cached_record: AcquisitionRecord | None = None) -> AcquisitionRecord:
    policy = POLICIES[source]
    if http_status == 304:
        if cached_record is None or body:
            raise ValueError("304 requires an empty body and a cached record")
        body_sha256 = cached_record.body_sha256
        byte_count = cached_record.byte_count
        content_type = content_type or cached_record.content_type
        schema_fingerprint = cached_record.schema_fingerprint
    else:
        body_sha256 = hashlib.sha256(body).hexdigest()
        byte_count = len(body)
        schema_fingerprint = observed_schema_fingerprint(source, body)
    draft = AcquisitionRecord(
        source=source,
        url=url,
        retrieved_utc=retrieved_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        http_status=http_status,
        content_type=content_type,
        body_sha256=body_sha256,
        byte_count=byte_count,
        parser_version=parser_version or policy.parser_version,
        schema_fingerprint=schema_fingerprint,
        etag=etag,
        last_modified=last_modified,
        cache_record_sha256=cached_record.record_sha256 if http_status == 304 else "",
        previous_record_sha256=previous_record_sha256,
    )
    return AcquisitionRecord(**_record_payload(draft), record_sha256=record_digest(draft))


def _url_allowed(policy: SourcePolicy, url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment:
        return False
    return url in policy.urls or any(url.startswith(prefix) for prefix in policy.url_prefixes)


def assess_snapshot(record: AcquisitionRecord, body: bytes, now: datetime,
                    cached_record: AcquisitionRecord | None = None) -> tuple[bool, tuple[str, ...]]:
    """Validate one HTTP acquisition record without performing network access."""
    reasons: list[str] = []
    policy = POLICIES.get(record.source)
    if policy is None:
        return False, ("UNKNOWN_SOURCE",)
    if not _url_allowed(policy, record.url):
        reasons.append("URL_NOT_ALLOWLISTED")
    if record.http_status not in {200, 304}:
        reasons.append("HTTP_STATUS")
    content_type = record.content_type.split(";", 1)[0].strip().lower()
    if content_type not in policy.content_types:
        reasons.append("CONTENT_TYPE")
    if record.byte_count <= 0 or record.byte_count > policy.max_bytes:
        reasons.append("BODY_SIZE")
    if record.parser_version != policy.parser_version:
        reasons.append("PARSER_VERSION")
    if record.schema_fingerprint != policy.schema_fingerprint:
        reasons.append("SCHEMA_DRIFT")
    try:
        retrieved = datetime.fromisoformat(record.retrieved_utc.replace("Z", "+00:00"))
        if retrieved.tzinfo is None:
            raise ValueError
        age = now.astimezone(UTC) - retrieved.astimezone(UTC)
        if age < timedelta(minutes=-5) or age > policy.max_age:
            reasons.append("STALE_OR_FUTURE")
    except ValueError:
        reasons.append("INVALID_RETRIEVAL_TIME")
    if record.record_sha256 != record_digest(record):
        reasons.append("RECORD_HASH")
    if record.http_status == 200:
        if hashlib.sha256(body).hexdigest() != record.body_sha256 or len(body) != record.byte_count:
            reasons.append("BODY_HASH_OR_SIZE")
    elif cached_record is None:
        reasons.append("CACHE_REQUIRED")
    else:
        if body:
            reasons.append("304_BODY_NOT_EMPTY")
        if (record.body_sha256, record.byte_count) != (cached_record.body_sha256, cached_record.byte_count):
            reasons.append("CACHE_IDENTITY")
        if record.cache_record_sha256 != cached_record.record_sha256:
            reasons.append("CACHE_IDENTITY_LINK")
    if policy.admission != "CANDIDATE" and policy.role == "LOCK_AUTHORITATIVE":
        reasons.append(policy.admission)
    return not reasons, tuple(sorted(set(reasons)))


def verify_record_chain(records: list[AcquisitionRecord]) -> tuple[bool, tuple[int, ...]]:
    broken: list[int] = []
    expected_previous = ZERO_HASH
    for index, record in enumerate(records):
        if record.previous_record_sha256 != expected_previous or record.record_sha256 != record_digest(record):
            broken.append(index)
        expected_previous = record.record_sha256
    return not broken, tuple(broken)


def coverage_inventory(now: datetime, events: list[Event],
                       healthy_sources: set[str]) -> tuple[bool, dict[str, str]]:
    """Prove a fresh, forward event exists for every frozen lock taxonomy."""
    now = now.astimezone(UTC)
    result: dict[str, str] = {}
    for policy in POLICIES.values():
        if policy.role != "LOCK_AUTHORITATIVE":
            continue
        for taxonomy, max_lag_days in policy.required_taxonomy_max_lag_days:
            key = f"{policy.source}:{taxonomy}"
            if policy.admission != "CANDIDATE":
                result[key] = policy.admission
                continue
            if policy.source not in healthy_sources:
                result[key] = "SOURCE_UNHEALTHY"
                continue
            candidates = [
                event for event in events
                if event.source == policy.source and event.taxonomy == taxonomy
                and event.status == "SCHEDULED" and now <= event.scheduled_utc
                <= now + timedelta(days=max_lag_days)
            ]
            result[key] = "COVERED" if candidates else "MISSING_FORWARD_EVENT"
    return all(value == "COVERED" for value in result.values()), result


def revision_delta(previous: list[Event], current: list[Event], now: datetime
                   ) -> tuple[bool, tuple[Revision, ...]]:
    """Type revisions and reject unexplained disappearance of a future event."""
    prior = {(event.source, event.source_id): event for event in previous}
    latest = {(event.source, event.source_id): event for event in current}
    if len(prior) != len(previous) or len(latest) != len(current):
        return False, (Revision("DUPLICATE_ID", "", ""),)
    revisions: list[Revision] = []
    healthy = True
    for key, old in prior.items():
        new = latest.get(key)
        if new is None:
            if old.scheduled_utc >= now.astimezone(UTC) and old.status != "CANCELLED":
                revisions.append(Revision("UNEXPLAINED_DISAPPEARANCE", old.source, old.source_id,
                                          old.scheduled_utc.isoformat(), ""))
                healthy = False
            continue
        if old.status != new.status:
            revisions.append(Revision(new.status, new.source, new.source_id,
                                      old.scheduled_utc.isoformat(), new.scheduled_utc.isoformat()))
        if old.scheduled_utc != new.scheduled_utc:
            revisions.append(Revision("MOVED", new.source, new.source_id,
                                      old.scheduled_utc.isoformat(), new.scheduled_utc.isoformat()))
    for key, new in latest.items():
        if key not in prior:
            revisions.append(Revision("ADDED", new.source, new.source_id, "",
                                      new.scheduled_utc.isoformat()))
    return healthy, tuple(revisions)


def conservative_revision_events(previous: list[Event], current: list[Event], now: datetime
                                 ) -> list[Event]:
    """Retain the old lock window after a move until that old window has ended."""
    latest = {(event.source, event.source_id): event for event in current}
    effective = list(current)
    for old in previous:
        new = latest.get((old.source, old.source_id))
        if (new is not None and old.scheduled_utc != new.scheduled_utc
                and old.status != "CANCELLED" and now.astimezone(UTC) < interval(old)[1]):
            effective.append(old)
    return effective
