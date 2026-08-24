"""Authorized, GET-only Dukascopy XAUUSD historical-data acquisition.

The utility preserves official response bytes outside the repository, seals
their hashes, and deterministically derives UTC M15/H1/H4 bid/ask bars.  It has
no MetaTrader, broker, model, messaging, process-control, or trading capability.
"""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCHEMA_VERSION = "dukascopy-xauusd-seal-1.0"
BASE = "https://jetta.dukascopy.com/v1"
INSTRUMENT_URI = f"{BASE}/instruments/XAU-USD"
START = date(2020, 1, 1)
END = date(2026, 6, 29)  # 2026-06-30 was inspected during endpoint discovery and is excluded.
SIDES = ("BID", "ASK")
FRAMES = {"M15": 900, "H1": 3600, "H4": 14400}
CSV_FIELDS = (
    "timestamp_utc", "receipt_utc",
    "open_bid", "high_bid", "low_bid", "close_bid",
    "open_ask", "high_ask", "low_ask", "close_ask", "tick_volume",
)
SPLIT = {
    "train_start_utc": "2020-01-01T00:00:00Z",
    "train_end_utc": "2023-12-31T23:45:00Z",
    "validation_start_utc": "2024-01-08T00:00:00Z",
    "validation_end_utc": "2024-12-31T23:45:00Z",
    "embargo_start_utc": "2025-01-01T00:00:00Z",
    "embargo_end_utc": "2025-01-08T00:00:00Z",
    "holdout_start_utc": "2025-01-09T00:00:00Z",
    "holdout_end_utc": "2026-06-29T23:45:00Z",
    "purge_seconds": 604800,
    "embargo_seconds": 604800,
    "sealed": True,
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def atomic_write(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path: Path) -> Any:
    with path.open("rb") as stream:
        return json.load(stream)


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode() + b"\n")


def days() -> Iterable[date]:
    current = START
    while current <= END:
        yield current
        current += timedelta(days=1)


def endpoint(side: str, day: date) -> str:
    return f"{BASE}/candles/minute/XAU-USD/{side}/{day.year}/{day.month}/{day.day}"


def raw_path(root: Path, side: str, day: date) -> Path:
    return root / "raw" / side.lower() / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.day:02d}.json"


def get(uri: str, attempts: int = 6) -> bytes:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(uri, method="GET", headers={"User-Agent": "xauusd-gate0-personal-research/1.0"})
            with urlopen(request, timeout=60) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}")
                return response.read()
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(min(2 ** attempt, 20))
    raise RuntimeError(f"GET failed after {attempts} attempts: {uri}: {last}")


def validate_payload(body: bytes, day: date) -> dict[str, Any]:
    value = json.loads(body)
    required = {"timestamp", "multiplier", "open", "high", "low", "close",
                "shift", "times", "opens", "highs", "lows", "closes", "volumes"}
    if set(value) != required:
        raise ValueError(f"unexpected response schema on {day}: {sorted(value)}")
    lengths = {len(value[key]) for key in ("times", "opens", "highs", "lows", "closes", "volumes")}
    if len(lengths) != 1 or value["shift"] != 60000 or value["multiplier"] <= 0:
        raise ValueError(f"invalid response arrays on {day}")
    expected = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1000)
    if value["timestamp"] != expected:
        raise ValueError(f"response day mismatch on {day}")
    return value


def register(root: Path, owner_attested_utc: str) -> None:
    script_hash = digest_file(Path(__file__))
    attestation = {
        "schema_version": "provider-rights-owner-attestation-1.0",
        "provider": "Dukascopy",
        "owner_attested_utc": owner_attested_utc,
        "evidence_type": "OWNER_ATTESTED_WRITTEN_PROVIDER_CONFIRMATION",
        "scope": {
            "project": "personal non-commercial XAUUSD research project",
            "download": True, "retention": True, "hashing_and_sealing": True,
            "deterministic_derivation": True, "replay_and_backtesting": True,
            "calibration": True, "derived_analytical_results": True,
            "internal_audit_retention": True,
            "redistribution": False, "resale": False, "commercial_data_service": False,
            "paid_subscription": False, "paid_trial": False, "unrelated_use": False,
        },
        "provenance_note": (
            "Owner confirms receipt of written Dukascopy permission. The original email is not "
            "currently available; it may be added later as supporting evidence but is not a prerequisite."
        ),
    }
    attestation["attestation_sha256"] = digest_bytes(canonical_bytes(attestation))
    split_hash = digest_bytes(canonical_bytes(SPLIT))
    plan = {
        "schema_version": "xauusd-acquisition-plan-1.0",
        "registered_utc": utc_now(),
        "provider": {
            "name": "Dukascopy", "legal_entity": "Dukascopy Bank SA",
            "source_uri": "https://widgets.dukascopy.com/en/historical-data-export",
            "instrument": "XAUUSD", "instrument_semantics": "Dukascopy XAU/USD bid/ask spot-metal bars",
            "timezone": "UTC", "price_content": "BAR_BID_ASK",
            "entitlement_status": "DOCUMENTED_ACTIVE",
            "terms_identifier": "owner-attested-written-provider-confirmation-2026-08-24",
        },
        "rights": {
            "review_status": "APPROVED_FOR_INTERNAL_EVALUATION",
            "terms_uri": "https://www.dukascopy.com/swiss/english/legal/",
            "terms_effective_date": owner_attested_utc[:10],
            "terms_artifact": "evidence/dukascopy_owner_attestation.json",
            "terms_sha256": digest_bytes(json.dumps(attestation, sort_keys=True, indent=2).encode() + b"\n"),
            "reviewed_utc": owner_attested_utc, "reviewed_by_role": "PROJECT_OWNER",
            "automated_use": True, "local_retention": True, "derived_data": True,
            "historical_replay": True, "internal_audit_retention": True,
            "redistribution": False, "termination_retention": "EXPLICITLY_PERMITTED",
        },
        "acquisition": {
            "method": "PROVIDER_API_READ_ONLY", "http_method": "GET",
            "start_utc": "2020-01-01T00:00:00Z", "end_utc": "2026-06-30T00:00:00Z",
            "output_outside_repository": True, "raw_bytes_preserved": True,
            "immutable_after_seal": True, "credentials_in_manifest": False,
        },
        "timeframes": {name: {"period_seconds": seconds,
            "minimum_rows": {"H4": 300, "H1": 500, "M15": 1000}[name],
            "derivation": "DETERMINISTIC_FROM_ADMITTED_SOURCE"} for name, seconds in FRAMES.items()},
        "split": SPLIT, "split_map_sha256": split_hash,
        "registration": {
            "holdout_status": "SEALED_UNVIEWED", "results_viewed": False, "random_split": False,
            "code_sha256": script_hash, "config_sha256": digest_bytes(canonical_bytes({"start": str(START), "end": str(END), "frames": FRAMES})),
            "acceptance_rules_sha256": digest_bytes(canonical_bytes({"split": SPLIT, "frames": FRAMES, "schema": CSV_FIELDS})),
        },
        "transformations": {
            "raw_bytes_immutable": True, "deterministic": True, "bid_ask_preserved": True,
            "forming_bars_excluded": True, "code_sha256": script_hash,
        },
        "contamination_exclusions": [{
            "date_utc": "2026-06-30", "reason": "API endpoint discovery sample inspected before registration",
            "excluded_from_all_partitions": True,
        }],
    }
    plan["plan_sha256"] = digest_bytes(canonical_bytes(plan))
    evidence = root / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    write_json(evidence / "dukascopy_owner_attestation.json", attestation)
    write_json(root / "acquisition_plan.json", plan)
    print(json.dumps({"status": "REGISTERED", "plan_sha256": plan["plan_sha256"],
                      "split_map_sha256": split_hash, "code_sha256": script_hash}, sort_keys=True))


def acquire_one(root: Path, side: str, day: date) -> dict[str, Any]:
    path = raw_path(root, side, day)
    uri = endpoint(side, day)
    if path.exists():
        body = path.read_bytes()
    else:
        body = get(uri)
        validate_payload(body, day)
        atomic_write(path, body)
    value = validate_payload(body, day)
    return {"path": str(path.relative_to(root)), "source_uri": uri, "side": side,
            "date_utc": str(day), "bytes": len(body), "sha256": digest_bytes(body),
            "rows": len(value["times"])}


def acquire(root: Path, workers: int) -> None:
    if not (root / "acquisition_plan.json").exists():
        raise RuntimeError("register before acquisition")
    instrument_path = root / "raw" / "instrument" / "XAU-USD.json"
    instrument_body = instrument_path.read_bytes() if instrument_path.exists() else get(INSTRUMENT_URI)
    instrument = json.loads(instrument_body)
    if instrument.get("code") != "XAU-USD" or instrument.get("name") != "XAU/USD":
        raise ValueError("instrument identity mismatch")
    if not instrument_path.exists():
        atomic_write(instrument_path, instrument_body)
    tasks = [(side, day) for day in days() for side in SIDES]
    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(acquire_one, root, side, day): (side, day) for side, day in tasks}
        for index, future in enumerate(as_completed(future_map), 1):
            records.append(future.result())
            if index % 250 == 0:
                print(json.dumps({"downloaded_or_verified": index, "total": len(tasks)}), flush=True)
    records.sort(key=lambda row: (row["date_utc"], row["side"]))
    manifest = {
        "schema_version": SCHEMA_VERSION, "sealed_at_utc": utc_now(),
        "instrument": {"path": str(instrument_path.relative_to(root)), "bytes": len(instrument_body),
                       "sha256": digest_bytes(instrument_body), "source_uri": INSTRUMENT_URI},
        "files": records,
    }
    manifest["raw_inventory_root_sha256"] = digest_bytes(canonical_bytes([
        [row["path"], row["sha256"], row["bytes"], row["rows"]] for row in records
    ]))
    write_json(root / "raw_inventory.json", manifest)
    print(json.dumps({"status": "RAW_SEALED", "files": len(records),
                      "bytes": sum(row["bytes"] for row in records),
                      "raw_inventory_root_sha256": manifest["raw_inventory_root_sha256"]}, sort_keys=True))


@dataclass
class Minute:
    stamp_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


def decode(value: dict[str, Any]) -> list[Minute]:
    count = len(value["times"])
    if count == 0:
        return []
    stamp = int(value["timestamp"])
    scale = Decimal(str(value["multiplier"]))
    fields = {name: Decimal(str(value[name])) for name in ("open", "high", "low", "close")}
    output: list[Minute] = []
    for index in range(count):
        stamp += int(value["times"][index]) * int(value["shift"])
        for name in fields:
            fields[name] += Decimal(int(value[name + "s"][index])) * scale
        volume = int((Decimal(str(value["volumes"][index])) * Decimal(1_000_000)).to_integral_value())
        output.append(Minute(stamp, fields["open"], fields["high"], fields["low"], fields["close"], volume))
    return output


def fmt(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.001")), "f")


def stamp(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def aggregate(bid: list[Minute], ask: list[Minute], seconds: int, receipt: str) -> list[dict[str, str]]:
    bid_map = {row.stamp_ms: row for row in bid}
    ask_map = {row.stamp_ms: row for row in ask}
    groups: dict[int, list[tuple[Minute, Minute]]] = {}
    period_ms = seconds * 1000
    mismatched_buckets = {stamp // period_ms * period_ms
                          for stamp in set(bid_map) ^ set(ask_map)}
    for value in sorted(set(bid_map) & set(ask_map)):
        bucket = value // period_ms * period_ms
        if bucket not in mismatched_buckets:
            groups.setdefault(bucket, []).append((bid_map[value], ask_map[value]))
    rows = []
    for bucket in sorted(groups):
        pairs = groups[bucket]
        left = [pair[0] for pair in pairs]
        right = [pair[1] for pair in pairs]
        row = {"timestamp_utc": stamp(bucket), "receipt_utc": receipt,
               "open_bid": fmt(left[0].open), "high_bid": fmt(max(x.high for x in left)),
               "low_bid": fmt(min(x.low for x in left)), "close_bid": fmt(left[-1].close),
               "open_ask": fmt(right[0].open), "high_ask": fmt(max(x.high for x in right)),
               "low_ask": fmt(min(x.low for x in right)), "close_ask": fmt(right[-1].close),
               "tick_volume": str(max(sum(x.volume for x in left), sum(x.volume for x in right)))}
        if any(Decimal(row[f"{kind}_ask"]) < Decimal(row[f"{kind}_bid"])
               for kind in ("open", "high", "low", "close")):
            raise ValueError(f"crossed derived bar at {row['timestamp_utc']}")
        rows.append(row)
    return rows


def derive(root: Path) -> None:
    inventory = read_json(root / "raw_inventory.json")
    receipt = inventory["sealed_at_utc"]
    derived = root / "derived"
    derived.mkdir(parents=True, exist_ok=True)
    streams: dict[str, tuple[Any, csv.DictWriter]] = {}
    counts = {name: 0 for name in FRAMES}
    ranges: dict[str, list[str | None]] = {name: [None, None] for name in FRAMES}
    gaps: dict[str, list[dict[str, Any]]] = {name: [] for name in FRAMES}
    previous_ms: dict[str, int | None] = {name: None for name in FRAMES}
    mismatch_buckets: dict[str, set[int]] = {name: set() for name in FRAMES}
    mismatch_records: list[dict[str, Any]] = []
    try:
        for name in FRAMES:
            stream = (derived / f"xauusd_{name.lower()}_bid_ask.csv").open("w", encoding="utf-8", newline="")
            writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
            writer.writeheader()
            streams[name] = (stream, writer)
        for index, day in enumerate(days(), 1):
            bid = decode(read_json(raw_path(root, "BID", day)))
            ask = decode(read_json(raw_path(root, "ASK", day)))
            bid_stamps = {row.stamp_ms for row in bid}
            ask_stamps = {row.stamp_ms for row in ask}
            unmatched = sorted(bid_stamps ^ ask_stamps)
            if unmatched:
                mismatch_records.append({
                    "date_utc": str(day),
                    "timestamps_utc": [stamp(value) for value in unmatched],
                    "missing_bid": [stamp(value) for value in sorted(ask_stamps - bid_stamps)],
                    "missing_ask": [stamp(value) for value in sorted(bid_stamps - ask_stamps)],
                    "bid_raw_sha256": digest_file(raw_path(root, "BID", day)),
                    "ask_raw_sha256": digest_file(raw_path(root, "ASK", day)),
                })
                for name, seconds in FRAMES.items():
                    period_ms = seconds * 1000
                    mismatch_buckets[name].update(value // period_ms * period_ms for value in unmatched)
            for name, seconds in FRAMES.items():
                for row in aggregate(bid, ask, seconds, receipt):
                    current = int(datetime.fromisoformat(row["timestamp_utc"].replace("Z", "+00:00")).timestamp() * 1000)
                    prior = previous_ms[name]
                    if prior is not None and current - prior != seconds * 1000:
                        delta = current - prior
                        mismatch = any(prior < bucket < current for bucket in mismatch_buckets[name])
                        gaps[name].append({
                            "after_utc": stamp(prior), "before_utc": stamp(current),
                            "reason": ("PROVIDER_SIDE_MISMATCH" if mismatch else
                                       "HOLIDAY_CLOSED" if delta >= 24 * 3600 * 1000 else "SESSION_CLOSED"),
                            "source_uri": INSTRUMENT_URI,
                            "evidence_artifact": "evidence/dukascopy_instrument_XAU-USD.json",
                            "evidence_sha256": inventory["instrument"]["sha256"],
                        })
                    previous_ms[name] = current
                    streams[name][1].writerow(row)
                    counts[name] += 1
                    ranges[name][0] = ranges[name][0] or row["timestamp_utc"]
                    ranges[name][1] = row["timestamp_utc"]
            if index % 250 == 0:
                print(json.dumps({"derived_days": index, "total_days": (END - START).days + 1}), flush=True)
    finally:
        for stream, _ in streams.values():
            stream.close()
    evidence_path = root / "evidence" / "dukascopy_instrument_XAU-USD.json"
    atomic_write(evidence_path, (root / inventory["instrument"]["path"]).read_bytes())
    mismatch_path = root / "evidence" / "dukascopy_bid_ask_mismatches.json"
    write_json(mismatch_path, {"schema_version": "dukascopy-side-mismatch-evidence-1.0",
                               "records": mismatch_records})
    mismatch_hash = digest_file(mismatch_path)
    for frame_gaps in gaps.values():
        for gap in frame_gaps:
            if gap["reason"] == "PROVIDER_SIDE_MISMATCH":
                gap["evidence_artifact"] = "evidence/dukascopy_bid_ask_mismatches.json"
                gap["evidence_sha256"] = mismatch_hash
    attestation_path = root / "evidence" / "dukascopy_owner_attestation.json"
    plan = read_json(root / "acquisition_plan.json")
    frame_manifests = {}
    descriptors = {}
    for name, seconds in FRAMES.items():
        path = derived / f"xauusd_{name.lower()}_bid_ask.csv"
        descriptor = {"path": f"data/{path.name}", "sha256": digest_file(path), "bytes": path.stat().st_size,
                      "row_count": counts[name], "start_utc": ranges[name][0], "end_utc": ranges[name][1]}
        descriptors[name] = descriptor
        manifest = {
            "schema_version": "replay-admission-1.0", "dataset_id": f"DUKASCOPY-XAUUSD-{name}-20200101-20260629",
            "frozen_at_utc": utc_now(), "bar_period_seconds": seconds,
            "provenance": {"provider": "Dukascopy", "source_uri": "https://widgets.dukascopy.com/en/historical-data-export",
                "instrument": "XAUUSD", "instrument_semantics": "Dukascopy XAU/USD bid/ask spot-metal OHLC",
                "timezone": "UTC", "acquisition_method": "official Jetta HTTPS GET minute bars; deterministic UTC aggregation",
                "terms_identifier": plan["provider"]["terms_identifier"]},
            "rights": {"review_status": "APPROVED_FOR_INTERNAL_EVALUATION", "automated_use": True,
                "local_retention": True, "derived_data": True, "historical_replay": True,
                "internal_audit_retention": True, "redistribution": False, "reviewed_by": "PROJECT_OWNER",
                "reviewed_utc": plan["rights"]["reviewed_utc"], "terms_artifact": "evidence/dukascopy_owner_attestation.json",
                "terms_sha256": digest_file(attestation_path)},
            "registration": {"trial_id": "GATE0-DUKASCOPY-REGISTERED-20260824", "strategy_version": "1.0-rc1",
                "code_sha256": plan["registration"]["code_sha256"], "config_sha256": plan["registration"]["config_sha256"],
                "split_map_sha256": plan["split_map_sha256"], "acceptance_rule_version": "1.0-rc1",
                "registered_utc": plan["registered_utc"], "holdout_status": "SEALED", "results_viewed": False},
            "files": [descriptor], "authorized_gaps": gaps[name],
        }
        manifest["dataset_root_sha256"] = digest_bytes(canonical_bytes([[descriptor[key] for key in
            ("path", "sha256", "bytes", "row_count", "start_utc", "end_utc")]]))
        manifest["manifest_sha256"] = digest_bytes(canonical_bytes(manifest))
        frame_manifests[name] = manifest
        write_json(root / "manifests" / f"{name.lower()}_manifest.json", manifest)
    declared = {name: {"dataset_id": frame_manifests[name]["dataset_id"],
                       "dataset_root_sha256": frame_manifests[name]["dataset_root_sha256"]} for name in FRAMES}
    bundle = {"schema_version": "replay-multiframe-bundle-1.0", "bundle_id": "DUKASCOPY-XAUUSD-20200101-20260629",
              "frozen_at_utc": utc_now(), "timeframes": declared, "split": SPLIT,
              "split_map_sha256": plan["split_map_sha256"]}
    bundle["bundle_root_sha256"] = digest_bytes(canonical_bytes([[name, declared[name]["dataset_id"],
        declared[name]["dataset_root_sha256"]] for name in sorted(declared)]))
    bundle["bundle_manifest_sha256"] = digest_bytes(canonical_bytes(bundle))
    write_json(root / "manifests" / "multiframe_bundle.json", bundle)
    report = {"status": "DERIVED_AND_SEALED", "raw_inventory_root_sha256": inventory["raw_inventory_root_sha256"],
              "bundle_root_sha256": bundle["bundle_root_sha256"], "split_map_sha256": plan["split_map_sha256"],
              "timeframes": {name: {**descriptors[name], "authorized_gaps": len(gaps[name])} for name in FRAMES},
              "rights_attestation_sha256": digest_file(attestation_path), "instrument_evidence_sha256": digest_file(evidence_path),
              "bid_ask_mismatch_evidence_sha256": mismatch_hash,
              "contamination_exclusions": plan["contamination_exclusions"], "external_python_trading": "DISABLED",
              "trading_authorized": False}
    report["report_sha256"] = digest_bytes(canonical_bytes(report))
    write_json(root / "sealed_dataset_report.json", report)
    print(json.dumps(report, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("register", "acquire", "derive"))
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--owner-attested-utc", default="2026-08-24T00:00:00Z")
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    root = args.private_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if args.command == "register":
        register(root, args.owner_attested_utc)
    elif args.command == "acquire":
        acquire(root, max(1, min(args.workers, 24)))
    else:
        derive(root)


if __name__ == "__main__":
    main()
