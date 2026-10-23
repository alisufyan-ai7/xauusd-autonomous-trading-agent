"""Deterministic, execution-disabled known-position management decision engine.

Pure management advisory intended for a future *single S2* broker modification
port. Exact persisted broker identity, fresh bid/ask and stop/TP are mandatory.
No MT5 imports, order_check, order_send, side selection, closure or write APIs.
A decision is NOT a permission to modify a broker position.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from .envelope import DemoSafetyError
from .known_position_reconciliation import KnownPositionBinding

MAX_QUOTE_AGE = timedelta(seconds=2)


class ManagementAction(StrEnum):
    NO_CHANGE = "NO_CHANGE"
    PROPOSE_EARLY_EXIT = "PROPOSE_EARLY_EXIT"
    PROPOSE_TIGHTEN_STOP = "PROPOSE_TIGHTEN_STOP"
    PROPOSE_TAKE_PROFIT_REFINEMENT = "PROPOSE_TAKE_PROFIT_REFINEMENT"


@dataclass(frozen=True, slots=True)
class KnownMarketSnapshot:
    """Only values observed from the *already reconciled* known position.

    structure_invalidation / favourable_structure_confirmed and trailing_stop
    are research hints, never trusted broker modification authority. A caller
    must independently verify completed-bar provenance before any later action.
    """

    account_fingerprint: str
    position_id: int
    side: str
    lots: Decimal
    entry_price: Decimal
    current_stop: Decimal
    current_target: Decimal
    tick_size: Decimal
    bid: Decimal
    ask: Decimal
    quote_utc: datetime
    observed_utc: datetime
    reconciliation: str
    structure_invalidation: bool = False
    favourable_structure_confirmed: bool = False
    trailing_stop: Decimal | None = None
    reduced_take_profit: Decimal | None = None


@dataclass(frozen=True, slots=True)
class ManagementDecision:
    action: ManagementAction
    reason: str
    suggested_stop: Decimal | None = None
    suggested_target: Decimal | None = None
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise DemoSafetyError("pure management intent cannot authorize MT5 write")


def _price(value: Decimal, label: str, tick: Decimal) -> None:
    if (
        type(value) is not Decimal or not value.is_finite()
        or value <= 0 or value % tick != 0
    ):
        raise DemoSafetyError(f"invalid or off-grid {label}")


def evaluate_known_position_management(
    binding: KnownPositionBinding, snapshot: KnownMarketSnapshot, *, now: datetime
) -> ManagementDecision:
    """Return ONE bounded, non-executable candidate or fail closed.

    Any account swap, unknown position, stale quote, stop/TP discrepancy, or
    unsafe price grid stops evaluation. Selection precedence: confirmed thesis
    invalidation, stop tightening, then non-widening target reduction.
    Active broker execution remains independently UNADMITTED and must itself
    reobserve the actual MT5 position, freeze levels, session and cash risk.
    """
    if (
        now.tzinfo is None or now.utcoffset() != timedelta(0)
        or snapshot.observed_utc.tzinfo is None
        or snapshot.observed_utc.utcoffset() != timedelta(0)
        or snapshot.quote_utc.tzinfo is None
        or snapshot.quote_utc.utcoffset() != timedelta(0)
        or snapshot.quote_utc > snapshot.observed_utc
        or snapshot.observed_utc > now
        or now - snapshot.quote_utc > MAX_QUOTE_AGE
    ):
        raise DemoSafetyError("stale, future or non-UTC management quote")
    if (
        snapshot.reconciliation != "OPEN"
        or snapshot.account_fingerprint != binding.account_fingerprint
        or type(snapshot.position_id) is not int
        or snapshot.position_id != binding.position_id
        or snapshot.side != binding.side
        or type(snapshot.lots) is not Decimal
        or snapshot.lots != binding.volume
        or snapshot.tick_size != binding.tick_size
        or snapshot.current_stop != binding.protective_sl
        or snapshot.current_target != binding.protective_tp
    ):
        raise DemoSafetyError("unknown/changed broker position or unbound protection")
    tick = binding.tick_size
    for label, value in (
        ("entry", snapshot.entry_price),
        ("stop", snapshot.current_stop),
        ("target", snapshot.current_target),
        ("bid", snapshot.bid),
        ("ask", snapshot.ask),
    ):
        _price(value, label, tick)
    if (
        snapshot.ask <= snapshot.bid
        or (
            snapshot.side == "BUY"
            and not (snapshot.current_stop < snapshot.entry_price < snapshot.current_target)
        )
        or (
            snapshot.side == "SELL"
            and not (snapshot.current_target < snapshot.entry_price < snapshot.current_stop)
        )
    ):
        raise DemoSafetyError("invalid known position price geometry")
    if (
        type(snapshot.structure_invalidation) is not bool
        or type(snapshot.favourable_structure_confirmed) is not bool
    ):
        raise DemoSafetyError("invalid thesis/structure source flags")

    # A real early exit still requires a future independently verified
    # completed-bar predicate and the single broker-owned close port.
    if snapshot.structure_invalidation:
        return ManagementDecision(
            ManagementAction.PROPOSE_EARLY_EXIT, "THESIS_INVALIDATED_RESEARCH_ONLY"
        )

    trailing = snapshot.trailing_stop
    if trailing is not None:
        _price(trailing, "trailing stop", tick)
        if snapshot.side == "BUY":
            safer = snapshot.current_stop < trailing < snapshot.bid - tick
        else:
            safer = snapshot.ask + tick < trailing < snapshot.current_stop
        # The research source is only eligible to suggest tightening after
        # favourable structure; untrusted premature candidates are ignored.
        if safer and snapshot.favourable_structure_confirmed:
            return ManagementDecision(
                ManagementAction.PROPOSE_TIGHTEN_STOP,
                "STRICTLY_REDUCES_INITIAL_KNOWN_LOSS_RESEARCH_ONLY",
                suggested_stop=trailing,
            )

    target = snapshot.reduced_take_profit
    if target is not None:
        _price(target, "new take profit", tick)
        if snapshot.side == "BUY":
            safer_target = snapshot.ask + tick < target < snapshot.current_target
        else:
            safer_target = snapshot.current_target < target < snapshot.bid - tick
        if safer_target and snapshot.favourable_structure_confirmed:
            return ManagementDecision(
                ManagementAction.PROPOSE_TAKE_PROFIT_REFINEMENT,
                "TIGHTER_KNOWN_TP_RESEARCH_ONLY",
                suggested_target=target,
            )

    return ManagementDecision(ManagementAction.NO_CHANGE, "NO_ADMISSIBLE_MANAGEMENT_CHANGE")
