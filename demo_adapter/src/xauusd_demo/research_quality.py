"""Deterministic, chronological real-broker DEMO learning evidence.

Every UTC-day closed-trade cohort is sorted chronologically. The earlier 70%
is development; the later 30% is held-out. The report may flag a need to
research a *separately tested* challenger; it NEVER retunes strategy weights,
upgrades source, or starts an order on its own.
"""
from __future__ import annotations

import json
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .envelope import DemoSafetyError


def review_closed_demo_cohort(folder: Path) -> dict[str, object]:
    deals: list[tuple[str, Decimal]] = []
    for path in sorted(folder.glob("????-??-??.json")):
        try:
            day = date.fromisoformat(path.stem)
            raw = json.loads(path.read_text(encoding="utf-8"))
            if raw.get("account_type") != "EXNESS_PRO_DEMO_ONLY":
                raise DemoSafetyError("cannot train on unrecognized broker cohort")
            for row in raw.get("positions", []):
                pnl = Decimal(str(row["net_usd"]))
                if not pnl.is_finite():
                    raise DemoSafetyError("broker outcome nonfinite")
                deals.append((day.isoformat(), pnl))
        except (OSError, ValueError, TypeError, KeyError, InvalidOperation) as exc:
            raise DemoSafetyError("historical broker research record corrupt") from exc
    deals.sort(key=lambda x: x[0])
    if not deals:
        return {
            "status": "INSUFFICIENT_REAL_CLOSED_TRADES",
            "count": 0, "auto_strategy_promotion": False,
        }
    if len(deals) < 30:
        return {
            "status": "INSUFFICIENT_REAL_CLOSED_TRADES",
            "count": len(deals), "auto_strategy_promotion": False,
        }
    n = len(deals)
    split = max(20, int(n * 0.7))
    development = deals[:split]
    validation = deals[split:]
    if not validation:
        raise DemoSafetyError("chronological validation cohort missing")

    def assess(rows: list[tuple[str, Decimal]]) -> dict[str, str | int]:
        values = [item[1] for item in rows]
        net = sum(values, Decimal(0))
        gross_positive = sum((x for x in values if x > 0), Decimal(0))
        gross_negative = sum((-x for x in values if x < 0), Decimal(0))
        peak = Decimal(0)
        equity = Decimal(0)
        maximum_drawdown = Decimal(0)
        for change in values:
            equity += change
            peak = max(peak, equity)
            maximum_drawdown = max(maximum_drawdown, peak-equity)
        return {
            "count": len(values),
            "net_usd": str(net),
            "expectancy_usd": str(net / Decimal(len(values))),
            "profit_factor": (
                str(gross_positive / gross_negative)
                if gross_negative > 0 else "UNDEFINED_NO_GROSS_LOSS"
            ),
            "max_drawdown_usd": str(maximum_drawdown),
            "winning_trades": sum(x > 0 for x in values),
        }
    dev, valid = assess(development), assess(validation)
    return {
        "status": (
            "RESEARCH_CHALLENGER_NEEDED"
            if Decimal(str(valid["expectancy_usd"])) <= 0
            else "VALIDATION_POSITIVE_REQUIRES_INDEPENDENT_REPLICATION"
        ),
        "count": n,
        "development": dev, "untouched_validation": valid,
        "split_rule": "CHRONOLOGICAL_70_30_BY_BROKER_CLOSURE",
        "auto_strategy_promotion": False,
        "estimated_future_profit_guaranteed": False,
    }


def write_quality_snapshot(folder: Path) -> None:
    review = review_closed_demo_cohort(folder)
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / "quality.json.tmp"
    dst = folder / "quality.json"
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(review, stream, sort_keys=True, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(dst)
