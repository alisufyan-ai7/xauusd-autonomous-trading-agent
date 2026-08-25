"""Create an offline A1 canary and receipt template without sending messages."""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from .alert_oracle import canary_digest
except ImportError:
    from alert_oracle import canary_digest


def private_target(path: Path) -> Path:
    target=path.resolve()
    repo=Path(__file__).resolve().parents[3]
    if target == repo or repo in target.parents:
        raise ValueError("private output must be outside the repository")
    return target


def prepare(output: Path, *, created_utc: str | None = None) -> dict[str, str]:
    """Create a fresh private canary bundle and return its public-safe fields."""
    output = private_target(output)
    output.mkdir(parents=True, exist_ok=False)
    nonce = secrets.token_urlsafe(24)
    digest = canary_digest(nonce)
    created = created_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    challenge = {
        "schema": "a1-private-canary-1.0",
        "created_utc": created,
        "nonce": nonce,
        "canary_sha256": digest,
        "channels": ["EMAIL", "TELEGRAM_PUSH"],
        "repeat_minutes": [0, 5, 10, 15],
        "ack_deadline_minutes": 15,
        "claim_limit": "Private canary preparation only; no trading authority.",
    }
    template = {
        "schema": "a1-private-delivery-evidence-1.0",
        "created_utc": created,
        "canary_sha256": digest,
        "designated_ack_role": "OWNER_DESIGNEE",
        "local_audit_record_sha256": None,
        "local_audit_chain_valid": False,
        "receipts": [],
        "acknowledged_utc": None,
        "ack_canary_sha256": digest,
    }
    (output / "PRIVATE_CANARY.json").write_text(
        json.dumps(challenge, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "PRIVATE_RECEIPT_TEMPLATE.json").write_text(
        json.dumps(template, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"status": "PREPARED_NOT_SENT", "canary_sha256": digest,
            "output": str(output), "created_utc": created}


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    try:
        print(json.dumps(prepare(args.output)))
        return 0
    except (OSError,ValueError) as exc:
        print(f"FAIL CLOSED: {exc}",file=sys.stderr); return 2


if __name__=="__main__": raise SystemExit(main())
