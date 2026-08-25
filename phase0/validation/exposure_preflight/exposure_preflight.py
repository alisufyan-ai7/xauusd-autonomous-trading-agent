"""Append a private read-only exposure preflight; never mutates broker state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PHASES = {"PRE_DRILL", "POST_RECOVERY"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


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


def _safe_zero_row(row: dict[str, Any], phase: str) -> bool:
    return (
        row.get("phase") == phase
        and row.get("status") == "PASS_NO_OPEN_EXPOSURE"
        and row.get("connected") is True
        and row.get("tradeapi_disabled") is True
        and row.get("positions_count") == 0
        and row.get("pending_orders_count") == 0
        and row.get("reasons") == []
    )


def verify_reconciliation(output: Path, *, pre_sha256: str | None = None,
                          post_sha256: str | None = None) -> dict[str, Any]:
    """Verify the exact pre/post zero-exposure chain used by the R31 drill."""
    output = private_target(output)
    chain = output / "exposure_preflight_records.jsonl"
    if not chain.is_file():
        raise ValueError("exposure preflight chain missing")
    sequence, final_hash = _validate_chain(chain)
    rows = [json.loads(line) for line in chain.read_text(encoding="utf-8").splitlines()]
    reasons: list[str] = []
    if (pre_sha256 is None) != (post_sha256 is None):
        reasons.append("BOUND_PAIR_DIGESTS_INCOMPLETE")
    if pre_sha256 is None:
        if sequence != 2 or len(rows) != 2:
            reasons.append("EXACT_PRE_POST_PAIR_REQUIRED")
        selected = rows[:2]
    else:
        if not SHA256.fullmatch(pre_sha256) or not SHA256.fullmatch(str(post_sha256)):
            reasons.append("BOUND_PAIR_DIGEST_INVALID")
            selected = []
        else:
            pre_matches = [(index, row) for index, row in enumerate(rows)
                           if row.get("record_sha256") == pre_sha256]
            post_matches = [(index, row) for index, row in enumerate(rows)
                            if row.get("record_sha256") == post_sha256]
            if len(pre_matches) != 1 or len(post_matches) != 1:
                reasons.append("BOUND_PAIR_NOT_UNIQUE")
                selected = []
            else:
                pre_index, pre_row = pre_matches[0]
                post_index, post_row = post_matches[0]
                if post_index != pre_index + 1 or post_index != len(rows) - 1:
                    reasons.append("BOUND_PAIR_NOT_LATEST_CONTIGUOUS")
                selected = [pre_row, post_row]
    for index, phase in enumerate(("PRE_DRILL", "POST_RECOVERY")):
        if index >= len(selected):
            continue
        if not _safe_zero_row(selected[index], phase):
            reasons.append(f"{phase}_NOT_ZERO_SAFE")
    return {
        "status": "PASS_RECONCILED" if not reasons else "FAIL_CLOSED",
        "reasons": sorted(set(reasons)),
        "pre_record_sha256": selected[0].get("record_sha256") if selected else None,
        "post_record_sha256": selected[1].get("record_sha256") if len(selected) > 1 else None,
        "final_record_sha256": final_hash,
        "risk_authority_restored": False,
    }


def main() -> int:
    from readonly_mt5 import ReadOnlyExposureMT5

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--phase", choices=sorted(PHASES))
    group.add_argument("--verify-reconciliation", action="store_true")
    parser.add_argument("--pre-sha256")
    parser.add_argument("--post-sha256")
    args = parser.parse_args()
    try:
        result = (verify_reconciliation(
            args.output, pre_sha256=args.pre_sha256, post_sha256=args.post_sha256
        ) if args.verify_reconciliation
                  else capture(ReadOnlyExposureMT5, args.output, args.phase))
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] in {"PASS_NO_OPEN_EXPOSURE", "PASS_RECONCILED"} else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
