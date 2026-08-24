"""Record and verify private A1 receipts; contains no delivery capability."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .alert_oracle import verify_delivery
except ImportError:
    from alert_oracle import verify_delivery

CHANNELS = {"EMAIL", "TELEGRAM_PUSH"}
ATTEMPTS = {0, 5, 10, 15}


def private_target(path: Path) -> Path:
    target = path.resolve()
    repo = Path(__file__).resolve().parents[3]
    if target == repo or repo in target.parents:
        raise ValueError("private output must be outside repository")
    return target


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires offset")
    return parsed.astimezone(timezone.utc)


def _bundle_path(output: Path) -> Path:
    path = output / "PRIVATE_RECEIPT_TEMPLATE.json"
    if not path.is_file():
        raise ValueError("private receipt template missing")
    return path


def _load_bundle(output: Path) -> dict[str, Any]:
    bundle = json.loads(_bundle_path(output).read_text(encoding="utf-8"))
    if bundle.get("schema") != "a1-private-delivery-evidence-1.0":
        raise ValueError("private receipt template schema invalid")
    return bundle


def _save_bundle(output: Path, bundle: dict[str, Any]) -> None:
    path = _bundle_path(output)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def validate_audit_chain(path: Path) -> tuple[int, str]:
    sequence = 0
    prior = "0" * 64
    if not path.exists():
        return sequence, prior
    for line in path.read_text(encoding="utf-8").splitlines():
        supplied = json.loads(line)
        row = dict(supplied)
        recorded = row.pop("record_sha256", None)
        actual = hashlib.sha256(
            json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if (row.get("sequence") != sequence
                or row.get("prior_record_sha256") != prior
                or recorded != actual):
            raise ValueError("private alert audit chain invalid")
        sequence += 1
        prior = actual
    return sequence, prior


def _append_audit(output: Path, event: str, payload: dict[str, Any]) -> str:
    chain = output / "PRIVATE_ALERT_AUDIT.jsonl"
    sequence, prior = validate_audit_chain(chain)
    row = {
        "schema": "gate0-a1-private-audit-1.0",
        "sequence": sequence,
        "prior_record_sha256": prior,
        "event": event,
        "recorded_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "payload": payload,
        "claim_limit": "Private canary audit only; no trading authority.",
    }
    digest = hashlib.sha256(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    row["record_sha256"] = digest
    with chain.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return digest


def _evidence_hash(output: Path, path: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_file() or output not in resolved.parents:
        raise ValueError("receipt evidence must be a file inside private output")
    return hashlib.sha256(resolved.read_bytes()).hexdigest()


def record_receipt(output: Path, *, channel: str, attempt_minute: int,
                   sent_utc: str, received_utc: str,
                   transport_receipt_file: Path) -> dict[str, Any]:
    output = private_target(output)
    if channel not in CHANNELS or attempt_minute not in ATTEMPTS:
        raise ValueError("invalid channel or attempt minute")
    sent = _utc(sent_utc)
    received = _utc(received_utc)
    if received < sent:
        raise ValueError("receipt time precedes send time")
    bundle = _load_bundle(output)
    if bundle.get("acknowledged_utc") is not None:
        raise ValueError("delivery already acknowledged")
    if any(row.get("channel") == channel and row.get("attempt_minute") == attempt_minute
           for row in bundle.get("receipts", [])):
        raise ValueError("duplicate channel attempt")
    receipt_hash = _evidence_hash(output, transport_receipt_file)
    receipt = {
        "channel": channel,
        "attempt_minute": attempt_minute,
        "canary_sha256": bundle["canary_sha256"],
        "transport_receipt_sha256": receipt_hash,
        "sent_utc": sent.isoformat().replace("+00:00", "Z"),
        "received_utc": received.isoformat().replace("+00:00", "Z"),
    }
    _append_audit(output, "DELIVERY_RECEIPT", receipt)
    bundle.setdefault("receipts", []).append(receipt)
    _save_bundle(output, bundle)
    return {"status": "RECORDED", "channel": channel,
            "attempt_minute": attempt_minute,
            "transport_receipt_sha256": receipt_hash}


def record_ack(output: Path, *, acknowledged_utc: str,
               acknowledgement_evidence_file: Path) -> dict[str, Any]:
    output = private_target(output)
    acknowledged = _utc(acknowledged_utc)
    bundle = _load_bundle(output)
    if bundle.get("acknowledged_utc") is not None:
        raise ValueError("duplicate acknowledgement")
    evidence_hash = _evidence_hash(output, acknowledgement_evidence_file)
    payload = {
        "acknowledged_utc": acknowledged.isoformat().replace("+00:00", "Z"),
        "ack_canary_sha256": bundle["canary_sha256"],
        "ack_evidence_sha256": evidence_hash,
    }
    audit_hash = _append_audit(output, "OWNER_ACKNOWLEDGEMENT", payload)
    bundle.update(payload)
    bundle["local_audit_record_sha256"] = audit_hash
    bundle["local_audit_chain_valid"] = True
    _save_bundle(output, bundle)
    return {"status": "ACK_RECORDED", "ack_evidence_sha256": evidence_hash,
            "local_audit_record_sha256": audit_hash}


def verify_private_evidence(output: Path) -> dict[str, Any]:
    output = private_target(output)
    bundle = _load_bundle(output)
    _, final_hash = validate_audit_chain(output / "PRIVATE_ALERT_AUDIT.jsonl")
    bundle["local_audit_chain_valid"] = (
        final_hash != "0" * 64
        and bundle.get("local_audit_record_sha256") == final_hash
    )
    _save_bundle(output, bundle)
    result = verify_delivery(bundle)
    result["evidence_bundle_sha256"] = hashlib.sha256(
        _bundle_path(output).read_bytes()
    ).hexdigest()
    result["local_audit_final_sha256"] = final_hash
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    receipt = subparsers.add_parser("record-receipt")
    receipt.add_argument("--channel", choices=sorted(CHANNELS), required=True)
    receipt.add_argument("--attempt-minute", type=int, choices=sorted(ATTEMPTS), required=True)
    receipt.add_argument("--sent-utc", required=True)
    receipt.add_argument("--received-utc", required=True)
    receipt.add_argument("--transport-receipt-file", type=Path, required=True)
    ack = subparsers.add_parser("record-ack")
    ack.add_argument("--acknowledged-utc", required=True)
    ack.add_argument("--acknowledgement-evidence-file", type=Path, required=True)
    subparsers.add_parser("verify")
    args = parser.parse_args()
    try:
        if args.command == "record-receipt":
            result = record_receipt(
                args.output, channel=args.channel, attempt_minute=args.attempt_minute,
                sent_utc=args.sent_utc, received_utc=args.received_utc,
                transport_receipt_file=args.transport_receipt_file,
            )
        elif args.command == "record-ack":
            result = record_ack(
                args.output, acknowledged_utc=args.acknowledged_utc,
                acknowledgement_evidence_file=args.acknowledgement_evidence_file,
            )
        else:
            result = verify_private_evidence(args.output)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] in {"RECORDED", "ACK_RECORDED", "PASS_SPEC_ONLY"} else 2
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
