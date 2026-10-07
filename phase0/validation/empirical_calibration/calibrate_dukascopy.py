"""Generate training/validation-only empirical candidates from a sealed M15 corpus."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from statistics import median

from calibration_workflow import CalibrationPlan, Observation, calibrate, rows_hash


UTC = timezone.utc
TRAIN_END = datetime(2023, 12, 31, 23, 45, tzinfo=UTC)
VALIDATION_START = datetime(2024, 1, 8, tzinfo=UTC)
VALIDATION_END = datetime(2024, 12, 31, 23, 45, tzinfo=UTC)


def parse_stamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def session(stamp: datetime) -> str:
    if stamp.hour < 8:
        return "ASIA"
    if stamp.hour < 13:
        return "LONDON"
    if stamp.hour < 21:
        return "LONDON_NY"
    return "ROLLOVER"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_metrics(path: Path):
    metrics = []
    history_return, history_range, history_spread = [], [], []
    previous_mid = None
    previous_time = None
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            stamp = parse_stamp(row["timestamp_utc"])
            if stamp > VALIDATION_END:
                break
            if not (stamp <= TRAIN_END or stamp >= VALIDATION_START):
                continue
            bid_open, bid_high, bid_low, bid_close = (Decimal(row[f"{name}_bid"])
                for name in ("open", "high", "low", "close"))
            ask_open, ask_high, ask_low, ask_close = (Decimal(row[f"{name}_ask"])
                for name in ("open", "high", "low", "close"))
            mid_open = (bid_open + ask_open) / 2
            mid_high = (bid_high + ask_high) / 2
            mid_low = (bid_low + ask_low) / 2
            mid_close = (bid_close + ask_close) / 2
            spread = float(max(ask_open - bid_open, ask_close - bid_close) * 100)
            absolute_return = (float(abs(mid_close - previous_mid) / previous_mid * 10_000)
                               if previous_mid else 0.0)
            range_bps = float((mid_high - mid_low) / mid_close * 10_000)
            gap = float(abs(mid_open - previous_mid) * 100) if previous_mid else 0.0
            quote_gap_ms = ((stamp - previous_time).total_seconds() * 1000 if previous_time else 900_000)
            if len(history_return) >= 96:
                metrics.append({
                    "stamp": stamp, "partition": "TRAIN" if stamp <= TRAIN_END else "VALIDATION",
                    "session": session(stamp), "spread": spread,
                    "spread_base": max(median(history_spread[-96:]), 0.01),
                    "return": absolute_return, "return_base": max(median(history_return[-96:]), 0.001),
                    "range": range_bps, "range_base": max(median(history_range[-96:]), 0.001),
                    "gap": gap, "quote_gap_ms": quote_gap_ms,
                    "slippage": max(absolute_return * float(mid_close) / 10_000 * 100, gap),
                    "cost": float(ask_close - bid_close),
                })
            history_spread.append(spread)
            history_return.append(absolute_return)
            history_range.append(range_bps)
            previous_mid, previous_time = mid_close, stamp
    return metrics


def observations(metrics):
    output = []
    event_id = None
    normal_streak = 0
    event_number = 0
    for item in metrics:
        if item["quote_gap_ms"] > 900_000:
            event_id, normal_streak = None, 0
        ratio = max(item["spread"] / item["spread_base"], item["return"] / item["return_base"],
                    item["range"] / item["range_base"])
        if item["partition"] != "TRAIN":
            phase, row_event = "NORMAL", None
        elif event_id is None and ratio >= 3.0:
            event_number += 1
            event_id = f"shock-{event_number:06d}"
            phase, row_event, normal_streak = "EVENT", event_id, 0
        elif event_id is not None:
            phase, row_event = "POST_EVENT", event_id
            normal_streak = normal_streak + 1 if ratio <= 1.5 else 0
            if normal_streak >= 3:
                event_id, normal_streak = None, 0
        else:
            phase, row_event = "NORMAL", None
        output.append(Observation(
            observed_utc=item["stamp"], partition=item["partition"], session=item["session"],
            event_phase=phase, event_id=row_event, spread_points=item["spread"],
            spread_baseline_points=item["spread_base"], adverse_latency_move_points=item["slippage"],
            gap_points=item["gap"], absolute_return_bps=item["return"],
            return_baseline_bps=item["return_base"], range_bps=item["range"],
            range_baseline_bps=item["range_base"], quote_gap_ms=item["quote_gap_ms"],
            tick_age_ms=900_000, round_trip_cost_usd=item["cost"],
        ))
    return tuple(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.private_root.resolve()
    bundle = json.loads((root / "manifests" / "multiframe_bundle.json").read_text())
    rows = observations(load_metrics(root / "derived" / "xauusd_m15_bid_ask.csv"))
    plan = CalibrationPlan(
        bundle_root_sha256=bundle["bundle_root_sha256"], derived_dataset_sha256=rows_hash(rows),
        rights_status="ADMITTED", frozen_utc=datetime.now(UTC), train_end_utc=TRAIN_END,
        holdout_status="SEALED_UNVIEWED", minimum_rows_per_session=1000,
        minimum_post_event_rows=100, minimum_complete_events=20,
        quantile_probability=.995, normalization_ratio_limit=1.5,
        consecutive_normal_rows=3, max_post_event_gap_seconds=900,
        code_sha256=sha(Path(__file__).read_bytes()), split_map_sha256=bundle["split_map_sha256"],
    )
    result = calibrate(plan, rows)
    report = {
        "schema_version": "dukascopy-empirical-calibration-1.0",
        "status": result.status, "reason_codes": result.reason_codes,
        "training_rows": result.training_rows, "validation_rows": result.validation_rows,
        "complete_post_events": result.complete_post_events,
        "candidate": asdict(result.candidate) if result.candidate else None,
        "bundle_root_sha256": bundle["bundle_root_sha256"],
        "derived_dataset_sha256": plan.derived_dataset_sha256,
        "split_map_sha256": bundle["split_map_sha256"],
        "holdout_exposed": False,
        "slippage_claim_limit": "NON_TRADING_ADVERSE_M15_MOVE_PROXY; NOT EXECUTION SLIPPAGE",
        "external_python_trading": "DISABLED", "trading_authorized": False,
    }
    report["report_sha256"] = sha(canonical(report))
    target = root / "calibration" / "empirical_calibration_report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
