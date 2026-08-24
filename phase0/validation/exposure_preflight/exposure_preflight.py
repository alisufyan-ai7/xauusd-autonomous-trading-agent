"""Append a private read-only exposure preflight; never mutates broker state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PHASES = {"PRE_DRILL", "POST_RECOVERY"}


def private_target(path: Path) -> Path:
    target = path.resolve()
    repo = Path(__file__).resolve().parents[3]
    if target == repo or repo in target.parents:
        raise ValueError("private output must be outside repository")
    return target


def _plain(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if hasattr(value, "_asdict"):
        return {str(key): item for key, item in value._asdict().items()}
    return None


def _validate_chain(path: Path) -> tuple[int, str]:
    sequence = 0
    prior = "0" * 64
    if not path.exists():
        return sequence, prior
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        recorded = row.pop("record_sha256", None)
        actual = hashlib.sha256(
            json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if (row.get("sequence") != sequence
                or row.get("prior_record_sha256") != prior
                or recorded != actual):
            raise ValueError("existing exposure chain invalid")
        sequence += 1
        prior = actual
    return sequence, prior


def capture(api: Any, output: Path, phase: str) -> dict[str, Any]:
    if phase not in PHASES:
        raise ValueError("invalid preflight phase")
    output = private_target(output)
    output.mkdir(parents=True, exist_ok=True)
    chain = output / "exposure_preflight_records.jsonl"
    sequence, prior = _validate_chain(chain)

    attached = bool(api.initialize())
    terminal = positions = orders = None
    try:
        if attached:
            terminal = _plain(api.terminal_info())
            positions = api.positions_get()
            orders = api.orders_get()
    finally:
        if attached:
            api.shutdown()

    reasons: list[str] = []
    if not attached:
        reasons.append("MT5_INITIALIZE_FAILED")
    if not isinstance(terminal, dict) or terminal.get("connected") is not True:
        reasons.append("TERMINAL_NOT_CONNECTED")
    if not isinstance(terminal, dict) or terminal.get("tradeapi_disabled") is not True:
        reasons.append("EXTERNAL_PYTHON_TRADING_NOT_DISABLED")
    positions_count = len(positions) if isinstance(positions, (tuple, list)) else None
    orders_count = len(orders) if isinstance(orders, (tuple, list)) else None
    if positions_count is None or orders_count is None:
        reasons.append("EXPOSURE_STATE_UNKNOWN")
    else:
        if positions_count:
            reasons.append("OPEN_POSITIONS_PRESENT")
        if orders_count:
            reasons.append("PENDING_ORDERS_PRESENT")

    status = "PASS_NO_OPEN_EXPOSURE" if not reasons else "FAIL_CLOSED"
    row = {
        "schema": "gate0-exposure-preflight-1.0",
        "sequence": sequence,
        "prior_record_sha256": prior,
        "phase": phase,
        "observed_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "attached": attached,
        "connected": terminal.get("connected") if isinstance(terminal, dict) else None,
        "tradeapi_disabled": terminal.get("tradeapi_disabled") if isinstance(terminal, dict) else None,
        "positions_count": positions_count,
        "pending_orders_count": orders_count,
        "status": status,
        "reasons": sorted(reasons),
        "claim_limit": "Read-only exposure counts; no broker mutation or trading authority.",
    }
    digest = hashlib.sha256(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    row["record_sha256"] = digest
    with chain.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return {
        "status": status,
        "phase": phase,
        "positions_count": positions_count,
        "pending_orders_count": orders_count,
        "record_sha256": digest,
        "reasons": sorted(reasons),
    }


def main() -> int:
    from readonly_mt5 import ReadOnlyExposureMT5

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=sorted(PHASES), required=True)
    args = parser.parse_args()
    try:
        result = capture(ReadOnlyExposureMT5, args.output, args.phase)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "PASS_NO_OPEN_EXPOSURE" else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
