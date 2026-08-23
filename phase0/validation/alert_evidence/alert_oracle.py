"""Offline A1 email/Telegram canary receipt verifier; sends nothing."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Any


CHANNELS = {"EMAIL", "TELEGRAM_PUSH"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires offset")
    return parsed.astimezone(timezone.utc)


def canary_digest(nonce: str, policy_version: str = "A1-1.0") -> str:
    return hashlib.sha256(f"{policy_version}|{nonce}".encode()).hexdigest()


def verify_delivery(bundle: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    try:
        if bundle.get("schema") != "a1-private-delivery-evidence-1.0":
            raise ValueError
        created = _utc(bundle["created_utc"])
        digest = bundle["canary_sha256"]
        if not SHA256.fullmatch(digest):
            raise ValueError
        if bundle.get("designated_ack_role") != "OWNER_DESIGNEE":
            reasons.append("ACK_ROLE_INVALID")
        receipts = bundle.get("receipts")
        if not isinstance(receipts, list):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return {"status":"FAIL_CLOSED","reasons":["EVIDENCE_SCHEMA_INVALID"]}

    seen: set[str] = set()
    attempts_seen: set[tuple[str,int]] = set()
    delivered: list[datetime] = []
    for receipt in receipts:
        channel = receipt.get("channel")
        attempt = receipt.get("attempt_minute")
        if channel not in CHANNELS or attempt not in {0,5,10,15} or (channel,attempt) in attempts_seen:
            reasons.append("CHANNEL_DUPLICATE_OR_INVALID")
            continue
        seen.add(channel); attempts_seen.add((channel,attempt))
        if receipt.get("canary_sha256") != digest or not SHA256.fullmatch(str(receipt.get("transport_receipt_sha256", ""))):
            reasons.append("RECEIPT_BINDING_INVALID")
            continue
        try:
            sent = _utc(receipt["sent_utc"])
            received = _utc(receipt["received_utc"])
        except (KeyError, TypeError, ValueError):
            reasons.append("RECEIPT_TIME_INVALID")
            continue
        due=created+timedelta(minutes=attempt)
        if sent < due or sent > due+timedelta(minutes=1) or received < sent or received > created + timedelta(minutes=15):
            reasons.append("DELIVERY_OUTSIDE_A1_DEADLINE")
        delivered.append(received)
    if seen != CHANNELS:
        reasons.append("DUAL_PATH_INCOMPLETE")

    try:
        ack = _utc(bundle["acknowledged_utc"])
        if bundle.get("ack_canary_sha256") != digest:
            reasons.append("ACK_BINDING_INVALID")
        if ack < max(delivered, default=created) or ack > created + timedelta(minutes=15):
            reasons.append("ACK_OUTSIDE_A1_DEADLINE")
        required_minutes={minute for minute in (0,5,10,15) if created+timedelta(minutes=minute)<=ack}
        for channel in CHANNELS:
            if any((channel,minute) not in attempts_seen for minute in required_minutes):
                reasons.append("REQUIRED_REPEAT_MISSING")
    except (KeyError, TypeError, ValueError):
        reasons.append("ACK_MISSING_OR_INVALID")

    return {
        "status":"PASS_SPEC_ONLY" if not reasons else "FAIL_CLOSED",
        "reasons":sorted(set(reasons)),
        "channels_verified":sorted(seen), "attempts_verified":len(attempts_seen),
        "risk_authority_restored":False,
        "claim_limit":"Delivery-path canary evidence only; no trading authority.",
    }
