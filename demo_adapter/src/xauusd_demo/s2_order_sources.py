"""Runtime inputs for a real DEMO-only full-Policy-A STOP order preflight.

Values alone do not confer broker order authority. The one S2 adapter must
derive fresh broker money and exposure, validate the entire pending lifetime,
and recalculate the full cash-risk model immediately before order_check.
This object contains no executable approval Boolean.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from .full_policy_broker_receipt import BoundAdverseCost

if TYPE_CHECKING:
    from xauusd_agent.guards.v2_official_source_gate import VerifiedOfficialSnapshot

    from .prospective_cash_journal import ProspectiveDemoCashJournal


@dataclass(frozen=True, slots=True)
class S2OrderSources:
    cash_journal: ProspectiveDemoCashJournal
    costs: BoundAdverseCost
    expected_cost_sha256: str
    official_snapshots: tuple[VerifiedOfficialSnapshot, ...]
    session_verified_through_utc: datetime | None
    shock_locked: bool | None
    normalized: bool | None
