# ruff: noqa: I001
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from xauusd_agent.features.v2_tpb_stop_plan import TPBStopPlan
from xauusd_demo.continuous_coordinator import PendingBrokerAck, QualifiedBrokerAck
from xauusd_demo.envelope import DemoSafetyError
from xauusd_demo.s2_readonly_coordinator_port import ReadOnlyS2CoordinatorPort

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)
FP = hashlib.sha256(
    b"Exness Technologies Ltd|Exness-MT5Trial15|321|USD"
).hexdigest()


def tpb(side="BUY"):
    return TPBStopPlan(
        setup_key="a"*64, side=side,
        entry_stop=D("2701") if side=="BUY" else D("2699"),
        protective_stop=D("2695") if side=="BUY" else D("2705"),
        take_profit=D("2720") if side=="BUY" else D("2680"),
        tp1_informational=D("2715") if side=="BUY" else D("2685"),
        confirmed_bar_utc=NOW, proposal_expires_utc=NOW+timedelta(seconds=30),
        expires_utc=NOW+timedelta(minutes=45),
    )


class Source:
    def __init__(self):
        self.plan = tpb()
        self.calls = 0

    def observe_closed_bar_plan(self, now):
        self.calls += 1
        return self.plan


class FakeMT5:
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_STATE_PLACED = 1
    ORDER_STATE_FILLED = 4
    ORDER_STATE_CANCELED = 2
    ORDER_STATE_EXPIRED = 3
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    DEAL_TYPE_BUY = 0
    DEAL_TYPE_SELL = 1
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1

    def __init__(self):
        self.account = dict(company="Exness Technologies Ltd",server="Exness-MT5Trial15",
                            currency="USD",login=321,trade_mode=0)
        self.terminal = {"connected":True, "tradeapi_disabled":True}
        self.order = {
            "ticket":501,"symbol":"XAUUSD","magic":260101,"type":4,
            "volume_initial":0.01,"price_open":2701.0,"sl":2695.0,"tp":2720.0,
            "time_expiration":int((NOW+timedelta(minutes=45)).timestamp()),"state":1,
        }
        self.orders=[self.order]
        self.positions=[]
        self.historic_orders=[]
        self.deals=[]
        self.calls=[]

    def terminal_info(self):
        return self.terminal

    def account_info(self):
        return self.account

    def orders_get(self):
        self.calls.append("orders_get")
        return self.orders

    def positions_get(self):
        self.calls.append("positions_get")
        return self.positions

    def history_orders_get(self, *,ticket):
        self.calls.append("history_orders_get")
        return self.historic_orders

    def history_deals_get(self, *,ticket=None,position=None):
        self.calls.append("history_deals_get")
        if position is not None:
            return self.deals
        return self.deals

    def symbol_info(self,symbol):
        return {"trade_tick_size":0.01}

    def order_send(self,*args,**kwargs):
        raise AssertionError("read-only port must never submit MT5 order")

    def order_check(self,*args,**kwargs):
        raise AssertionError("read-only port must never call order_check")


class TestAdapter:
    def __init__(self, mt5):
        self._mt5=mt5
        self._identity=SimpleNamespace(account_id_sha256=FP)
        self.calls=[]

    def _identity_guard(self, *, require_execution_enabled):
        self.calls.append("identity_guard")
        assert require_execution_enabled is False
        if self._mt5.terminal["connected"] is not True:
            raise DemoSafetyError("disconnected broker")
        a=self._mt5.account
        fp=hashlib.sha256(
            f"{a['company']}|{a['server']}|{a['login']}|{a['currency']}".encode()
        ).hexdigest()
        if a["trade_mode"] != 0 or fp != FP:
            raise DemoSafetyError("wrong account or LIVE")
        return self._mt5.terminal,a

    def _build_request(self, request, *,now):
        self.calls.append("build_request")
        request.validate()
        return {"type":4,"price":float(request.entry_stop),"sl":float(request.stop_loss),
                "tp":float(request.take_profit)}


def make_port():
    mt5=FakeMT5()
    adapter=TestAdapter(mt5)
    source=Source()
    port=ReadOnlyS2CoordinatorPort(adapter=adapter,plan_source=source)
    return port,adapter,mt5,source


def pending():
    return PendingBrokerAck(
        setup_key="a"*64,account_fingerprint=FP,order_ticket=501,
        side="BUY",volume_lots=D("0.01"),entry_stop=D("2701"),
        stop_loss=D("2695"),take_profit=D("2720"),
        expires_utc=NOW+timedelta(minutes=45),
    )


def filled():
    return QualifiedBrokerAck(
        setup_key="a"*64,account_fingerprint=FP,position_id=700,
        order_ticket=501,entry_deal_ticket=1001,side="BUY",
        volume_lots=D("0.01"),entry_price=D("2701"),
        stop_loss=D("2695"),take_profit=D("2720"),tick_size=D("0.01"),
    )


def test_unified_readonly_port_never_advertises_order_to_live_coordinator():
    port,adapter,mt5,source=make_port()
    assert port.one_cycle_proposal(NOW+timedelta(seconds=5)) is None
    assert source.calls==1
    assert "identity_guard" in adapter.calls
    assert "build_request" in adapter.calls
    assert not any(x.startswith("order_") for x in mt5.calls)


def test_inspection_binds_same_s2_request_but_submit_never_sends():
    port,_,mt5,_=make_port()
    candidate=port.inspect_closed_bar_plan(NOW+timedelta(seconds=4))
    assert candidate is not None
    assert candidate.pending_stop_request.stop_loss==D("2695")
    assert not candidate.broker_execution_permitted
    with pytest.raises(
        DemoSafetyError, match="FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED"
    ):
        port.submit_qualified(candidate.proposal,NOW+timedelta(seconds=4))
    assert not mt5.calls


def test_unified_pending_port_delegates_real_mt5_order_observation():
    port,_,mt5,_=make_port()
    state=port.known_pending_state(pending(),NOW)
    assert state.state=="PENDING" and state.fill is None
    assert "orders_get" in mt5.calls


def test_unified_pending_port_requires_deal_for_fill_and_unknown_on_ambiguity():
    port,_,mt5,_=make_port()
    mt5.orders=[]
    mt5.historic_orders=[mt5.order|{"state":mt5.ORDER_STATE_FILLED}]
    mt5.deals=[{
        "ticket":1001,"order":501,"position_id":700,"symbol":"XAUUSD",
        "entry":0,"magic":260101,"type":0,"volume":0.01,"price":2701.0,
    }]
    mt5.positions=[{
        "identifier":700,"symbol":"XAUUSD","magic":260101,
        "type":0,"volume":0.01,"sl":2695.0,"tp":2720.0,
    }]
    outcome=port.known_pending_state(pending(),NOW)
    assert outcome.state=="FILLED" and outcome.fill is not None
    assert outcome.fill.position_id==700
    mt5.positions[0]["sl"]=0
    assert port.known_pending_state(pending(),NOW).state=="UNKNOWN"


@pytest.mark.parametrize("failure",["live","wrong_login","disconnected"])
def test_unified_port_denies_bad_attached_terminal_before_read_or_submit(failure):
    port,_,mt5,_=make_port()
    if failure=="live":
        mt5.account["trade_mode"]=2
    elif failure=="wrong_login":
        mt5.account["login"]=999
    else:
        mt5.terminal["connected"]=False
    with pytest.raises(DemoSafetyError):
        port.one_cycle_proposal(NOW+timedelta(seconds=2))
    with pytest.raises(DemoSafetyError):
        port.known_pending_state(pending(),NOW)


def test_missing_position_deal_is_unknown_not_closed():
    port,_,mt5,_=make_port()
    mt5.orders=[]
    mt5.positions=[]
    mt5.deals=[]
    assert port.known_position_state(filled(),NOW)=="UNKNOWN"


def test_zero_trading_and_zero_phantom_intents_via_coordinator(tmp_path):
    from xauusd_demo.continuous_coordinator import ContinuousDemoCoordinator

    port,_,mt5,_=make_port()
    with ContinuousDemoCoordinator(tmp_path/"coordinator.sqlite", account_fingerprint=FP) as coord:
        coord.arm_attended(
            confirmation="ARM-CONTINUOUS-PRO-DEMO-XAUUSD",
            broker_flat_confirmed=True,
        )
        outcome=coord.cycle(port,now=NOW+timedelta(seconds=2))
        assert outcome.action=="NO_ORDER"
        assert coord.conn.execute(
            "SELECT COUNT(*) FROM agent_cycles"
        ).fetchone()[0]==0
    assert mt5.orders==[mt5.order]
