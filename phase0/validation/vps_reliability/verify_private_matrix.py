"""Verify a private VPS record chain and print only a publication-safe summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .private_probe import private_target
    from .private_probe_oracle import verify_private_matrix
except ImportError:
    from private_probe import private_target
    from private_probe_oracle import verify_private_matrix


def verify_output(output: Path, *, allow_incomplete: bool = False) -> dict:
    output = private_target(output)
    records_path = output / "vps_probe_records.jsonl"
    if not records_path.is_file():
        raise ValueError("private VPS record chain missing")
    records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
    result = verify_private_matrix(records)
    if (allow_incomplete
            and result["status"] == "FAIL_CLOSED"
            and result["reasons"] == ["REQUIRED_SCENARIOS_INCOMPLETE"]):
        result = dict(result)
        result["status"] = "PASS_PREFIX"
        result["reasons"] = []
        result["claim_limit"] = (
            "Valid incomplete prefix only; the VPS matrix is not complete or admitted."
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    try:
        result = verify_output(args.output, allow_incomplete=args.allow_incomplete)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] in {"PASS", "PASS_PREFIX"} else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
