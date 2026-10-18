"""OFFLINE replay-only Policy A evidence bridge; never authorizes a broker order.

Integrity checking of a caller-pinned source does NOT authenticate the external
broker, fee schedules, ledger or events. The production submission veto stays.
All validation is deterministic and has no import of MT5, network or filesystem.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from xauusd_agent.risk.full_policy_a import (
    FullPolicyAInput,
    FullPolicyAResult,
    evaluate_full_policy_a,
)

from scripts.v11_readonly_collector import CaptureSafetyError

SEGMENTS = ("account", "symbol", "tick", "ledger", "costs", "guard")


def _canonical(value: object) -> bytes:
    def validate(value: object) -> None:
        if type(value) is dict:
            for key, item in value.items():
                if type(key) is not str:
                    raise CaptureSafetyError("non-string evidence key")
                validate(item)
        elif type(value) is list:
            for item in value:
                validate(item)
        elif type(value) not in (str, int, bool, type(None)):
            raise CaptureSafetyError("noncanonical/float source evidence")
    validate(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def evidence_sha256(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _money(data: Mapping[str, Any], name: str) -> Decimal:
    value = data.get(name)
    if type(value) is not str:
        raise CaptureSafetyError(f"{name}: exact Decimal string required")
    try:
        result = Decimal(value)
    except Exception as exc:
        raise CaptureSafetyError(f"{name}: invalid decimal") from exc
    if not result.is_finite():
        raise CaptureSafetyError(f"{name}: nonfinite decimal")
    return result


def _utc(raw: object, field: str) -> datetime:
    if type(raw) is not str:
        raise CaptureSafetyError(f"{field}: missing UTC time")
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureSafetyError(f"{field}: invalid UTC time") from exc
    if ts.tzinfo is None or ts.utcoffset() != timedelta(0):
        raise CaptureSafetyError(f"{field}: not UTC")
    return ts.astimezone(UTC)


def _require(condition: bool, error: str) -> None:
    if not condition:
        raise CaptureSafetyError(error)


def replay_full_policy_a(
    bundle: Mapping[str, Any],
    independent_pins: Mapping[str, str],
    expected_fingerprint_sha256: str,
) -> FullPolicyAResult:
    """Derive cash risk from *synthetic replay* records without trusting booleans.

    Pins must be obtained independently in the future and are not a substitute
    for authenticated broker, history, Event Guard or account-specific costs.
    Any validation failure RAISES, never creates an admission/permit.
    """
    _require(type(expected_fingerprint_sha256) is str
             and len(expected_fingerprint_sha256) == 64
             and all(ch in "0123456789abcdef" for ch in expected_fingerprint_sha256),
             "invalid independently pinned account fingerprint")
    _require(set(bundle) == set(SEGMENTS) | {"candidate"},
             "bundle segments missing/unknown")
    _require(set(independent_pins) == set(SEGMENTS),
             "missing independently supplied source digests")
    records: dict[str, dict[str, Any]] = {}
    for name in SEGMENTS:
        value = bundle[name]
        _require(type(value) is dict, f"{name} must be one canonical object")
        pin = independent_pins[name]
        _require(type(pin) is str and len(pin) == 64
                 and all(ch in "0123456789abcdef" for ch in pin),
                 f"{name}: invalid pin")
        _require(evidence_sha256(value) == pin, f"{name}: source SHA mismatch")
        records[name] = value

    account = records["account"]
    symbol = records["symbol"]
    tick = records["tick"]
    ledger = records["ledger"]
    costs = records["costs"]
    guard = records["guard"]
    proposal = bundle["candidate"]
    _require(type(proposal) is dict, "candidate record must be canonical")

    now = _utc(proposal.get("decision_utc"), "candidate decision")
    _require(now.weekday() < 5, "weekend/reopen regime not independently eligible")
    for name, record in records.items():
        source_time = _utc(record.get("observed_utc"), name + " observed")
        _require(timedelta(0) <= now - source_time <= timedelta(seconds=2),
                 name + ": stale/future/mixed epoch")

    _require(account.get("company") == "Exness Technologies Ltd"
             and account.get("server") == "Exness-MT5Trial15"
             and account.get("currency") == "USD"
             and account.get("trade_mode") == 0
             and account.get("connected") is True
             and account.get("tradeapi_disabled") is True,
             "broker/terminal identity or execution-disabled state unknown")
    login = account.get("login")
    _require(type(login) is int and login > 0, "invalid account identity")
    fp = hashlib.sha256(
        f"{account['company']}|{account['server']}|{login}|USD".encode()
    ).hexdigest()
    _require(fp == expected_fingerprint_sha256, "demo fingerprint mismatch")

    _require(symbol.get("symbol") == "XAUUSD"
             and tick.get("symbol") == "XAUUSD"
             and proposal.get("symbol") == "XAUUSD",
             "symbol mismatch")
    _require(ledger.get("positions") == [] and ledger.get("orders") == []
             and ledger.get("journal_status") == "RECONCILED"
             and ledger.get("period_boundary_status") == "RECONCILED",
             "unknown/unowned exposure or accounting")
    _require(ledger.get("complete_trade_attribution") is True,
             "streak trade attribution incomplete")
    day_start = _utc(ledger.get("day_boundary_utc"), "day boundary")
    week_start = _utc(ledger.get("week_boundary_utc"), "week boundary")
    inception = _utc(ledger.get("inception_utc"), "strategy inception")
    _require(inception <= week_start <= day_start <= now,
             "missing or contradictory UTC boundaries")
    _require(costs.get("scope") == "DEMO_LIFECYCLE_ONLY"
             and costs.get("admission") == "INDEPENDENTLY_ADMITTED_FOR_REPLAY"
             and costs.get("components_nonoverlapping") is True,
             "unadmitted or overlapping cost proof")
    _require(guard.get("session") == "SUPPORTED_LONDON_NY"
             and guard.get("event") == "CLEAR"
             and guard.get("shock") == "NORMAL"
             and guard.get("holiday") == "NONE"
             and guard.get("schedule") == "BROKER_SESSION_ELIGIBLE",
             "market/session event not eligible")

    bid = _money(tick, "bid")
    ask = _money(tick, "ask")
    spread_cap = _money(guard, "admitted_spread_ceiling_price")
    tick_size = _money(symbol, "tick_size")
    point = _money(symbol, "point")
    volume = _money(proposal, "volume_lots")
    side = proposal.get("side")
    _require(side in ("BUY", "SELL"), "invalid side")
    _require(bid > 0 and ask > bid and spread_cap > 0
             and ask - bid <= spread_cap, "invalid or widened quote")
    tick_seen = _utc(tick.get("tick_utc"), "tick timestamp")
    _require(timedelta(0) <= now - tick_seen <= timedelta(seconds=2),
             "broker tick is stale")
    stop = _money(proposal, "protective_stop")
    _require(tick_size > 0 and point > 0, "tick and point metadata invalid")
    _require(stop > 0 and stop % tick_size == 0, "stop not normalized to tick grid")
    entry = ask if side == "BUY" else bid
    _require(entry > stop if side == "BUY" else entry < stop,
             "stop not adverse")
    stop_level = _money(symbol, "trade_stops_level")
    freeze_level = _money(symbol, "trade_freeze_level")
    _require(stop_level >= 0 and freeze_level >= 0, "invalid stop/freeze metadata")
    reference = bid if side == "BUY" else ask
    actual_distance = reference - stop if side == "BUY" else stop - reference
    _require(actual_distance >= max(stop_level, freeze_level) * point,
             "broker protective stop distance is invalid")

    # Caller supplies signed/verified cashflow journal values in a future
    # independent process. This replay engine rejects absent boundaries; it
    # does not certify the external origin of the supplied journal.
    data = FullPolicyAInput(
        symbol="XAUUSD", side=side, volume_lots=volume,
        volume_min=_money(symbol, "volume_min"),
        volume_step=_money(symbol, "volume_step"),
        entry_worst=entry, stop_adverse=stop, tick_size=tick_size,
        tick_value_loss_per_lot_usd=_money(symbol, "tick_value_loss_per_lot_usd"),
        commission_usd=_money(costs, "round_trip_commission_usd"),
        swap_buffer_usd=_money(costs, "swap_buffer_usd"),
        slippage_buffer_usd=_money(costs, "slippage_buffer_usd"),
        gap_buffer_usd=_money(costs, "gap_buffer_usd"),
        balance_usd=_money(account, "balance_usd"),
        equity_usd=_money(account, "equity_usd"),
        margin_used_usd=_money(account, "margin_used_usd"),
        free_margin_usd=_money(account, "free_margin_usd"),
        incremental_margin_usd=_money(symbol, "incremental_margin_usd"),
        m1_current_adverse_cost_usd=_money(costs, "m1_current_adverse_usd"),
        m1_stressed_adverse_cost_usd=_money(costs, "m1_stressed_adverse_usd"),
        # Strict empty-exposure reconciliation; never default unknown to zero.
        concurrent_committed_usd=Decimal(0),
        existing_incremental_loss_usd=Decimal(0),
        day_start_equity_usd=_money(ledger, "day_start_equity_usd"),
        day_external_flows_usd=_money(ledger, "day_external_flows_usd"),
        week_start_equity_usd=_money(ledger, "week_start_equity_usd"),
        week_external_flows_usd=_money(ledger, "week_external_flows_usd"),
        inception_external_flows_usd=_money(ledger, "inception_external_flows_usd"),
        normalized_high_water_usd=_money(ledger, "normalized_high_water_usd"),
        loss_equivalent_streak=_money(ledger, "loss_equivalent_streak"),
        snapshot_reconciled=True, accounting_reconciled=True,
        exposure_known_and_owned=True, sources_verified=True,
        symbol_verified=True, calibration_admitted=True,
        session_event_guard_pass=True, protective_stop_broker_confirmable=True,
    )
    return evaluate_full_policy_a(data)
