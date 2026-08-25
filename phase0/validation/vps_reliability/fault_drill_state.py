"""Read-only readiness check used by the bounded G0-07 orchestrator."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

EXPECTED_STATES = {"HEALTHY", "DISCONNECTED"}


def _plain(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if hasattr(value, "_asdict"):
        return {str(key): item for key, item in value._asdict().items()}
    return None


def observe(api: Any, expected: str) -> dict[str, Any]:
    if expected not in EXPECTED_STATES:
        raise ValueError("invalid expected state")

    attached = bool(api.initialize())
    terminal = tick = None
    try:
        if attached:
            terminal = _plain(api.terminal_info())
            if expected == "HEALTHY":
                tick = _plain(api.symbol_info_tick("XAUUSD"))
    finally:
        if attached:
            api.shutdown()

    if not attached or not isinstance(terminal, dict):
        return {"status": "WAIT", "reason": "MT5_NOT_READY", "expected": expected}
    if terminal.get("tradeapi_disabled") is not True:
        return {
            "status": "FAIL_CLOSED",
            "reason": "EXTERNAL_PYTHON_TRADING_NOT_DISABLED",
            "expected": expected,
        }

    connected = terminal.get("connected")
    if expected == "DISCONNECTED":
        status = "READY" if connected is False else "WAIT"
        reason = "DISCONNECTED_OBSERVED" if status == "READY" else "STILL_CONNECTED"
        return {"status": status, "reason": reason, "expected": expected}

    if connected is not True:
        return {"status": "WAIT", "reason": "TERMINAL_NOT_CONNECTED", "expected": expected}
    tick_age = None
    if isinstance(tick, dict) and isinstance(tick.get("time_msc"), (int, float)):
        tick_age = round(
            datetime.now(timezone.utc).timestamp() - tick["time_msc"] / 1000,
            3,
        )
    if not isinstance(tick_age, (int, float)) or not -2 <= tick_age <= 30:
        return {
            "status": "WAIT",
            "reason": "FRESH_TICK_NOT_AVAILABLE",
            "expected": expected,
            "tick_age_seconds": tick_age,
        }
    return {
        "status": "READY",
        "reason": "HEALTHY_WITH_FRESH_TICK",
        "expected": expected,
        "tick_age_seconds": tick_age,
        "terminal_build": terminal.get("build"),
    }


def main() -> int:
    try:
        from .readonly_mt5 import ReadOnlyMT5
    except ImportError:
        from readonly_mt5 import ReadOnlyMT5

    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", choices=sorted(EXPECTED_STATES), required=True)
    args = parser.parse_args()
    try:
        result = observe(ReadOnlyMT5, args.expected)
        print(json.dumps(result, sort_keys=True))
        return {"READY": 0, "FAIL_CLOSED": 2, "WAIT": 3}[result["status"]]
    except (OSError, ValueError) as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
