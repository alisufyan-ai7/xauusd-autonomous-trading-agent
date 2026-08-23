"""Offline normalization of a private Event Guard acquisition directory.

No network, broker, model, credential, messaging, or trading API is imported.
Raw response bodies stay in the operator-selected private directory; the report
contains only normalized official events, source status, and evidence hashes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from capture_official_sources import _latest_for, _load_records, _target_urls
from event_guard_oracle import (
    Event, parse_bea_json, parse_dol_ui_schedule_html, parse_fed_monthly_html, parse_ics,
    reconcile_authoritative,
)
from source_conformance import POLICIES, assess_snapshot, coverage_inventory

UTC = timezone.utc
NORMALIZED_REPORT = "normalized_event_guard.json"


def _raw_body(output: Path, record) -> bytes:
    path = output / record.source / f"{record.body_sha256}.raw"
    if not path.is_file():
        raise ValueError(f"private body missing for {record.source}:{record.body_sha256}")
    body = path.read_bytes()
    if len(body) != record.byte_count or hashlib.sha256(body).hexdigest() != record.body_sha256:
        raise ValueError(f"private body hash/size mismatch for {record.source}")
    return body


def _event_record(event: Event) -> dict:
    return {
        "source": event.source,
        "source_id": event.source_id,
        "taxonomy": event.taxonomy,
        "tier": event.tier,
        "scheduled_utc": event.scheduled_utc.isoformat().replace("+00:00", "Z"),
        "status": event.status,
        "payload_sha256": event.payload_sha256,
    }


def normalize(output: Path, now: datetime) -> dict:
    output = output.resolve()
    records = _load_records(output / "acquisition_records.jsonl")
    by_digest = {record.record_sha256: record for record in records}
    source_status: dict[str, dict] = {}
    events: list[Event] = []
    healthy_sources: set[str] = set()

    for source in ("BLS_ICS", "BEA_JSON", "FED_CALENDAR", "DOL_UI", "CENSUS_WATCH"):
        target_results: list[dict] = []
        source_events: list[Event] = []
        for url in _target_urls(source, now):
            record = _latest_for(records, source, url)
            if record is None:
                target_results.append({"url": url, "status": "MISSING"})
                continue
            try:
                body = _raw_body(output, record)
                cached = by_digest.get(record.cache_record_sha256) if record.http_status == 304 else None
                healthy, reasons = assess_snapshot(
                    record, b"" if record.http_status == 304 else body, now, cached
                )
                if not healthy:
                    raise ValueError(",".join(reasons))
                text = body.decode("utf-8", errors="strict")
                if source == "BLS_ICS":
                    source_events.extend(parse_ics(text, source))
                elif source == "BEA_JSON":
                    source_events.extend(parse_bea_json(text))
                elif source == "FED_CALENDAR":
                    source_events.extend(parse_fed_monthly_html(text))
                elif source == "DOL_UI":
                    source_events.extend(parse_dol_ui_schedule_html(text, now))
                target_results.append({
                    "url": url,
                    "status": "NORMALIZED",
                    "record_sha256": record.record_sha256,
                    "body_sha256": record.body_sha256,
                })
            except Exception as exc:
                target_results.append({"url": url, "status": "REJECTED", "reason": str(exc)})
        if target_results and all(item["status"] == "NORMALIZED" for item in target_results):
            healthy_sources.add(source)
            events.extend(source_events)
            source_state = "HEALTHY"
        else:
            source_state = "SOURCE_UNHEALTHY"
        source_status[source] = {"status": source_state, "targets": target_results}

    reconciliation_ok, conflicts = reconcile_authoritative(events)
    coverage_ok, coverage = coverage_inventory(now, events, healthy_sources)
    future_events = sorted(
        (event for event in events if event.scheduled_utc >= now.astimezone(UTC)),
        key=lambda event: (event.scheduled_utc, event.source, event.source_id),
    )
    all_candidate_sources_healthy = all(
        source_status[source]["status"] == "HEALTHY"
        for source in ("BLS_ICS", "BEA_JSON", "FED_CALENDAR", "DOL_UI")
    )
    status = "PASS" if all_candidate_sources_healthy and reconciliation_ok and coverage_ok else "FAIL_CLOSED"
    return {
        "schema_version": "event-guard-normalized-1.0",
        "status": status,
        "normalized_utc": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "manifest_records": len(records),
        "manifest_final_record_sha256": records[-1].record_sha256 if records else "",
        "source_status": source_status,
        "reconciliation": {"status": "PASS" if reconciliation_ok else "FAIL", "conflicts": conflicts},
        "coverage": coverage,
        "future_events": [_event_record(event) for event in future_events],
        "claim_limit": "Private read-only normalization evidence only; not trading authorization.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path,
                        help="existing private capture directory; never commit or publish")
    args = parser.parse_args(argv)
    try:
        result = normalize(args.output, datetime.now(UTC))
        destination = args.output.resolve() / NORMALIZED_REPORT
        destination.write_text(
            json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    except Exception as exc:
        result = {"status": "FAIL_CLOSED", "reason": str(exc)}
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
