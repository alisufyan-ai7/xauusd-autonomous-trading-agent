"""Focused actual upgrade regressions: USD API spend, TP, early exit.

Offline fake providers only. Does not log in or send Exness orders.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

from xauusd_demo.ai_known_position_actions import AIKnownPositionActions
from xauusd_demo.continuous_coordinator import QualifiedBrokerAck
from xauusd_demo.openai_demo_advisor import OpenAIDemoAdvisor

NOW = datetime(2026, 10, 24, 12, 0, 5, tzinfo=UTC)


def _entry(advisor, key, when):
    return advisor.approve(
        setup_key=key, proposed_side="BUY", observed_utc=when,
        market={"closed_bar": when.isoformat()},
    )


def test_review_limit_is_dollars_not_32_calls(tmp_path, monkeypatch):
    with OpenAIDemoAdvisor(
        tmp_path / "reviews.sqlite",
        api_key="test-offline-only", daily_budget_usd=D("2"),
    ) as advisor:
        calls = []

        def fake(market):
            calls.append(market)
            return {
                "direction": "BUY", "regime": "TREND",
                "reason_code": "STRUCTURE_SUPPORTS_ENTRY",
                "_usage": {"input_tokens": 450, "output_tokens": 40},
            }

        monkeypatch.setattr(advisor, "_request", fake)
        for i in range(75):
            assert _entry(
                advisor, f"{i:064x}", NOW+timedelta(minutes=15*i),
            )
        assert len(calls) == 75
        rows = advisor._db.execute("SELECT COUNT(*) FROM ai_spend").fetchone()
        assert rows is not None and rows[0] == 75
        assert _entry(advisor, f"{12:064x}", NOW+timedelta(days=1))
        assert len(calls) == 75


def test_small_daily_usd_budget_prevents_unbounded_billing(
    tmp_path, monkeypatch,
):
    with OpenAIDemoAdvisor(
        tmp_path / "reviews.sqlite", api_key="test-only",
        daily_budget_usd=D("0.01"),
    ) as advisor:
        called = []

        def fake(market):
            called.append(market)
            return {
                "direction": "NO_TRADE", "regime": "UNCERTAIN",
                "reason_code": "INSUFFICIENT_EDGE",
            }

        monkeypatch.setattr(advisor, "_request", fake)
        assert not _entry(advisor, "a"*64, NOW)
        assert not _entry(advisor, "b"*64, NOW)
        assert len(called) == 1
        assert advisor.last_reason == "AI_DAILY_USD_BUDGET_PROTECTED"


def _receipt():
    return QualifiedBrokerAck(
        setup_key="a"*64, account_fingerprint="b"*64,
        position_id=51, order_ticket=21, entry_deal_ticket=31,
        side="BUY", volume_lots=D("0.01"), entry_price=D("100"),
        stop_loss=D("99"), take_profit=D("103"), tick_size=D("0.01"),
    )


class FakePositionAdvisor:
    def __init__(self, action):
        self.action = action
        self.calls = 0

    def manage_position(self, **kwargs):
        self.calls += 1
        return self.action


class FakeBroker:
    TIMEFRAME_M15 = 15
    TRADE_ACTION_SLTP = 6
    TRADE_ACTION_DEAL = 1
    TRADE_RETCODE_DONE = 10009
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_FOK = 0

    def __init__(self):
        self.position = {
            "identifier": 51, "ticket": 77, "volume": 0.01,
            "symbol": "XAUUSD", "magic": 260101, "tp": 103.0,
            "sl": 99.0,
        }
        self.writes = []

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        assert (symbol, timeframe, start, count) == ("XAUUSD", 15, 1, 4)
        return [{
            "time": int((NOW-timedelta(minutes=15*i+15, seconds=5)).timestamp()),
            "open": 100, "high": 104, "low": 99, "close": 101,
        } for i in range(4)]

    def symbol_info(self, symbol):
        return {"filling_mode": 2, "trade_stops_level": 10, "point": 0.01}

    def positions_get(self):
        return (self.position,) if self.position is not None else ()

    def order_check(self, payload):
        return {"retcode": 0}

    def order_send(self, payload):
        self.writes.append(payload.copy())
        if payload["action"] == self.TRADE_ACTION_SLTP:
            self.position["tp"] = payload["tp"]
        else:
            self.position = None
        return {"retcode": self.TRADE_RETCODE_DONE}


def test_known_tp_refinement_moves_target_closer_and_is_journaled(
    tmp_path,
):
    broker = FakeBroker()
    advisor = FakePositionAdvisor("TIGHTEN_TP")
    receipt = _receipt()
    with AIKnownPositionActions(
        tmp_path/"position.sqlite", advisor=advisor,
    ) as manager:
        target = manager.current_tp(
            receipt, now=NOW, broker_position=broker.position,
        )
        result = manager.review_and_act(
            broker, receipt, position=broker.position.copy(), now=NOW,
            bid=D("101.50"), ask=D("101.60"),
            current_stop=D("99"), current_tp=target,
            minimum_distance=D("0.10"),
        )
        assert result == "AI_TP_REFINED_CONFIRMED"
        assert target > D(str(broker.position["tp"])) > D("101.7")
        assert len(broker.writes) == 1
        assert manager.current_tp(
            receipt, now=NOW, broker_position=broker.position,
        ) == D(str(broker.position["tp"]))


def test_ai_early_exit_requires_known_position_broker_closed_receipt(
    tmp_path, monkeypatch,
):
    broker = FakeBroker()
    advisor = FakePositionAdvisor("EARLY_EXIT")
    monkeypatch.setattr(
        "xauusd_demo.ai_known_position_actions.observe_known_mt5_position",
        lambda *args, **kwargs: "CLOSED" if broker.position is None else "OPEN",
    )
    with AIKnownPositionActions(
        tmp_path/"position.sqlite", advisor=advisor,
    ) as manager:
        r = _receipt()
        result = manager.review_and_act(
            broker, r, position=broker.position.copy(), now=NOW,
            bid=D("101.50"), ask=D("101.60"),
            current_stop=D("99"), current_tp=D("103"),
            minimum_distance=D("0.10"),
        )
        assert result == "AI_EARLY_EXIT_BROKER_CONFIRMED"
        assert len(broker.writes) == 1
        assert broker.writes[0]["position"] == 77
        assert broker.writes[0]["volume"] == 0.01
        assert broker.writes[0]["type"] == broker.ORDER_TYPE_SELL
