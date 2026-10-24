"""Attended Windows VPS Exness Pro DEMO risk observation; no broker orders."""

from __future__ import annotations

import argparse
import importlib
import json
from datetime import UTC, datetime

from xauusd_demo.broker_money_readonly import inspect_real_demo_money


def main() -> int:
    parser = argparse.ArgumentParser(description="EXNESS DEMO no-order broker-money capture")
    parser.add_argument("--confirm-readonly", action="store_true")
    args = parser.parse_args()
    if not args.confirm_readonly:
        print("NOT_RUN_REQUIRES_EXPLICIT_READ_ONLY_CONFIRMATION")
        return 2
    mt5 = None
    initialized = False
    try:
        mt5 = importlib.import_module("MetaTrader5")
        if not mt5.initialize():
            raise RuntimeError("connected MT5 terminal initialization failed")
        initialized = True
        result = inspect_real_demo_money(mt5, now=datetime.now(UTC))
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        # Never expose exception messages that may contain account or login data.
        print(json.dumps({
            "status": "FAIL_CLOSED_NO_ORDER",
            "error_type": type(exc).__name__,
            "order_check_calls": 0,
            "order_send_calls": 0,
        }, sort_keys=True))
        return 1
    finally:
        if initialized and mt5 is not None:
            mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
