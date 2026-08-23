"""Independent, offline oracle for the free official-source Event Guard design.

This module deliberately performs no network access and has no trading imports.  It
tests normalization, source-health, reconciliation, interval, and shock-lock
semantics against captured/constructed official-source shapes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from html.parser import HTMLParser
import json
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC = timezone.utc
EASTERN = "America/New_York"
WINDOWS = {"TIER_1": (30, 30), "TIER_2": (15, 15)}
BLS_ZONE_ALIASES = {
    "Eastern Standard Time": EASTERN,
    "US Eastern Standard Time": EASTERN,
    "US-Eastern": EASTERN,
}


def verified_zone(zone: str) -> ZoneInfo:
    """Load an IANA zone or fail with a deterministic operator diagnostic."""
    try:
        return ZoneInfo(zone)
    except ZoneInfoNotFoundError as exc:
        try:
            ZoneInfo(EASTERN)
        except ZoneInfoNotFoundError:
            raise RuntimeError(
                "IANA timezone data unavailable; install the hash-pinned Event Guard "
                "Windows requirements before testing or capture"
            ) from exc
        raise ValueError(f"unsupported or unverified timezone identifier: {zone}") from exc


def admitted_source_zone(source: str, zone: str) -> str:
    """Map only frozen, source-specific aliases to a verified IANA zone."""
    if source == "BLS_ICS" and zone in BLS_ZONE_ALIASES:
        return BLS_ZONE_ALIASES[zone]
    return zone


@dataclass(frozen=True)
class Event:
    source: str
    source_id: str
    title: str
    scheduled_utc: datetime
    source_timezone: str
    taxonomy: str
    tier: str
    status: str = "SCHEDULED"
    payload_sha256: str = ""

    def __post_init__(self):
        if self.scheduled_utc.tzinfo is None or self.scheduled_utc.utcoffset() != timedelta(0):
            raise ValueError("scheduled_utc must be timezone-aware UTC")
        if self.tier not in WINDOWS:
            raise ValueError("unknown tier")
        if self.status not in {"SCHEDULED", "CANCELLED", "SUSPENDED", "TENTATIVE"}:
            raise ValueError("unknown status")


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def payload_hash(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def local_to_utc(date_text: str, time_text: str, zone: str = EASTERN) -> datetime:
    """Normalize an explicit IANA-zone local timestamp to UTC."""
    if not zone or "/" not in zone:
        raise ValueError("verified IANA timezone required")
    local = datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M").replace(
        tzinfo=verified_zone(zone)
    )
    return local.astimezone(UTC)


def parse_utc(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timezone missing")
    return parsed.astimezone(UTC)


def classify(title: str) -> tuple[str, str] | None:
    text = re.sub(r"\s+", " ", title).strip().lower()
    rules = (
        (("employment situation",), ("US_EMPLOYMENT", "TIER_1")),
        (("consumer price index", "cpi"), ("US_CPI", "TIER_1")),
        (("personal income and outlays",), ("US_PCE", "TIER_1")),
        (("fomc statement", "federal open market committee statement", "fomc meeting"), ("FOMC_STATEMENT", "TIER_1")),
        (("fomc press conference",), ("FOMC_PRESS_CONFERENCE", "TIER_1")),
        (("fomc minutes",), ("FOMC_MINUTES", "TIER_1")),
        (("initial claims", "jobless claims", "unemployment insurance weekly claims"), ("US_JOBLESS_CLAIMS", "TIER_2")),
        (("fed speech", "federal reserve speech", "fed testimony"), ("FED_COMMUNICATION", "TIER_2")),
    )
    for names, result in rules:
        if any(name in text for name in names):
            return result
    return None


def _unfold_ics(text: str) -> list[str]:
    unfolded: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += raw[1:]
        else:
            unfolded.append(raw)
    return unfolded


def parse_ics(text: str, source: str, default_zone: str | None = None) -> list[Event]:
    """Parse the small RFC 5545 subset used by BLS/BEA release calendars."""
    blocks: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in _unfold_ics(text):
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT" and current is not None:
            blocks.append(current)
            current = None
        elif current is not None and ":" in line:
            key, value = line.split(":", 1)
            current[key] = value.replace("\\,", ",").replace("\\;", ";")

    events: list[Event] = []
    for item in blocks:
        title = item.get("SUMMARY", "")
        category = classify(title)
        if category is None:
            continue
        dt_key = next((key for key in item if key.startswith("DTSTART")), None)
        if dt_key is None:
            raise ValueError("DTSTART missing")
        raw = item[dt_key]
        zone_match = re.search(r"TZID=([^;:]+)", dt_key)
        if raw.endswith("Z"):
            scheduled = datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
            source_zone = "UTC"
        else:
            source_zone = zone_match.group(1) if zone_match else default_zone
            if not source_zone:
                raise ValueError("verified IANA timezone required")
            zone = admitted_source_zone(source, source_zone)
            scheduled = datetime.strptime(raw, "%Y%m%dT%H%M%S").replace(
                tzinfo=verified_zone(zone)
            ).astimezone(UTC)
            source_zone = zone
        status = item.get("STATUS", "CONFIRMED").upper()
        normalized_status = "CANCELLED" if status == "CANCELLED" else "SCHEDULED"
        taxonomy, tier = category
        source_id = item.get("UID") or hashlib.sha256(
            f"{source}|{title}|{scheduled.isoformat()}".encode()
        ).hexdigest()
        events.append(Event(source, source_id, title, scheduled, source_zone, taxonomy, tier,
                            normalized_status, payload_hash(item)))
    return events


def parse_bea_json(text: str) -> list[Event]:
    raw = json.loads(text)
    events: list[Event] = []
    for title, body in raw.items():
        category = classify(title)
        if category is None:
            continue
        taxonomy, tier = category
        for timestamp in body.get("release_dates", []):
            scheduled = parse_utc(timestamp)
            source_id = hashlib.sha256(f"BEA|{title}|{timestamp}".encode()).hexdigest()
            events.append(Event("BEA_JSON", source_id, title, scheduled, "UTC", taxonomy, tier,
                                payload_sha256=payload_hash({"title": title, "timestamp": timestamp})))
    return events


def parse_official_rows(rows: list[dict], source: str, zone: str = EASTERN) -> list[Event]:
    """Normalize monitored Fed/Census/DOL schedule rows after snapshot extraction."""
    events: list[Event] = []
    for row in rows:
        category = classify(row["title"])
        if category is None:
            continue
        status = row.get("status", "SCHEDULED").upper()
        if status in {"SUSPENDED", "TENTATIVE"} and not row.get("date"):
            # A time-less protected row cannot prove a safe interval.
            raise ValueError("protected suspended/tentative row lacks authoritative time")
        scheduled = local_to_utc(row["date"], row["time"], zone)
        taxonomy, tier = category
        source_id = row.get("id") or hashlib.sha256(
            f"{source}|{row['title']}|{scheduled.isoformat()}".encode()
        ).hexdigest()
        events.append(Event(source, source_id, row["title"], scheduled, zone, taxonomy, tier,
                            status, payload_hash(row)))
    return events


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tokens: list[str] = []

    def handle_data(self, data: str) -> None:
        value = re.sub(r"\s+", " ", data).strip()
        if value:
            self.tokens.append(value)


def _twelve_hour_to_24(value: str) -> str:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})\s*([ap])\.?m\.?", value.strip(), re.I)
    if not match:
        raise ValueError("verified Fed event time missing")
    hour, minute, meridiem = int(match.group(1)), int(match.group(2)), match.group(3).lower()
    if hour < 1 or hour > 12 or minute > 59:
        raise ValueError("invalid Fed event time")
    if meridiem == "p" and hour != 12:
        hour += 12
    if meridiem == "a" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


def parse_fed_monthly_html(text: str) -> list[Event]:
    """Parse exact-time FOMC rows from one official Fed month calendar."""
    parser = _VisibleText()
    parser.feed(text)
    tokens = parser.tokens
    page_text = " ".join(tokens[:80])
    month_match = re.search(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b",
        page_text,
        re.I,
    )
    if not month_match:
        raise ValueError("Fed calendar month/year missing")
    month = datetime.strptime(month_match.group(1), "%B").month
    year = int(month_match.group(2))
    admitted_titles = {"FOMC Meeting", "FOMC Press Conference", "FOMC Minutes"}
    rows: list[dict] = []
    for index, token in enumerate(tokens):
        if token not in admitted_titles:
            continue
        time_token = next(
            (candidate for candidate in reversed(tokens[max(0, index - 6):index])
             if re.fullmatch(r"\d{1,2}:\d{2}\s*[ap]\.?m\.?", candidate, re.I)),
            None,
        )
        day_token = next(
            (candidate for candidate in tokens[index + 1:index + 12]
             if re.fullmatch(r"\d{1,2}", candidate)),
            None,
        )
        if time_token is None or day_token is None:
            raise ValueError(f"exact Fed time/date missing for {token}")
        day = int(day_token)
        scheduled_date = datetime(year, month, day).date().isoformat()
        taxonomy = classify(token)
        if taxonomy is None:
            raise ValueError(f"unclassified protected Fed row: {token}")
        rows.append({
            "id": f"fed-{year:04d}{month:02d}{day:02d}-{taxonomy[0].lower()}",
            "title": token,
            "date": scheduled_date,
            "time": _twelve_hour_to_24(time_token),
        })
    if not rows:
        raise ValueError("no protected FOMC rows in Fed month calendar")
    return parse_official_rows(rows, "FED_CALENDAR")


def parse_dol_ui_schedule_html(text: str, now: datetime,
                               horizon_days: int = 21) -> list[Event]:
    """Expand ETA's explicit weekly rule and holiday exceptions into UTC events."""
    if horizon_days < 14 or horizon_days > 92:
        raise ValueError("DOL schedule horizon outside frozen bounds")
    parser = _VisibleText()
    parser.feed(text)
    visible = " ".join(parser.tokens)
    rule = re.search(
        r"published each week on Thursday morning at\s*"
        r"(\d{1,2}:\d{2}\s*[ap]\.?m\.?)\s*(EST|ET|EDT)\b",
        visible,
        re.I,
    )
    if rule is None or not re.search(
        r"Exceptions to this schedule occur when a Thursday falls on a Federal Holiday",
        visible,
        re.I,
    ):
        raise ValueError("authoritative DOL weekly rule or holiday contract missing")
    base_time = _twelve_hour_to_24(rule.group(1))
    if base_time != "08:30":
        raise ValueError("unexpected DOL weekly release time")

    exception_pattern = re.compile(
        r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*"
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
        r"(\d{1,2}),\s*(20\d{2}).{0,80}?"
        r"(\d{1,2}:\d{2}\s*[ap]\.?m\.?)\s*(EST|ET|EDT)\b",
        re.I,
    )
    exceptions: dict[tuple[int, int], tuple[datetime, str]] = {}
    for match in exception_pattern.finditer(visible):
        release_date = datetime.strptime(
            f"{match.group(1)}, {match.group(2)} {match.group(3)}, {match.group(4)}",
            "%A, %B %d, %Y",
        )
        if release_date.strftime("%A").lower() != match.group(1).lower():
            raise ValueError("DOL holiday exception weekday/date mismatch")
        week = release_date.date().isocalendar()[:2]
        if week in exceptions:
            raise ValueError("duplicate DOL holiday exception week")
        exceptions[week] = (release_date, _twelve_hour_to_24(match.group(5)))

    now_utc = now.astimezone(UTC)
    eastern = verified_zone(EASTERN)
    start = now_utc.astimezone(eastern).date()
    end_utc = now_utc + timedelta(days=horizon_days)
    rows: list[dict] = []
    for offset in range(horizon_days + 2):
        candidate = start + timedelta(days=offset)
        if candidate.weekday() != 3:
            continue
        exception = exceptions.get(candidate.isocalendar()[:2])
        if exception:
            release_date, release_time = exception
            local_date = release_date.date()
        else:
            local_date, release_time = candidate, base_time
        hour, minute = (int(value) for value in release_time.split(":"))
        scheduled = datetime(local_date.year, local_date.month, local_date.day,
                             hour, minute, tzinfo=eastern).astimezone(UTC)
        if scheduled < now_utc or scheduled > end_utc:
            continue
        rows.append({
            "id": f"dol-ui-{local_date:%Y%m%d}",
            "title": "Unemployment Insurance Weekly Claims",
            "date": local_date.isoformat(),
            "time": release_time,
            "basis": "DOL_ETA_WEEKLY_RULE_WITH_HOLIDAY_EXCEPTIONS",
            "exception": bool(exception),
        })
    if not rows:
        raise ValueError("no future DOL weekly claims event inside frozen horizon")
    return parse_official_rows(rows, "DOL_UI")


def reconcile_authoritative(events: list[Event]) -> tuple[bool, list[str]]:
    """Fail closed when two authoritative snapshots disagree on the same event ID."""
    seen: dict[tuple[str, str], Event] = {}
    conflicts: list[str] = []
    for event in events:
        key = (event.source, event.source_id)
        previous = seen.get(key)
        if previous and (previous.scheduled_utc != event.scheduled_utc or previous.status != event.status):
            conflicts.append(f"{event.source}:{event.source_id}")
        seen[key] = event
    return not conflicts, sorted(set(conflicts))


def fred_date_cross_check(event: Event, fred_release_date: str | None) -> bool:
    """FRED can corroborate the date only; it is never used as the event clock."""
    if fred_release_date is None:
        return True
    return event.scheduled_utc.astimezone(verified_zone(EASTERN)).date().isoformat() == fred_release_date


def interval(event: Event) -> tuple[datetime, datetime]:
    pre, post = WINDOWS[event.tier]
    return event.scheduled_utc - timedelta(minutes=pre), event.scheduled_utc + timedelta(minutes=post)


def guard_state(now: datetime, events: list[Event], *, source_healthy: bool,
                shock_locked: bool, normalized: bool = True) -> str:
    now = now.astimezone(UTC)
    if not source_healthy:
        return "SOURCE_UNHEALTHY"
    if shock_locked:
        return "SHOCK_LOCK"
    for event in events:
        if event.status in {"TENTATIVE", "SUSPENDED"}:
            return "SOURCE_UNHEALTHY"
        if event.status == "CANCELLED":
            continue
        start, end = interval(event)
        if start <= now < event.scheduled_utc:
            return "PRE_LOCK"
        if event.scheduled_utc <= now < end:
            return "EVENT_ACTIVE" if now == event.scheduled_utc else "POST_LOCK"
        if now >= end and not normalized:
            return "NORMALIZATION_PENDING"
    return "HEALTHY"


def entry_allowed(now: datetime, events: list[Event], *, source_healthy: bool,
                  shock_locked: bool, normalized: bool, submission_latency: timedelta) -> bool:
    if guard_state(now, events, source_healthy=source_healthy,
                   shock_locked=shock_locked, normalized=normalized) != "HEALTHY":
        return False
    crossing = now.astimezone(UTC) + submission_latency
    return all(event.status == "CANCELLED" or crossing < interval(event)[0] or now >= interval(event)[1]
               for event in events)
