"""Offline broker observers for deterministic tests and null operation."""

from __future__ import annotations

from dataclasses import dataclass

from .observation import (
    AccountObservation,
    BuildFingerprint,
    OrderObservation,
    PositionObservation,
    SymbolFingerprint,
)


class BrokerObservationUnavailable(RuntimeError):
    """Raised when the null observer has no authoritative snapshot."""


@dataclass(frozen=True, slots=True)
class StaticReadOnlyBroker:
    """Fixed offline observations with the same read-only protocol surface."""

    account: AccountObservation
    symbol: SymbolFingerprint
    build: BuildFingerprint
    positions: tuple[PositionObservation, ...] = ()
    orders: tuple[OrderObservation, ...] = ()

    def observe_account(self) -> AccountObservation:
        return self.account

    def observe_symbol_fingerprint(self, symbol: str) -> SymbolFingerprint:
        if symbol != self.symbol.symbol:
            raise BrokerObservationUnavailable("requested symbol has no fixed observation")
        return self.symbol

    def observe_build_fingerprint(self) -> BuildFingerprint:
        return self.build

    def observe_positions(self) -> tuple[PositionObservation, ...]:
        return self.positions

    def observe_orders(self) -> tuple[OrderObservation, ...]:
        return self.orders


@dataclass(frozen=True, slots=True)
class UnavailableBrokerObserver:
    """Null observer that fails closed for every requested observation."""

    reason: str = "BROKER_OBSERVATION_UNAVAILABLE"

    def _unavailable(self) -> BrokerObservationUnavailable:
        return BrokerObservationUnavailable(self.reason)

    def observe_account(self) -> AccountObservation:
        raise self._unavailable()

    def observe_symbol_fingerprint(self, symbol: str) -> SymbolFingerprint:
        del symbol
        raise self._unavailable()

    def observe_build_fingerprint(self) -> BuildFingerprint:
        raise self._unavailable()

    def observe_positions(self) -> tuple[PositionObservation, ...]:
        raise self._unavailable()

    def observe_orders(self) -> tuple[OrderObservation, ...]:
        raise self._unavailable()
