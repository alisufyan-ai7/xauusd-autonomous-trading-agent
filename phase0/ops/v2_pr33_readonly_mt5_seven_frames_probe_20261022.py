"""Attended XAUUSD Exness Pro DEMO seven-frame observation: READ ONLY.

PROSPECTIVE DIAGNOSTIC ONLY. Not executed or admitted on the owner's VPS.
Run only from a reviewed exact source tree with an already connected MT5
DEMO profile and external-Python automated trading protection ENABLED
(tradeapi_disabled=True). No login, order APIs, symbol selection or writes.
Output is sanitized; NEVER print MT5 account login or credentials.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from xauusd_agent.broker.v2_mt5_context_readonly import MT5ExtendedReadOnlyAdapter
from xauusd_agent.features.v2_market_context import ContextTimeframe

# Fingerprint only, from the previously owner-reported, read-only DEMO preflight.
# The fingerprint computation algorithm must match before source admission.
ADMITTED_FINGERPRINT = (
    "9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91"
)
ADMITTED_SERVER = "Exness-MT5Trial15"
ADMITTED_COMPANY = "Exness Technologies Ltd"

READ_COUNTS = {
    ContextTimeframe.W1: 104,
    ContextTimeframe.D1: 180,
    ContextTimeframe.H4: 300,
    ContextTimeframe.H1: 500,
    ContextTimeframe.M15: 1000,
    ContextTimeframe.M5: 300,
    ContextTimeframe.M1: 300,
}


def capture() -> dict[str, object]:
    as_of = datetime.now(UTC)
    with MT5ExtendedReadOnlyAdapter(
        admitted_fingerprint_sha256=ADMITTED_FINGERPRINT,
        admitted_server=ADMITTED_SERVER,
        admitted_company=ADMITTED_COMPANY,
    ) as reader:
        # Capture the quote first. Reading seven historical series can take
        # seconds, so sampling tick LAST against the earlier as_of would
        # wrongly reject healthy active-market data as future-dated.
        quote = reader.read_latest_quote(symbol="XAUUSD", as_of=as_of)
        if quote is None:
            raise RuntimeError("XAUUSD quote unavailable; source proof incomplete")
        quote_age = (as_of - quote.broker_time).total_seconds()
        if quote_age < -0.25 or quote_age > 5:
            raise RuntimeError("quote timestamp unavailable, stale or future-dated")
        frames = reader.read_seven_frames(as_of=as_of, limits=READ_COUNTS)
        # Identity and disabled trading are rechecked after observation.
        reader._guard_demo_identity()
        out: dict[str, object] = {
            "status": "READ_ONLY_EXTENDED_MARKET_CAPTURE_ONLY_NOT_TRADING_ADMISSION",
            "symbol": "XAUUSD",
            "account_fingerprint_sha256": ADMITTED_FINGERPRINT,
            "company": ADMITTED_COMPANY,
            "server": ADMITTED_SERVER,
            "trade_mode": "DEMO",
            "external_python_trading_disabled": True,
            "observed_utc": as_of.isoformat(),
            "quote_age_seconds": round((as_of - quote.broker_time).total_seconds(), 3),
            "bars": {},
            "order_api_calls": 0,
            "execution_enabled": False,
        }
        result: dict[str, object] = {}
        for timeframe, series in frames.items():
            if not series:
                raise RuntimeError(f"{timeframe.value} empty broker result")
            if series[-1].close_time > as_of:
                raise RuntimeError(f"{timeframe.value} contains a forming candle")
            result[timeframe.value] = {
                "requested": READ_COUNTS[timeframe],
                "observed": len(series),
                "oldest_open_utc": series[0].open_time.isoformat(),
                "latest_closed_utc": series[-1].close_time.isoformat(),
                "latest_age_seconds": int((as_of - series[-1].close_time).total_seconds()),
            }
        out["bars"] = result
        return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sanitized read-only seven-timeframe MT5 DEMO observation"
    )
    parser.add_argument(
        "--confirm-readonly",
        action="store_true",
        help="Attest that MT5 is on dedicated project DEMO with trading API disabled",
    )
    args = parser.parse_args()
    if not args.confirm_readonly:
        print("NOT_EXECUTED_REQUIRE_CONFIRM_READONLY")
        return 2
    try:
        result = capture()
    except Exception as exc:
        # Error class only: broker exceptions can contain raw account identifiers.
        print(json.dumps({
            "status": "FAIL_CLOSED_NO_ORDER",
            "error_type": type(exc).__name__,
            "order_api_calls": 0,
        }, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
