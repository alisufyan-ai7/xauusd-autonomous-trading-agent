"""Static first-DEMO-order release invariant: fail if S2 cash-risk stop disappears.

Do not import MT5, never instantiate demo adapter, and never send broker orders.
The script intentionally returns a successful *test* while reporting
NOT_ADMITTED. The test being green is not activation authority.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "demo_adapter/src/xauusd_demo/mt5_demo.py"
GUARD_TEXT = "FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED"
LIVE = REPO / "src/xauusd_agent"

code = SOURCE.read_text(encoding="utf-8")
tree = ast.parse(code)
methods = [
    node
    for node in ast.walk(tree)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and node.name == "submit_market_order"
]
reasons: list[str] = []
if len(methods) != 1:
    reasons.append("RELEASE_SUBMISSION_METHOD_MISSING_OR_DUPLICATE")
else:
    method = methods[0]
    text = ast.get_source_segment(code, method) or ""
    guard = text.find(GUARD_TEXT)
    check = text.find("self._mt5.order_check(")
    send = text.find("self._mt5.order_send(")
    if guard < 0 or check < 0 or send < 0 or not (guard < check < send):
        reasons.append("MANDATORY_FULL_POLICY_A_STOP_MISSING_OR_ORDERED_UNSAFELY")
    if "raise DemoSafetyError(" not in text[guard:check]:
        reasons.append("FULL_POLICY_A_STOP_NO_LONGER_RAISES")
if not (REPO / "demo_adapter/src/xauusd_demo/control.py").is_file():
    reasons.append("DURABLE_CONTROL_MISSING")
if not (REPO / "demo_adapter/src/xauusd_demo/ledger.py").is_file():
    reasons.append("DURABLE_SUBMISSION_LEDGER_MISSING")
if any("order_send(" in f.read_text(encoding="utf-8") for f in LIVE.rglob("*.py")):
    reasons.append("MAIN_PRODUCTION_PACKAGE_GAINED_ORDER_SEND")
status = (
    "RELEASE_TEST_INVARIANTS_FAIL"
    if reasons else "PASS_STATIC_STOP_PRESENT__FIRST_DEMO_ORDER_NOT_ADMITTED"
)
print(json.dumps({
    "status": status,
    "real_order_api_calls": 0,
    "real_demo_trade_activated": False,
    "external_python_trading_toggle": "UNCHANGED",
    "owner_first_demo_order_release_permit": "NOT_ADMITTED",
    "missing_conditions": [
        "FULL_BROKER_AUTHENTICATED_POLICY_A_CASH_SOURCE",
        "COMPLETE_OBJECTIVE_TPB_SIGNAL",
        "OFFICIAL_EVENT_GUARD_LIVE_SOURCE",
        "BROKER_DEAL_AND_KNOWN_POSITION_RECONCILIATION",
        "ACTUAL_ALERT_AND_RESTART_TESTS",
        "SEPARATE_EXACT_OWNER_ORDER_APPROVAL",
    ],
    "static_errors": reasons,
}, sort_keys=True))
raise SystemExit(1 if reasons else 0)
