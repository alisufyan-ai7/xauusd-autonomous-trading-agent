"""No-network, synthetic-only tests for attended DEMO recovery.

No MetaTrader5 module import, no broker connection, no real task mutation.
"""
from __future__ import annotations

import hashlib
import importlib.util
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from xauusd_demo.continuous_coordinator import ContinuousDemoCoordinator
from xauusd_demo.ops_safety_watchdog import PersistentDemoSafetyWatchdog

CODE = Path(__file__).resolve().parents[1] / "scripts" / "attended_demo_recovery_core.py"
spec = importlib.util.spec_from_file_location("attended_demo_recovery_core", CODE)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

NOW = datetime(2026, 10, 26, 16, 52, 5, tzinfo=UTC)
BROKER = "Exness Technologies Ltd"
SERVER = "Exness-MT5Trial15"
CURRENCY = "USD"
LOGIN = "synthetic"
FP = hashlib.sha256(f"{BROKER}|{SERVER}|{LOGIN}|{CURRENCY}".encode()).hexdigest()


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    SYMBOL_TRADE_MODE_FULL = 4
    TIMEFRAME_M15 = 15

    def __init__(self):
        self.positions = []
        self.orders = []
        self.deals = []
        self.history_orders = []
        self.initialized = False
        self.shut_down = False
        self.order_send_calls = 0

    def initialize(self, *, path, timeout):
        assert path == "synthetic-existing-terminal64.exe"
        assert timeout == 10000
        self.initialized = True
        return True

    def shutdown(self):
        self.shut_down = True

    def terminal_info(self):
        return SimpleNamespace(connected=True, tradeapi_disabled=False)

    def account_info(self):
        return SimpleNamespace(
            trade_mode=0, company=BROKER, server=SERVER,
            currency=CURRENCY, login=LOGIN,
        )

    def positions_get(self):
        return self.positions

    def orders_get(self):
        return self.orders

    def history_deals_get(self, *_):
        return self.deals

    def history_orders_get(self, *_):
        return self.history_orders

    def symbol_info(self, symbol):
        assert symbol == "XAUUSD"
        return SimpleNamespace(trade_mode=self.SYMBOL_TRADE_MODE_FULL)

    def symbol_info_tick(self, symbol):
        assert symbol == "XAUUSD"
        return SimpleNamespace(time_msc=int((NOW - timedelta(seconds=1)).timestamp()*1000))

    def copy_rates_from_pos(self, symbol, frame, pos, count):
        assert (symbol, frame, pos, count) == ("XAUUSD", 15, 1, 2)
        return [{"time":int(NOW.replace(minute=30,second=0).timestamp())}]

    def order_send(self, *_args, **_kwargs):
        self.order_send_calls += 1
        raise AssertionError("recovery must never call order_send")


def prepare(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "EXPECTED_ACCOUNT_SHA256", FP)
    state = tmp_path / "state"
    state.mkdir()
    coord_path = state / "coordinator.sqlite"
    with ContinuousDemoCoordinator(coord_path, account_fingerprint=FP) as coord:
        coord.arm_attended(
            confirmation="ARM-CONTINUOUS-PRO-DEMO-XAUUSD",
            broker_flat_confirmed=True,
        )
        coord._quarantine("SOURCE_OR_FEATURE_EXCEPTION")
    with PersistentDemoSafetyWatchdog(state / "watchdog.sqlite", max_age_seconds=1800) as w:
        w.arm_attended(
            now=NOW - timedelta(days=1),
            confirmation_phrase="P1-ARM-DEMO-WATCHDOG",
        )
    with sqlite3.connect(state / "control.sqlite") as db:
        db.execute(
            "CREATE TABLE demo_control (singleton_id INTEGER, state TEXT, account_id_sha256 TEXT)"
        )
        db.execute(
            "INSERT INTO demo_control VALUES (1,'ACTIVE',?)", (FP,),
        )
    with sqlite3.connect(state / "requests.sqlite") as db:
        db.execute("CREATE TABLE demo_submission (status TEXT)")
    for name in module.JOURNALS:
        if not (state / name).is_file():
            sqlite3.connect(state / name).close()
    (state / "cycles.jsonl").write_text('{"sanitized":"before"}\n')
    (state / "openai_key.dpapi").write_text("synthetic_not_real_secret")
    vault = tmp_path / "private"
    vault.mkdir()
    return state, vault


def status(state, name, query):
    with sqlite3.connect(state / name) as db:
        return db.execute(query).fetchone()[0]


def test_attended_recovery_backs_up_preserves_and_rearms_only_two_controls(
    tmp_path, monkeypatch,
):
    state, vault = prepare(tmp_path, monkeypatch)
    fake = FakeMT5()
    module.attended_recover(
        state, vault, "synthetic-existing-terminal64.exe",
        fake, now_func=lambda: NOW,
    )
    assert fake.initialized and fake.shut_down
    assert fake.order_send_calls == 0
    assert status(state,"coordinator.sqlite","SELECT state FROM agent_control") == "ACTIVE"
    assert status(state,"watchdog.sqlite","SELECT state FROM watchdog") == "ACTIVE"
    assert status(vault,"coordinator.sqlite","SELECT state FROM agent_control") == "QUARANTINED"
    assert status(vault,"watchdog.sqlite","SELECT state FROM watchdog") == "ACTIVE"
    assert (vault/"cycles.jsonl").read_text() == '{"sanitized":"before"}\n'
    assert not (vault/"openai_key.dpapi").exists()
    assert (vault/"recovery_prestate_manifest.json").is_file()
    assert status(state,"coordinator.sqlite","SELECT COUNT(*) FROM agent_cycles") == 0
    assert status(state,"watchdog.sqlite","SELECT COUNT(*) FROM incident_outbox") == 1


@pytest.mark.parametrize("failure",["foreign_position","historical_order","wrong_account","stale_tick"])
def test_recovery_rejects_broker_or_account_uncertainty_without_state_change(
    tmp_path, monkeypatch, failure,
):
    state, vault = prepare(tmp_path, monkeypatch)
    fake = FakeMT5()
    if failure == "foreign_position":
        fake.positions = [object()]
    elif failure == "historical_order":
        fake.history_orders = [object()]
    elif failure == "wrong_account":
        fake.account_info = lambda: SimpleNamespace(
            trade_mode=2, company="Other", server="other",
            currency=CURRENCY, login=LOGIN,
        )
    else:
        fake.symbol_info_tick = lambda symbol: SimpleNamespace(time_msc=123)
    with pytest.raises(module.RecoveryHold):
        module.attended_recover(
            state,vault,"synthetic-existing-terminal64.exe",
            fake,now_func=lambda:NOW,
        )
    assert fake.shut_down
    assert status(state,"coordinator.sqlite","SELECT state FROM agent_control") == "QUARANTINED"
    assert status(state,"watchdog.sqlite","SELECT state FROM watchdog") == "ACTIVE"
    assert list(vault.iterdir()) == []


def test_prior_broker_intent_blocks_recovery_even_when_broker_current_flat(
    tmp_path, monkeypatch,
):
    state,vault=prepare(tmp_path,monkeypatch)
    with sqlite3.connect(state/"coordinator.sqlite") as db:
        db.execute(
            "INSERT INTO agent_cycles(setup_key,stage,side,bar_utc,ticket) VALUES (?,?,?,?,?)",
            ("a"*64,"PREPARING","BUY",NOW.isoformat(),None),
        )
    fake=FakeMT5()
    with pytest.raises(module.RecoveryHold,match="ORDER_INTENT"):
        module.attended_recover(
            state,vault,"synthetic-existing-terminal64.exe",
            fake,now_func=lambda:NOW,
        )
    assert status(state,"coordinator.sqlite","SELECT state FROM agent_control") == "QUARANTINED"
    assert fake.order_send_calls==0
