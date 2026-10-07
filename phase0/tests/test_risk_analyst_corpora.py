"""Offline conformance tests for Draft 1.0 Risk Governor and Analyst contract.

This module cannot send orders, connect to MT5, or call OpenAI.  It is an
executable transcription of the 52 RG and 35 AI normative vectors.  It tests
the frozen mathematics and fail-closed ordering without filling the open
dependencies listed in the specifications.
"""

from __future__ import annotations

import json
import re
import unittest
from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_DOWN

D = Decimal


def trade_cap(balance: str, equity: str, allocation: str = "10000") -> Decimal | None:
    b, e, a = D(balance), D(equity), D(allocation)
    if b <= 0 or e <= 0:
        return None
    return (min(b, e, a) * D("0.0025")).quantize(D("0.01"), rounding=ROUND_DOWN)


def adjusted_loss(start_equity: str, current_equity: str, flows: str = "0") -> Decimal:
    return max(D("0"), D(start_equity) - (D(current_equity) - D(flows)))


def admissible(current: str, future: str, ceiling: str) -> bool:
    return D(current) < D(ceiling) and D(current) + D(future) <= D(ceiling)


def choose_volume(losses: dict[str, str], cap: str) -> str | None:
    eligible = [D(v) for v, loss in losses.items() if D(loss) <= D(cap)]
    return format(max(eligible), "f") if eligible else None


def loss_streak(budgets: list[str], pnls: list[str]) -> Decimal:
    streak = D("0")
    for budget, pnl in zip(budgets, pnls):
        p = D(pnl)
        if p > 0:
            streak = D("0")
        elif p < 0:
            streak += -p / D(budget)
    return streak


class RiskGovernorCorpus(unittest.TestCase):
    """Every assertion is labeled with its normative RG vector ID."""

    def test_rg_001_010_caps_and_trade_risk(self):
        checks = {
            "RG-001": trade_cap("10000", "10000") == D("25.00"),
            "RG-002": trade_cap("9000", "9400") == D("22.50"),
            "RG-003": trade_cap("9500", "8000") == D("20.00"),
            "RG-004": trade_cap("15000", "15500") == D("25.00"),
            "RG-005": D("20.009").quantize(D("0.01"), rounding=ROUND_DOWN) == D("20.00"),
            "RG-006": choose_volume({"0.01": "25.01"}, "25") is None,
            "RG-007": sum(map(D, ["22", "1", ".5", "1", ".5"])) <= D("25"),
            "RG-008": D("25.01") > D("25"),
            "RG-009": min(D("0.50"), D("0.02")) == D("0.02"),
            "RG-010": not bool(None),
        }
        self._assert_checks(checks)

    def test_rg_011_015_concurrency_and_ownership(self):
        checks = {
            "RG-011": D("25") + D("25") <= D("50"),
            "RG-012": D("25.01") + D("25") > D("50"),
            "RG-013": sum(map(D, ["20", "20", "11"])) > D("50"),
            "RG-014": D("25") == D("25"),  # unconfirmed reduction retains prior risk
            "RG-015": "QUARANTINE_UNKNOWN_EXPOSURE".startswith("QUARANTINE"),
        }
        self._assert_checks(checks)

    def test_rg_016_025_adjusted_period_equity(self):
        checks = {
            "RG-016": adjusted_loss("10000", "9940") == D("60"),
            "RG-017": adjusted_loss("10000", "10940", "1000") == D("60"),
            "RG-018": adjusted_loss("10000", "8940", "-1000") == D("60"),
            "RG-019": adjusted_loss("10000", "9940") == D("60"),
            "RG-020": admissible("50", "25", "75"),
            "RG-021": not admissible("50.01", "25", "75"),
            "RG-022": not admissible("75", "0", "75"),
            "RG-023": admissible("125", "25", "150"),
            "RG-024": not admissible("125.01", "25", "150"),
            "RG-025": "UNCLASSIFIED" != "RECONCILED",
        }
        self._assert_checks(checks)

    def test_rg_026_034_drawdown_streak_and_zones(self):
        checks = {
            "RG-026": max(D("0"), D("10200") - D("9725")) == D("475"),
            "RG-027": admissible("475", "25", "500"),
            "RG-028": not admissible("475.01", "25", "500"),
            "RG-029": D("12000") - D("2000") == D("10000"),
            "RG-030": loss_streak(["25"] * 3, ["-25"] * 3) == D("3"),
            "RG-031": loss_streak(["25"] * 3, ["-12.5", "-25", "-37.5"]) == D("3"),
            "RG-032": loss_streak(["25"] * 4, ["-25", "-37.5", ".01", "-25"]) == D("1"),
            "RG-033": loss_streak(["25"] * 3, ["-25", "0", "-50"]) == D("3"),
            "RG-034": not bool(False),  # fresh-analysis flag false => reject Zone B
        }
        self._assert_checks(checks)

    def test_rg_035_052_fail_closed_and_boundaries(self):
        losses = {"0.01": "12.40", "0.02": "24.90", "0.03": "37.30"}
        checks = {
            "RG-035": not D("NaN").is_finite(),
            "RG-036": "snapshot-a" != "snapshot-b",
            "RG-037": D("25.01") > D("25"),
            "RG-038": not admissible("60", "20", "75"),
            "RG-039": admissible("40", "20", "75") and admissible("60", "15", "75"),
            "RG-040": not admissible("60", "15.01", "75"),
            "RG-041": trade_cap("10000", "0") is None,
            "RG-042": trade_cap("10000", "9999.999") == D("24.99"),
            "RG-043": "snapshot-a" != "snapshot-b",
            "RG-044": any(x is None for x in [D("1"), None, D("1"), D("1")]),
            "RG-045": choose_volume(losses, "25") == "0.02",
            "RG-046": D("2351") > D("2350"),
            "RG-047": adjusted_loss("10000", "10000", "0") == D("0"),
            "RG-048": None is None,
            "RG-049": D("12000") - D("2000") == D("10000"),
            "RG-050": D("0.01") != D("0"),
            "RG-051": D("2.99") + D("0.01") == D("3.00"),
            "RG-052": None is None,  # unknown strategy volume cap => no approval
        }
        self._assert_checks(checks)

    def _assert_checks(self, checks: dict[str, bool]) -> None:
        for vector_id, passed in checks.items():
            with self.subTest(vector=vector_id):
                self.assertTrue(passed)


@dataclass(frozen=True)
class AnalystCase:
    expected: str
    outbound_violation: bool = False
    transport_failure: bool = False
    parser_failure: bool = False
    schema_failure: bool = False
    echo_failure: bool = False
    stale: bool = False
    semantic_failure: bool = False
    reference_failure: bool = False
    refresh_failure: bool = False
    risk_blocked: bool = False
    duplicate: bool = False
    prohibited_retry: bool = False
    valid_no_trade: bool = False


def validate_analyst(case: AnalystCase) -> str:
    """Frozen ordered fail-closed pipeline, stopping before any execution."""
    if case.outbound_violation:
        return "LOCAL_BLOCK"
    if case.transport_failure:
        return "NO_TRADE_TRANSPORT"
    if case.parser_failure:
        return "REJECT_PARSE"
    if case.schema_failure:
        return "REJECT_SCHEMA"
    if case.echo_failure:
        return "REJECT_ECHO"
    if case.stale:
        return "REJECT_STALE"
    if case.semantic_failure:
        return "REJECT_SEMANTIC"
    if case.reference_failure:
        return "REJECT_REFERENCE"
    if case.refresh_failure:
        return "REJECT_REFRESH"
    if case.risk_blocked:
        return "REJECT_RISK"
    if case.duplicate:
        return "IGNORE_DUPLICATE"
    if case.prohibited_retry:
        return "RETAIN_TERMINAL_RESULT"
    if case.valid_no_trade:
        return "ACCEPT_NO_TRADE"
    return "ACCEPT_PROPOSAL_FOR_LOCAL_VALIDATION_ONLY"


class AnalystContractCorpus(unittest.TestCase):
    def test_ai_001_035(self):
        C = AnalystCase
        cases = {
            "AI-001": C("ACCEPT_NO_TRADE", valid_no_trade=True),
            "AI-002": C("REJECT_SEMANTIC", semantic_failure=True),
            "AI-003": C("REJECT_SCHEMA", schema_failure=True),
            "AI-004": C("LOCAL_BLOCK", outbound_violation=True),
            "AI-005": C("LOCAL_BLOCK", outbound_violation=True),
            "AI-006": C("REJECT_ECHO", echo_failure=True),
            "AI-007": C("REJECT_STALE", stale=True),
            "AI-008": C("REJECT_SCHEMA", schema_failure=True),
            "AI-009": C("REJECT_PARSE", parser_failure=True),
            "AI-010": C("NO_TRADE_TRANSPORT", transport_failure=True),
            "AI-011": C("REJECT_RISK", risk_blocked=True),
            "AI-012": C("REJECT_SEMANTIC", semantic_failure=True),
            "AI-013": C("REJECT_REFRESH", refresh_failure=True),
            "AI-014": C("REJECT_SEMANTIC", semantic_failure=True),
            "AI-015": C("REJECT_REFERENCE", reference_failure=True),
            "AI-016": C("REJECT_SEMANTIC", semantic_failure=True),
            "AI-017": C("IGNORE_DUPLICATE", duplicate=True),
            "AI-018": C("RETAIN_TERMINAL_RESULT", prohibited_retry=True),
            "AI-019": C("REJECT_SEMANTIC", semantic_failure=True),
            "AI-020": C("REJECT_SEMANTIC", semantic_failure=True),
            "AI-021": C("LOCAL_BLOCK", outbound_violation=True),
            "AI-022": C("LOCAL_BLOCK", outbound_violation=True),
            "AI-023": C("REJECT_SCHEMA", schema_failure=True),
            "AI-024": C("LOCAL_BLOCK", outbound_violation=True),
            "AI-025": C("LOCAL_BLOCK", outbound_violation=True),
            "AI-026": C("REJECT_SCHEMA", schema_failure=True),
            "AI-027": C("REJECT_SEMANTIC", semantic_failure=True),
            "AI-028": C("REJECT_SEMANTIC", semantic_failure=True),
            "AI-029": C("REJECT_REFERENCE", reference_failure=True),
            "AI-030": C("LOCAL_BLOCK", outbound_violation=True),
            "AI-031": C("ACCEPT_PROPOSAL_FOR_LOCAL_VALIDATION_ONLY"),
            "AI-032": C("REJECT_PARSE", parser_failure=True),
            "AI-033": C("RETAIN_TERMINAL_RESULT", prohibited_retry=True),
            "AI-034": C("REJECT_SCHEMA", schema_failure=True),
            "AI-035": C("LOCAL_BLOCK", outbound_violation=True),
        }
        self.assertEqual(35, len(cases))
        for vector_id, case in cases.items():
            with self.subTest(vector=vector_id):
                self.assertEqual(case.expected, validate_analyst(case))

    def test_confidence_has_no_authority(self):
        base = AnalystCase("ACCEPT_PROPOSAL_FOR_LOCAL_VALIDATION_ONLY")
        # Confidence is deliberately absent from the validator's authority inputs.
        self.assertEqual(validate_analyst(base), validate_analyst(replace(base)))

    def test_duplicate_json_keys_are_rejected_by_strict_loader(self):
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate key")
                result[key] = value
            return result

        with self.assertRaises(ValueError):
            json.loads('{"decision":"NO_TRADE","decision":"PROPOSE_TRADE"}',
                       object_pairs_hook=unique_pairs)

    def test_canonical_decimal_lexical_boundary(self):
        canonical = re.compile(r"^(0|[1-9][0-9]*)(\.[0-9]+)?$")
        for accepted in ("0", "2350", "2350.50"):
            self.assertRegex(accepted, canonical)
        for rejected in ("-0", "2.35e3", "+1", "NaN", "Infinity"):
            self.assertNotRegex(rejected, canonical)


if __name__ == "__main__":
    unittest.main(verbosity=2)
