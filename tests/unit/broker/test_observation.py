import inspect
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from xauusd_agent.broker.fixture import (
    BrokerObservationUnavailable,
    StaticReadOnlyBroker,
    UnavailableBrokerObserver,
)
from xauusd_agent.broker.observation import (
    AccountFingerprint,
    AccountObservation,
    BrokerReadOnly,
    BuildFingerprint,
    SymbolFingerprint,
)


def test_broker_protocol_is_structurally_read_only() -> None:
    method_names = {
        name
        for name, value in inspect.getmembers(BrokerReadOnly)
        if inspect.isfunction(value) and not name.startswith("_")
    }
    assert method_names == {
        "observe_account",
        "observe_build_fingerprint",
        "observe_orders",
        "observe_positions",
        "observe_symbol_fingerprint",
    }
    forbidden_fragments = {"submit", "send", "modify", "cancel", "close", "enable"}
    assert not any(fragment in name for name in method_names for fragment in forbidden_fragments)


def test_fingerprints_are_immutable() -> None:
    fingerprint = AccountFingerprint(
        broker="Exness",
        server="Demo",
        account_id_sha256="a" * 64,
        currency="USD",
        leverage=100,
        account_mode="DEMO",
    )
    with pytest.raises(FrozenInstanceError):
        fingerprint.leverage = 200  # type: ignore[misc]
    assert Decimal("0.01").is_finite()


def test_static_observer_implements_only_read_observations() -> None:
    account_fingerprint = AccountFingerprint(
        broker="Exness",
        server="Demo",
        account_id_sha256="a" * 64,
        currency="USD",
        leverage=100,
        account_mode="DEMO",
    )
    symbol_fingerprint = SymbolFingerprint(
        symbol="XAUUSD",
        path="Metals\\XAUUSD",
        digits=3,
        point=Decimal("0.001"),
        contract_size=Decimal("100"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("100"),
        volume_step=Decimal("0.01"),
    )
    observer = StaticReadOnlyBroker(
        account=AccountObservation(
            observed_at_utc="2026-10-05T00:00:00Z",
            connected=True,
            trading_api_disabled=True,
            equity=Decimal("10000"),
            free_margin=Decimal("10000"),
            margin_used=Decimal("0"),
            fingerprint=account_fingerprint,
        ),
        symbol=symbol_fingerprint,
        build=BuildFingerprint("MetaTrader 5", "MetaQuotes", 5000, "5.0"),
    )
    assert isinstance(observer, BrokerReadOnly)
    assert observer.observe_positions() == ()
    assert observer.observe_orders() == ()
    assert observer.observe_symbol_fingerprint("XAUUSD") == symbol_fingerprint
    with pytest.raises(BrokerObservationUnavailable):
        observer.observe_symbol_fingerprint("EURUSD")


def test_unavailable_observer_fails_closed_for_every_public_read() -> None:
    observer = UnavailableBrokerObserver()
    calls = (
        observer.observe_account,
        observer.observe_build_fingerprint,
        observer.observe_orders,
        observer.observe_positions,
    )
    for call in calls:
        with pytest.raises(BrokerObservationUnavailable):
            call()
    with pytest.raises(BrokerObservationUnavailable):
        observer.observe_symbol_fingerprint("XAUUSD")
