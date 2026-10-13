"""Fail-closed advisory setup evaluation and lifecycle.

The engine can create only advisory candidates.  It has no sizing, broker,
order, position, or execution interface.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType

from xauusd_agent.market.models import _require_utc


class SetupFamily(StrEnum):
    TPB = "TPB"
    BRT = "BRT"
    FBR = "FBR"
    RSR = "RSR"
    MOC = "MOC"


class Direction(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class Predicate(StrEnum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class SetupState(StrEnum):
    OBSERVED = "OBSERVED"
    PROPOSED = "PROPOSED"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    CONSUMED = "CONSUMED"
    NO_TRADE = "NO_TRADE"


@dataclass(frozen=True, slots=True)
class SetupConfig:
    strategy_version: str
    tick_size: Decimal
    minimum_rr_tp1: Decimal = Decimal("1.5")
    minimum_rr_final: Decimal = Decimal("2.0")
    expiry_bars: Mapping[SetupFamily, int] | None = None
    required_predicates: Mapping[SetupFamily, frozenset[str]] | None = None

    def __post_init__(self) -> None:
        if not self.strategy_version.strip():
            raise ValueError("strategy_version is required")
        if self.tick_size <= 0:
            raise ValueError("setup thresholds must be positive")
        if self.minimum_rr_tp1 < Decimal("1.5") or self.minimum_rr_final < Decimal("2.0"):
            raise ValueError("reward/risk configuration weakens the frozen baseline")
        expected = {
            SetupFamily.TPB: 4,
            SetupFamily.BRT: 4,
            SetupFamily.FBR: 3,
            SetupFamily.RSR: 4,
            SetupFamily.MOC: 0,
        }
        supplied = dict(self.expiry_bars or expected)
        if supplied != expected:
            raise ValueError("expiry bars differ from frozen family baseline")
        object.__setattr__(self, "expiry_bars", MappingProxyType(supplied))
        common = {
            "data_admitted",
            "session_clear",
            "spread_clear",
            "volatility_clear",
            "event_clear",
            "exposure_clear",
            "risk_clear",
        }
        family_specific = {
            SetupFamily.TPB: {
                "regime",
                "impulse",
                "zone_location",
                "confirmation",
                "structure_valid",
            },
            SetupFamily.BRT: {
                "regime",
                "boundary",
                "consolidation",
                "breakout",
                "retest",
                "confirmation",
                "structure_valid",
            },
            SetupFamily.FBR: {
                "regime",
                "boundary",
                "breach",
                "reclaim",
                "hold",
                "confirmation",
                "structure_valid",
            },
            SetupFamily.RSR: {
                "regime",
                "range",
                "location",
                "confirmation",
                "cluster_unused",
                "structure_valid",
            },
            SetupFamily.MOC: {
                "regime",
                "impulse",
                "compression",
                "trigger",
                "quote_chase_clear",
                "structure_valid",
            },
        }
        baseline = {family: frozenset(common | family_specific[family]) for family in SetupFamily}
        supplied_predicates = dict(self.required_predicates or baseline)
        if set(supplied_predicates) != set(SetupFamily):
            raise ValueError("required_predicates must define all setup families")
        if any(
            not baseline[family].issubset(supplied_predicates[family]) for family in SetupFamily
        ):
            raise ValueError("required_predicates weakens the frozen predicate inventory")
        object.__setattr__(
            self,
            "required_predicates",
            MappingProxyType(
                {family: frozenset(names) for family, names in supplied_predicates.items()}
            ),
        )


@dataclass(frozen=True, slots=True)
class SetupCandidate:
    setup_id: str
    family: SetupFamily
    direction: Direction
    decision_time: datetime
    state: SetupState
    reasons: tuple[str, ...]
    entry: Decimal | None = None
    stop: Decimal | None = None
    tp1: Decimal | None = None
    final_target: Decimal | None = None
    expiry_bars: int = 0

    @property
    def proposed(self) -> bool:
        return self.state is SetupState.PROPOSED


@dataclass(frozen=True, slots=True)
class SetupLifecycle:
    setup_id: str
    state: SetupState = SetupState.OBSERVED
    last_event_time: datetime | None = None
    terminal_reason: str | None = None


def _canonical_identity(parts: Mapping[str, object]) -> str:
    encoded = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _rr(entry: Decimal, stop: Decimal, target: Decimal, direction: Direction) -> Decimal | None:
    if direction is Direction.LONG:
        risk, reward = entry - stop, target - entry
    else:
        risk, reward = stop - entry, entry - target
    return None if risk <= 0 or reward <= 0 else reward / risk


def evaluate_setup(
    *,
    config: SetupConfig,
    account_fingerprint: str,
    family: SetupFamily,
    direction: Direction,
    decision_time: datetime,
    trigger_bar_time: datetime,
    anchor_times: Sequence[datetime],
    level_prices: Sequence[Decimal],
    predicates: Mapping[str, Predicate],
    entry: Decimal,
    stop: Decimal,
    tp1: Decimal,
    final_target: Decimal,
) -> SetupCandidate:
    """Evaluate explicit upstream predicates without inventing missing evidence."""
    _require_utc(decision_time, "decision_time")
    _require_utc(trigger_bar_time, "trigger_bar_time")
    if trigger_bar_time > decision_time:
        raise ValueError("trigger bar cannot be in the future")
    if (
        not re.fullmatch(r"[0-9a-f]{64}", account_fingerprint)
        or not anchor_times
        or not level_prices
    ):
        raise ValueError("immutable setup identity inputs are required")
    for value in anchor_times:
        _require_utc(value, "anchor_time")
    identity = _canonical_identity(
        {
            "strategy_version": config.strategy_version,
            "account_fingerprint": account_fingerprint,
            "symbol": "XAUUSD",
            "family": family.value,
            "direction": direction.value,
            "anchor_times": [value.isoformat() for value in anchor_times],
            "level_prices": [str(value) for value in level_prices],
            "trigger_bar_time": trigger_bar_time.isoformat(),
        }
    )
    reasons: list[str] = []
    assert config.required_predicates is not None
    for missing in sorted(config.required_predicates[family] - predicates.keys()):
        reasons.append(f"{missing}:UNKNOWN")
    for name in sorted(predicates):
        result = predicates[name]
        if result is Predicate.UNKNOWN:
            reasons.append(f"{name}:UNKNOWN")
        elif result is Predicate.FALSE:
            reasons.append(f"{name}:FALSE")
    rr_tp1 = _rr(entry, stop, tp1, direction)
    rr_final = _rr(entry, stop, final_target, direction)
    if rr_tp1 is None or rr_tp1 < config.minimum_rr_tp1:
        reasons.append("TP1_RR_INSUFFICIENT")
    if rr_final is None or rr_final < config.minimum_rr_final:
        reasons.append("FINAL_RR_INSUFFICIENT")
    assert config.expiry_bars is not None
    if reasons:
        return SetupCandidate(
            identity,
            family,
            direction,
            decision_time,
            SetupState.NO_TRADE,
            tuple(reasons),
            expiry_bars=config.expiry_bars[family],
        )
    return SetupCandidate(
        identity,
        family,
        direction,
        decision_time,
        SetupState.PROPOSED,
        (),
        entry,
        stop,
        tp1,
        final_target,
        config.expiry_bars[family],
    )


def select_unambiguous(candidates: Sequence[SetupCandidate]) -> SetupCandidate | None:
    """Admit exactly one proposal; zero or competing proposals fail closed."""
    proposed = [candidate for candidate in candidates if candidate.proposed]
    return proposed[0] if len(proposed) == 1 else None


_CANCELLATIONS = {
    "COMMON_FILTER_FAILED",
    "REGIME_LOST",
    "STRUCTURE_INVALIDATED",
    "EVENT_LOCK",
    "PRICE_ALREADY_REACHED_TARGET",
    "QUOTE_STALE",
    "SPREAD_BLOCKED",
}


def transition(state: SetupLifecycle, event: str, event_time: datetime) -> SetupLifecycle:
    _require_utc(event_time, "event_time")
    if state.last_event_time is not None and event_time <= state.last_event_time:
        raise ValueError("lifecycle event time must increase")
    if state.state in {
        SetupState.CANCELLED,
        SetupState.EXPIRED,
        SetupState.CONSUMED,
        SetupState.NO_TRADE,
    }:
        raise ValueError("terminal lifecycle cannot reactivate")
    if event == "PROPOSE" and state.state is SetupState.OBSERVED:
        return SetupLifecycle(state.setup_id, SetupState.PROPOSED, event_time)
    if event == "RESERVE" and state.state is SetupState.PROPOSED:
        return SetupLifecycle(state.setup_id, SetupState.PENDING, event_time)
    if event in _CANCELLATIONS and state.state in {SetupState.PROPOSED, SetupState.PENDING}:
        return SetupLifecycle(state.setup_id, SetupState.CANCELLED, event_time, event)
    if event == "PENDING_EXPIRED" and state.state is SetupState.PENDING:
        return SetupLifecycle(state.setup_id, SetupState.EXPIRED, event_time, event)
    if event == "FILLED_OBSERVED" and state.state is SetupState.PENDING:
        return SetupLifecycle(state.setup_id, SetupState.CONSUMED, event_time, event)
    raise ValueError("invalid lifecycle transition")
