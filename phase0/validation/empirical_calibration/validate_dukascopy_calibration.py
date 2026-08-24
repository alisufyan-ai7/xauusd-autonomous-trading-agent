"""Independent chronological validation of training-only Dukascopy candidates."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path

from calibrate_dukascopy import load_metrics


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def quantile(values, probability):
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, math.ceil(probability * len(ordered)) - 1))]


def validation_recoveries(rows):
    durations = []
    event_start = None
    normal_streak = 0
    for row in rows:
        if row["quote_gap_ms"] > 900_000:
            event_start, normal_streak = None, 0
        ratio = max(row["spread"] / row["spread_base"], row["return"] / row["return_base"],
                    row["range"] / row["range_base"])
        if event_start is None and ratio >= 3.0:
            event_start, normal_streak = row["stamp"], 0
        elif event_start is not None:
            normal_streak = normal_streak + 1 if ratio <= 1.5 else 0
            if normal_streak >= 3:
                durations.append(int((row["stamp"] - event_start).total_seconds()))
                event_start, normal_streak = None, 0
    return durations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.private_root.resolve()
    calibration_path = root / "calibration" / "empirical_calibration_report.json"
    calibration = json.loads(calibration_path.read_text())
    candidate = calibration["candidate"]
    metrics = [row for row in load_metrics(root / "derived" / "xauusd_m15_bid_ask.csv")
               if row["partition"] == "VALIDATION"]
    mappings = {
        "spread_points": "spread", "slippage_proxy_points": "slippage",
        "gap_points": "gap", "round_trip_cost_usd": "cost",
        "return_bps": "return", "range_bps": "range", "quote_gap_ms": "quote_gap_ms",
    }
    observed = {name: quantile([row[source] for row in metrics], .99)
                for name, source in mappings.items()}
    observed["tick_age_ms"] = 900_000
    recoveries = validation_recoveries(metrics)
    observed["post_event_normalization_seconds"] = quantile(recoveries, .99) if recoveries else None
    checks = {name: observed[name] is not None and observed[name] <= candidate[name]
              for name in observed}
    checks["minimum_validation_rows"] = len(metrics) >= 10_000
    checks["minimum_complete_validation_events"] = len(recoveries) >= 20
    status = "VALIDATED_FROZEN_FOR_GATE0_REPLAY" if all(checks.values()) else "FAIL_CLOSED"
    report = {
        "schema_version": "dukascopy-empirical-calibration-validation-1.0",
        "status": status, "candidate_artifact_sha256": candidate["artifact_sha256"],
        "bundle_root_sha256": calibration["bundle_root_sha256"],
        "derived_dataset_sha256": calibration["derived_dataset_sha256"],
        "validation_rows": len(metrics), "complete_validation_events": len(recoveries),
        "promotion_rule": "validation nearest-rank q0.99 must not exceed training q0.995 candidate",
        "observed_validation_q99": observed, "checks": checks,
        "frozen_replay_stress_constants": candidate if status.startswith("VALIDATED") else None,
        "claim_limit": "Historical non-trading replay stress; slippage is an adverse-price-move proxy, not execution slippage.",
        "holdout_exposed": False, "external_python_trading": "DISABLED", "trading_authorized": False,
    }
    report["report_sha256"] = sha(json.dumps(report, sort_keys=True, separators=(",", ":")).encode())
    target = root / "calibration" / "empirical_calibration_validation_report.json"
    target.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    if status == "FAIL_CLOSED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
