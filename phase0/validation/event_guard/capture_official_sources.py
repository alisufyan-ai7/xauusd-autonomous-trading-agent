"""Read-only official schedule capture utility for controlled VPS evidence runs.

This program performs HTTPS GETs only against the frozen official-source
registry.  It has no broker, order, model, or messaging integrations.  Captured
bodies are private evidence and must not be committed or published.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

from source_conformance import (
    AcquisitionRecord, POLICIES, ZERO_HASH, assess_snapshot, make_record,
    verify_record_chain,
)

UTC = timezone.utc
DEFAULT_SOURCES = ("BLS_ICS", "BEA_JSON", "FED_CALENDAR", "CENSUS_WATCH", "DOL_UI")
FED_HORIZON_MONTHS = 4


def _load_records(path: Path) -> list[AcquisitionRecord]:
    if not path.exists():
        return []
    records: list[AcquisitionRecord] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(AcquisitionRecord(**json.loads(line)))
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid manifest line {number}") from exc
    healthy, broken = verify_record_chain(records)
    if not healthy:
        raise ValueError(f"manifest hash chain invalid at indexes {broken}")
    return records


def _latest_for(records: list[AcquisitionRecord], source: str,
                url: str) -> AcquisitionRecord | None:
    return next((record for record in reversed(records)
                 if record.source == source and record.url == url), None)


def _target_urls(source: str, now: datetime) -> tuple[str, ...]:
    if source != "FED_CALENDAR":
        return POLICIES[source].urls
    urls: list[str] = []
    for offset in range(FED_HORIZON_MONTHS):
        absolute_month = now.year * 12 + now.month - 1 + offset
        year, zero_based_month = divmod(absolute_month, 12)
        month = zero_based_month + 1
        month_name = datetime(year, month, 1).strftime("%B").lower()
        urls.append(
            f"https://www.federalreserve.gov/newsevents/{year:04d}-{month_name}.htm"
        )
    return tuple(urls)


def _request(url: str, cached: AcquisitionRecord | None) -> urllib.request.Request:
    headers = {
        "Accept": "text/calendar, application/json, text/html, application/xhtml+xml, */*;q=0.1",
        "User-Agent": "XAUUSD-Gate0-ReadOnly-EventGuard-Evidence/0.1",
    }
    if cached and cached.etag:
        headers["If-None-Match"] = cached.etag
    if cached and cached.last_modified:
        headers["If-Modified-Since"] = cached.last_modified
    return urllib.request.Request(url, headers=headers, method="GET")


def _fetch(source: str, url: str, cached: AcquisitionRecord | None, previous_hash: str,
           timeout_seconds: float) -> tuple[AcquisitionRecord, bytes]:
    policy = POLICIES[source]
    if source == "FRED_CROSSCHECK":
        raise ValueError("FRED requires separate optional configuration and never controls locks")
    request = _request(url, cached)
    try:
        response = urllib.request.urlopen(request, timeout=timeout_seconds)
        status = response.status
        content_type = response.headers.get("Content-Type", "")
        body = response.read(policy.max_bytes + 1)
        headers = response.headers
    except urllib.error.HTTPError as exc:
        if exc.code != 304:
            raise
        status = 304
        content_type = exc.headers.get("Content-Type", "")
        body = b""
        headers = exc.headers
    if len(body) > policy.max_bytes:
        raise ValueError(f"{source} payload exceeds frozen size limit")
    record = make_record(
        source=source,
        url=url,
        retrieved_utc=datetime.now(UTC),
        http_status=status,
        content_type=content_type,
        body=body,
        etag=headers.get("ETag", ""),
        last_modified=headers.get("Last-Modified", ""),
        previous_record_sha256=previous_hash,
        cached_record=cached if status == 304 else None,
    )
    healthy, reasons = assess_snapshot(
        record, body, datetime.now(UTC), cached if status == 304 else None
    )
    if not healthy:
        raise ValueError(f"{source} snapshot rejected: {','.join(reasons)}")
    return record, body


def capture(output: Path, sources: list[str], timeout_seconds: float) -> dict:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = output / "acquisition_records.jsonl"
    records = _load_records(manifest)
    previous_hash = records[-1].record_sha256 if records else ZERO_HASH
    run: list[dict] = []
    capture_started = datetime.now(UTC)
    targets: list[tuple[str, str]] = []
    for source in sources:
        if source not in DEFAULT_SOURCES:
            raise ValueError(f"source is not enabled for capture: {source}")
        targets.extend((source, url) for url in _target_urls(source, capture_started))
    for source, url in targets:
        cached = _latest_for(records, source, url)
        try:
            record, body = _fetch(source, url, cached, previous_hash, timeout_seconds)
            if record.http_status == 200:
                body_dir = output / source
                body_dir.mkdir(parents=True, exist_ok=True)
                destination = body_dir / f"{record.body_sha256}.raw"
                if not destination.exists():
                    destination.write_bytes(body)
            with manifest.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(asdict(record), sort_keys=True, separators=(",", ":")) + "\n")
            records.append(record)
            previous_hash = record.record_sha256
            run.append({"source": source, "url": url, "status": "CAPTURED", "http_status": record.http_status,
                        "record_sha256": record.record_sha256})
        except Exception as exc:  # evidence runner records and continues across independent sources
            run.append({"source": source, "url": url, "status": "REJECTED", "reason": str(exc)})
    return {
        "status": "PASS" if all(item["status"] == "CAPTURED" for item in run) else "FAIL_CLOSED",
        "captured_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "sources": run,
        "claim_limit": "Read-only acquisition evidence only; not trading authorization.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path,
                        help="private local evidence directory; never commit or publish")
    parser.add_argument("--source", action="append", choices=DEFAULT_SOURCES)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    args = parser.parse_args(argv)
    try:
        result = capture(args.output, args.source or list(DEFAULT_SOURCES), args.timeout_seconds)
    except Exception as exc:
        result = {"status": "FAIL_CLOSED", "reason": str(exc)}
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
