"""Deterministic Gate 0 oracle for the frozen replay acceptance gates.

This module evaluates already-computed, versioned replay statistics.  It does
not calculate strategy performance, open a holdout, connect to MT5, or trade.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


REQUIRED_VALIDITY_GATES = (
    "lineage_complete",
    "causal_audit_passed",
    "deterministic_repeat_passed",
    "trial_registry_complete",
    "zero_policy_violations",
    "numeric_and_event_integrity_passed",
)


@dataclass(frozen=True)
class Evaluation:
    verdict: str
    failures: tuple[str, ...]
    insufficient_evidence: tuple[str, ...]


def evaluate(record: dict[str, Any]) -> Evaluation:
    """Apply Draft 1.0 section 6 without relaxing missing-data behavior."""
    failures: list[str] = []
    insufficient: list[str] = []

    validity = record.get("validity", {})
    for gate in REQUIRED_VALIDITY_GATES:
        if validity.get(gate) is not True:
            failures.append(f"validity:{gate}")

    metrics = record.get("metrics", {})
    required_metrics = (
        "oos_mean_r",
        "ci95_lower_r",
        "dsr_probability",
        "pbo",
        "max_drawdown_usd",
        "best_month_positive_profit_share",
        "best_session_positive_profit_share",
        "expectancy_without_best_5_r",
        "nonnegative_fold_fraction",
        "expectancy_without_best_fold_r",
        "double_cost_expectancy_r",
    )
    for name in required_metrics:
        value = metrics.get(name)
        if name not in metrics or value is None:
            insufficient.append(f"metric:{name}")
        elif isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value):
            failures.append(f"metric:{name}_invalid")

    bounded = (
        "dsr_probability", "pbo", "best_month_positive_profit_share",
        "best_session_positive_profit_share", "nonnegative_fold_fraction",
    )
    for name in bounded:
        value = metrics.get(name)
        if (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and not 0 <= value <= 1):
            failures.append(f"metric:{name}_outside_0_1")
    drawdown = metrics.get("max_drawdown_usd")
    if (isinstance(drawdown, (int, float)) and not isinstance(drawdown, bool)
            and math.isfinite(drawdown) and drawdown < 0):
        failures.append("metric:max_drawdown_usd_negative")
    mean_r, ci_lower = metrics.get("oos_mean_r"), metrics.get("ci95_lower_r")
    if (all(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) for value in (mean_r, ci_lower))
            and ci_lower > mean_r):
        failures.append("metric:ci95_lower_above_mean")

    evidence = record.get("evidence", {})
    for name in ("sample_size_justified", "coverage_sufficient", "selection_adjustment_applicable"):
        if evidence.get(name) is not True:
            insufficient.append(f"evidence:{name}")

    metric_invalid = any(reason.startswith("metric:") for reason in failures)
    if not insufficient and not metric_invalid:
        if metrics["oos_mean_r"] <= 0:
            failures.append("economic:oos_mean_r_not_positive")
        if metrics["ci95_lower_r"] <= -0.05:
            failures.append("economic:ci95_lower_not_above_minus_0_05r")
        if metrics["dsr_probability"] < 0.95:
            failures.append("selection:dsr_below_0_95")
        if metrics["pbo"] > 0.20:
            failures.append("selection:pbo_above_0_20")
        if metrics["max_drawdown_usd"] > 500:
            failures.append("risk:drawdown_above_500_usd")
        if metrics["best_month_positive_profit_share"] > 0.50:
            failures.append("fragility:month_share_above_0_50")
        if metrics["best_session_positive_profit_share"] > 0.60:
            failures.append("fragility:session_share_above_0_60")
        if metrics["expectancy_without_best_5_r"] <= -0.05:
            failures.append("fragility:without_best_5_not_above_minus_0_05r")
        if metrics["nonnegative_fold_fraction"] < 0.75:
            failures.append("walk_forward:nonnegative_fold_fraction_below_0_75")
        if metrics["expectancy_without_best_fold_r"] <= -0.05:
            failures.append("walk_forward:without_best_fold_not_above_minus_0_05r")
        if metrics["double_cost_expectancy_r"] <= -0.05:
            failures.append("cost:double_cost_not_above_minus_0_05r")

    if failures:
        verdict = "REJECT"
    elif insufficient:
        verdict = "INSUFFICIENT_EVIDENCE"
    else:
        verdict = "ACCEPT"
    return Evaluation(verdict, tuple(failures), tuple(insufficient))
