"""Synthetic replay of source-pinned broker/accounting evidence: never MT5."""
from __future__ import annotations

import copy
import hashlib
from typing import Any

import pytest
from xauusd_agent.risk.full_policy_a import FullRiskDisposition

from scripts.v11_offline_risk_bridge import evidence_sha256, replay_full_policy_a
from scripts.v11_readonly_collector import CaptureSafetyError


def _identity() -> str:
    return hashlib.sha256(
        b"Exness Technologies Ltd|Exness-MT5Trial15|12345678|USD"
    ).hexdigest()


def bundle() -> dict[str, dict[str, Any]]:
    t = "2026-10-19T14:00:00Z"
    return {
        "account": {
            "observed_utc": t, "company": "Exness Technologies Ltd",
            "server": "Exness-MT5Trial15", "login": 12345678,
            "currency": "USD", "trade_mode": 0, "connected": True,
            "tradeapi_disabled": True, "balance_usd": "10000",
            "equity_usd": "10000", "margin_used_usd": "0",
            "free_margin_usd": "10000",
        },
        "symbol": {
            "observed_utc": t, "symbol": "XAUUSD", "volume_min": "0.01",
            "volume_step": "0.01", "tick_size": "0.01", "point": "0.01",
            "tick_value_loss_per_lot_usd": "1",
            "trade_stops_level": "10", "trade_freeze_level": "10",
            "incremental_margin_usd": "5",
        },
        "tick": {
            "observed_utc": t, "tick_utc": t, "symbol": "XAUUSD",
            "bid": "2000.00", "ask": "2000.20",
        },
        "ledger": {
            "observed_utc": t, "positions": [], "orders": [],
            "journal_status": "RECONCILED", "period_boundary_status": "RECONCILED",
            "complete_trade_attribution": True,
            "day_boundary_utc": "2026-10-19T00:00:00Z",
            "week_boundary_utc": "2026-10-19T00:00:00Z",
            "inception_utc": "2026-09-01T00:00:00Z",
            "day_start_equity_usd": "10000", "day_external_flows_usd": "0",
            "week_start_equity_usd": "10000", "week_external_flows_usd": "0",
            "inception_external_flows_usd": "0", "normalized_high_water_usd": "10000",
            "loss_equivalent_streak": "0",
        },
        "costs": {
            "observed_utc": t, "scope": "DEMO_LIFECYCLE_ONLY",
            "admission": "INDEPENDENTLY_ADMITTED_FOR_REPLAY",
            "components_nonoverlapping": True,
            "round_trip_commission_usd": "1", "swap_buffer_usd": "0.50",
            "slippage_buffer_usd": "1", "gap_buffer_usd": "0.50",
            "m1_current_adverse_usd": "3", "m1_stressed_adverse_usd": "6",
        },
        "guard": {
            "observed_utc": t, "session": "SUPPORTED_LONDON_NY",
            "event": "CLEAR", "shock": "NORMAL",
            "holiday": "NONE", "schedule": "BROKER_SESSION_ELIGIBLE",
            "admitted_spread_ceiling_price": "0.50",
        },
        "candidate": {
            "decision_utc": t, "symbol": "XAUUSD", "side": "BUY",
            "volume_lots": "0.01", "protective_stop": "1978.20",
        },
    }


def pins(data: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {k: evidence_sha256(v) for k, v in data.items() if k != "candidate"}


def review(data: dict[str, dict[str, Any]],
           pinned: dict[str, str] | None = None) -> object:
    return replay_full_policy_a(data, pins(data) if pinned is None else pinned,
                                _identity())


def test_synthetic_bridge_price_to_protective_stop_exact() -> None:
    result = review(bundle())
    assert result.disposition is FullRiskDisposition.ALLOW_MATH_ONLY
    assert result.l_price == 22
    assert result.l_plan == 25


def test_far_stop_rejected_by_cash_risk_not_only_m1() -> None:
    data = bundle()
    data["candidate"]["protective_stop"] = "1700.00"
    result = review(data)
    assert result.disposition is FullRiskDisposition.REJECT
    assert "POLICY_A_PER_TRADE_STOP_LOSS_USD" in result.reasons


def test_tampering_after_independent_pin_fails() -> None:
    data = bundle()
    genuine = pins(data)
    data["costs"]["commission_usd"] = "0"
    with pytest.raises(CaptureSafetyError, match="source SHA mismatch"):
        review(data, genuine)


def test_missing_period_or_unreconciled_history_fails() -> None:
    data = bundle()
    data["ledger"].pop("day_start_equity_usd")
    with pytest.raises(CaptureSafetyError, match="day_start_equity"):
        review(data)
    data = bundle()
    data["ledger"]["period_boundary_status"] = "UNKNOWN"
    with pytest.raises(CaptureSafetyError, match="accounting"):
        review(data)


@pytest.mark.parametrize(("segment", "key", "bad"), [
    ("account", "tradeapi_disabled", False),
    ("account", "login", 8888),
    ("account", "trade_mode", 2),
    ("ledger", "positions", [{"symbol": "XAUUSD"}]),
    ("ledger", "orders", None),
    ("ledger", "complete_trade_attribution", False),
    ("symbol", "trade_stops_level", None),
    ("symbol", "trade_freeze_level", "-1"),
    ("symbol", "tick_value_loss_per_lot_usd", None),
    ("tick", "bid", "2000.70"),
    ("tick", "tick_utc", "2026-10-19T13:59:54Z"),
    ("guard", "event", "UNKNOWN"),
    ("guard", "admitted_spread_ceiling_price", "0.01"),
    ("costs", "scope", "LIVE"),
    ("costs", "round_trip_commission_usd", None),
    ("costs", "components_nonoverlapping", False),
])
def test_fail_closed_broker_accounting_market_component(
    segment: str, key: str, bad: Any,
) -> None:
    data = bundle()
    data[segment][key] = bad
    with pytest.raises(CaptureSafetyError):
        review(data)


def test_same_epoch_time_skew_prevents_mixed_state() -> None:
    data = bundle()
    data["ledger"]["observed_utc"] = "2026-10-19T13:59:57Z"
    with pytest.raises(CaptureSafetyError, match="mixed epoch"):
        review(data)


def test_diverging_dollar_cost_and_event_risk_are_not_silently_zero() -> None:
    data = bundle()
    data["costs"]["gap_buffer_usd"] = "NaN"
    with pytest.raises(CaptureSafetyError, match="nonfinite"):
        review(data)
    data = bundle()
    data["guard"]["holiday"] = "WEEKLY_REOPEN"
    with pytest.raises(CaptureSafetyError, match="not eligible"):
        review(data)


def test_price_is_not_trusted_from_caller_and_cannot_buy_at_bid() -> None:
    data = bundle()
    data["candidate"]["entry_worst"] = "1999.00"
    result = review(data)
    assert result.l_price == 22
    assert result.l_plan == 25


def test_float_prices_never_reinterpreted_as_exact_account_money() -> None:
    data = bundle()
    data["tick"]["ask"] = 2000.2
    with pytest.raises(CaptureSafetyError, match="noncanonical|exact Decimal"):
        review(data)


def test_candidate_does_not_generate_an_order_or_permit() -> None:
    import inspect

    from scripts import v11_offline_risk_bridge

    source = inspect.getsource(v11_offline_risk_bridge)
    assert "import MetaTrader5" not in source
    assert "order_send(" not in source
    assert "order_check(" not in source
    assert "initialize(" not in source
    assert not hasattr(v11_offline_risk_bridge, "submit_market_order")


def test_exact_sha_uses_canonical_sorting_and_rejects_float() -> None:
    assert evidence_sha256({"b": "2", "a": "1"}) == evidence_sha256(
        {"a": "1", "b": "2"}
    )
    with pytest.raises(CaptureSafetyError):
        evidence_sha256({"x": 1.25})


def test_explicit_calibration_source_claim_is_not_external_authority() -> None:
    # The bridge is replay-only despite a caller-supplied admission string and
    # matching hashes. Never connect it to the adapter's runtime veto.
    data = copy.deepcopy(bundle())
    assert review(data).disposition is FullRiskDisposition.ALLOW_MATH_ONLY
