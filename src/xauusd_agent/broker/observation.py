"""Immutable broker observations and an intentionally read-only boundary."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class AccountFingerprint:
    broker: str
    server: str
    account_id_sha256: str
    currency: str
    leverage: int
    account_mode: str


@dataclass(frozen=True, slots=True)
class SymbolFingerprint:
    symbol: str
    path: str
    digits: int
    point: Decimal
    contract_size: Decimal
    volume_min: Decimal
    volume_max: Decimal
    volume_step: Decimal


@dataclass(frozen=True, slots=True)
class BuildFingerprint:
    terminal_name: str
    terminal_company: str
    terminal_build: int
    python_bridge_version: str


@dataclass(frozen=True, slots=True)
class BrokerFingerprint:
    account: AccountFingerprint
    symbol: SymbolFingerprint
    build: BuildFingerprint


@dataclass(frozen=True, slots=True)
class AccountObservation:
    observed_at_utc: str
    connected: bool
    trading_api_disabled: bool
    equity: Decimal
    free_margin: Decimal
    margin_used: Decimal
    fingerprint: AccountFingerprint


@dataclass(frozen=True, slots=True)
class PositionObservation:
    position_id: str
    symbol: str
    side: str
    volume_lots: Decimal


@dataclass(frozen=True, slots=True)
class OrderObservation:
    order_id: str
    symbol: str
    side: str
    volume_lots: Decimal
    state: str


@runtime_checkable
class BrokerReadOnly(Protocol):
    """The complete broker port for an execution-disabled production candidate.

    There are intentionally no submit, modify, cancel, close, or enable methods.
    Implementations may only return observations.
    """

    def observe_account(self) -> AccountObservation: ...

    def observe_symbol_fingerprint(self, symbol: str) -> SymbolFingerprint: ...

    def observe_build_fingerprint(self) -> BuildFingerprint: ...

    def observe_positions(self) -> tuple[PositionObservation, ...]: ...

    def observe_orders(self) -> tuple[OrderObservation, ...]: ...
