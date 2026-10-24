"""Focused release checks: full-session DEMO, AI cache, bounded audit, known SL.

No external OpenAI requests, no actual MT5 order API, no LIVE account.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from xauusd_demo.continuous_coordinator import QualifiedBrokerAck
from xauusd_demo.demo_forever_worker import ContinuousDemoWorker
from xauusd_demo.demo_session_guard import assess_experimental_demo_window
from xauusd_demo.envelope import DemoSafetyError
from xauusd_demo.known_broker_protection import KnownDemoProtectionManager
from xauusd_demo.openai_demo_advisor import OpenAIDemoAdvisor

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)


def test_demo_entry_window_has_no_arbitrary_ny_hours():
    # Any weekday/weekend UTC hour is eligible to be *evaluated*; MT5 tick
    # freshness/market trade mode still determines whether orders are possible.
    for hour in (0, 3, 10, 15, 23):
        now = NOW.replace(hour=hour)
        result = assess_experimental_demo_window(
            now=now, pending_expires_utc=now+timedelta(minutes=35),
        )
        assert result.allowed and not result.live_permission
    old = assess_experimental_demo_window(
        now=NOW, pending_expires_utc=NOW-timedelta(seconds=1),
    )
    assert old.allowed is False


def test_openai_response_is_cached_and_only_admits_same_side(tmp_path, monkeypatch):
    with OpenAIDemoAdvisor(tmp_path/"ai.sqlite", api_key="offline-unit") as advisor:
        seen = []
        def send(market):
            seen.append(market)
            return {
                "direction": "BUY", "regime": "TREND",
                "reason_code": "STRUCTURE_SUPPORTS_ENTRY",
            }
        monkeypatch.setattr(advisor, "_request", send)
        for _ in range(3):
            assert advisor.approve(
                setup_key="a"*64, proposed_side="BUY",
                observed_utc=NOW, market={"bar": "closed"},
            )
        assert len(seen) == 1
        assert not advisor.approve(
            setup_key="b"*64, proposed_side="SELL",
            observed_utc=NOW, market={"bar": "closed"},
        )


def test_openai_api_failure_is_no_trade_and_not_retried_for_same_setup(
    tmp_path, monkeypatch,
):
    with OpenAIDemoAdvisor(tmp_path/"ai.sqlite", api_key="offline-unit") as advisor:
        calls = []
        def failure(market):
            calls.append(market)
            raise OSError("offline")
        monkeypatch.setattr(advisor, "_request", failure)
        for _ in range(2):
            assert advisor.approve(
                setup_key="c"*64, proposed_side="BUY", observed_utc=NOW,
                market={"bar": "closed"},
            ) is False
        assert len(calls) == 1


def test_log_repeats_suppressed_but_state_changes_retained(tmp_path):
    worker = ContinuousDemoWorker(
        coordinator=None, port=None, watchdog=None,
        state_directory=tmp_path, polling_seconds=5,
    )
    data = {
        "utc": NOW.isoformat(), "state": "ACTIVE", "action": "NO_ORDER",
        "reason": "NO_QUALIFIED_TPB_SETUP",
        "strategy_status": "NO_M15_BAR",
    }
    worker._write_audit(data)
    for i in range(1, 14):
        worker._write_audit({
            **data, "utc": (NOW+timedelta(seconds=5*i)).isoformat(),
        })
    worker._write_audit({
        **data, "utc": (NOW+timedelta(seconds=75)).isoformat(),
        "action": "PENDING_ORDER_FILLED",
    })
    assert len((tmp_path/"cycles.jsonl").read_text().splitlines()) == 2


def receipt():
    return QualifiedBrokerAck(
        setup_key="s"*64, account_fingerprint="a"*64,
        position_id=51, order_ticket=21, entry_deal_ticket=31,
        side="BUY", volume_lots=D("0.01"), entry_price=D("100"),
        stop_loss=D("99"), take_profit=D("103"), tick_size=D("0.01"),
    )


class PositionBroker:
    TRADE_ACTION_SLTP = 6
    TRADE_RETCODE_DONE = 10009

    def __init__(self):
        self.position = {
            "identifier": 51, "ticket": 77, "symbol": "XAUUSD",
            "magic": 260101, "sl": 99.0, "tp": 103.0,
        }
        self.calls = 0
        self.return_uncertain = False

    def positions_get(self):
        return (self.position,)

    def orders_get(self):
        return ()

    def symbol_info_tick(self, symbol):
        return {
            "time_msc": int(NOW.timestamp()*1000),
            "bid": 101.51, "ask": 101.61,
        }

    def symbol_info(self, symbol):
        return {
            "point": 0.01,
            "trade_stops_level": 3, "trade_freeze_level": 0,
        }

    def order_check(self, payload):
        return {"retcode": 0}

    def order_send(self, payload):
        self.calls += 1
        if self.return_uncertain:
            return None
        self.position["sl"] = payload["sl"]
        return {"retcode": self.TRADE_RETCODE_DONE}


class PositionAdapter:
    def __init__(self):
        self._mt5 = PositionBroker()
    def _identity_guard(self, *, require_execution_enabled):
        assert require_execution_enabled


def test_known_broker_only_tightens_stop_once(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "xauusd_demo.known_broker_protection.observe_known_mt5_position",
        lambda *args, **kwargs: "OPEN",
    )
    adapter = PositionAdapter()
    with KnownDemoProtectionManager(
        tmp_path/"position.sqlite", adapter=adapter,
    ) as manager:
        first = manager.observe_and_manage(receipt(), now=NOW)
        assert first.state == "OPEN"
        assert first.action == "BROKER_STOP_TIGHTENED"
        assert adapter._mt5.position["sl"] > 99
        assert adapter._mt5.calls == 1
        next_result = manager.observe_and_manage(
            receipt(), now=NOW+timedelta(seconds=1),
        )
        assert next_result.state == "OPEN"
        assert adapter._mt5.calls == 1


def test_uncertain_slpt_update_can_never_be_sent_twice(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "xauusd_demo.known_broker_protection.observe_known_mt5_position",
        lambda *args, **kwargs: "OPEN",
    )
    adapter = PositionAdapter()
    adapter._mt5.return_uncertain = True
    with KnownDemoProtectionManager(
        tmp_path/"position.sqlite", adapter=adapter,
    ) as manager:
        with pytest.raises(DemoSafetyError):
            manager.observe_and_manage(receipt(), now=NOW)
        with pytest.raises(DemoSafetyError):
            manager.observe_and_manage(receipt(), now=NOW)
        assert adapter._mt5.calls == 1
