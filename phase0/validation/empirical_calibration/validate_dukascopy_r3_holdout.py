"""One-time untouched-holdout validation of the R3 frozen calibration artifact."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from statistics import median


UTC = timezone.utc
HOLDOUT_START = datetime(2026, 7, 7, 0, 15, tzinfo=UTC)
HOLDOUT_END = datetime(2026, 8, 21, 20, tzinfo=UTC)
FROZEN = {
    "spread_points": 257.6,
    "slippage_proxy_points": 2762.244878293765,
    "gap_points": 70.5,
    "round_trip_cost_usd": 1.934,
    "return_bps": 60.34808883662764,
    "range_bps": 91.89578551545637,
    "quote_gap_ms": 4500000.0,
    "tick_age_ms": 900000,
    "post_event_normalization_seconds": 40500,
    "slippage_basis": "NON_TRADING_ADVERSE_LATENCY_PROXY",
}


def quantile(values, probability):
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, math.ceil(probability * len(ordered)) - 1))]


def load(path: Path):
    rows = []
    returns, ranges, spreads = [], [], []
    previous_mid = previous_time = None
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            stamp = datetime.fromisoformat(row["timestamp_utc"].replace("Z", "+00:00"))
            bid_open, bid_high, bid_low, bid_close = (Decimal(row[f"{name}_bid"])
                for name in ("open", "high", "low", "close"))
            ask_open, ask_high, ask_low, ask_close = (Decimal(row[f"{name}_ask"])
                for name in ("open", "high", "low", "close"))
            mid_open, mid_high = (bid_open + ask_open) / 2, (bid_high + ask_high) / 2
            mid_low, mid_close = (bid_low + ask_low) / 2, (bid_close + ask_close) / 2
            spread = float(max(ask_open - bid_open, ask_close - bid_close) * 100)
            ret = float(abs(mid_close - previous_mid) / previous_mid * 10_000) if previous_mid else 0.0
            rng = float((mid_high - mid_low) / mid_close * 10_000)
            gap = float(abs(mid_open - previous_mid) * 100) if previous_mid else 0.0
            quote_gap = (stamp - previous_time).total_seconds() * 1000 if previous_time else 900_000
            if HOLDOUT_START <= stamp <= HOLDOUT_END and len(returns) >= 96:
                rows.append({"stamp": stamp, "spread": spread, "spread_base": max(median(spreads[-96:]), .01),
                    "return": ret, "return_base": max(median(returns[-96:]), .001),
                    "range": rng, "range_base": max(median(ranges[-96:]), .001),
                    "gap": gap, "quote_gap_ms": quote_gap,
                    "slippage": max(ret * float(mid_close) / 10_000 * 100, gap),
                    "cost": float(ask_close - bid_close)})
            spreads.append(spread); returns.append(ret); ranges.append(rng)
            previous_mid, previous_time = mid_close, stamp
    return rows


def recoveries(rows):
    values = []
    start = None
    streak = 0
    for row in rows:
        if row["quote_gap_ms"] > 900_000:
            start, streak = None, 0
        ratio = max(row["spread"] / row["spread_base"], row["return"] / row["return_base"],
                    row["range"] / row["range_base"])
        if start is None and ratio >= 3:
            start, streak = row["stamp"], 0
        elif start is not None:
            streak = streak + 1 if ratio <= 1.5 else 0
            if streak >= 3:
                values.append(int((row["stamp"] - start).total_seconds()))
                start, streak = None, 0
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.private_root.resolve()
    rows = load(root / "derived" / "xauusd_m15_bid_ask.csv")
    mapping = {"spread_points": "spread", "slippage_proxy_points": "slippage",
               "gap_points": "gap", "round_trip_cost_usd": "cost",
               "return_bps": "return", "range_bps": "range", "quote_gap_ms": "quote_gap_ms"}
    observed = {name: quantile([row[source] for row in rows], .99) for name, source in mapping.items()}
    observed["tick_age_ms"] = 900_000
    recovered = recoveries(rows)
    observed["post_event_normalization_seconds"] = quantile(recovered, .99) if recovered else None
    checks = {name: observed[name] is not None and observed[name] <= FROZEN[name] for name in observed}
    checks["minimum_holdout_rows"] = len(rows) >= 2500
    checks["minimum_complete_holdout_events"] = len(recovered) >= 100
    status = "R3_HOLDOUT_PASS_FROZEN" if all(checks.values()) else "R3_HOLDOUT_REJECT"
    report = {"schema_version": "dukascopy-calibration-r3-holdout-1.0", "status": status,
        "frozen_constants": FROZEN, "observed_holdout_q99": observed, "checks": checks,
        "holdout_rows": len(rows), "complete_holdout_events": len(recovered),
        "holdout_start_utc": HOLDOUT_START.isoformat().replace("+00:00", "Z"),
        "holdout_end_utc": HOLDOUT_END.isoformat().replace("+00:00", "Z"),
        "claim_limit": "Historical replay stress only; no execution-slippage or trading claim.",
        "external_python_trading": "DISABLED", "trading_authorized": False}
    report["report_sha256"] = hashlib.sha256(json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    target = root / "calibration" / "r3_holdout_validation_report.json"
    target.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    if status != "R3_HOLDOUT_PASS_FROZEN":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
