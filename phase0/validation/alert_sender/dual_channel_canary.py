"""Send only the frozen A1 email/Telegram canary and seal private evidence."""

from __future__ import annotations

import argparse
import concurrent.futures
import email
import hashlib
import imaplib
import json
import re
import smtplib
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid, parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable

from phase0.validation.alert_evidence.prepare_private_canary import prepare
from phase0.validation.alert_evidence.private_delivery_evidence import (
    record_ack, record_receipt, verify_private_evidence,
)
from phase0.validation.alert_sender.sender_setup import (
    IMAP_HOST, LABEL, SMTP_HOST, _telegram,
)

SUBJECT = "[XAUUSD GATE0 TEST] A1 canary — no trading authority"
ATTEMPTS = (0, 5, 10, 15)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canary_body(digest: str) -> str:
    return ("TEST/CANARY ONLY. No trading or broker action is authorized.\n"
            f"Canary SHA-256: {digest}\n"
            f"Acknowledge with exactly: ACK {digest}\n")


class GmailChannel:
    def __init__(self, address: str, password: str, label: str = LABEL):
        self.address, self.password, self.label = address, password, label
        self.message_ids: list[str] = []

    def preflight(self) -> None:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, 465, context=context, timeout=30) as smtp:
            smtp.login(self.address, self.password)
        imap = imaplib.IMAP4_SSL(IMAP_HOST, 993, ssl_context=context, timeout=30)
        try:
            imap.login(self.address, self.password)
            status, folders = imap.list()
            if status != "OK" or not any(self.label.encode() in row for row in folders or []):
                raise ValueError("required Gmail label is missing")
        finally:
            imap.logout()

    def send(self, subject: str, body: str, digest: str, attempt: int,
             now: Callable[[], datetime]) -> dict[str, Any]:
        message = EmailMessage()
        message_id = make_msgid(domain="gate0.local")
        message["From"] = self.address
        message["To"] = self.address
        message["Subject"] = subject
        message["Date"] = format_datetime(now())
        message["Message-ID"] = message_id
        message["X-Gate0-Canary"] = digest
        message["X-Gate0-Attempt-Minute"] = str(attempt)
        message.set_content(body)
        sent = now()
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, 465, context=context, timeout=30) as smtp:
            smtp.login(self.address, self.password)
            refused = smtp.send_message(message)
            if refused:
                raise ValueError("Gmail refused one or more recipients")
        self.message_ids.append(message_id)
        received, uidvalidity, uid, gmail_id, raw = self._await_mailbox(message_id, now)
        return {"sent_utc": _iso(sent), "received_utc": _iso(received),
                "provider_semantics": "SMTP accepted and Gmail Inbox copy observed",
                "message_id": message_id, "imap_uidvalidity": uidvalidity,
                "imap_uid": uid, "gmail_message_id": gmail_id,
                "raw_message_sha256": hashlib.sha256(raw).hexdigest()}

    def _await_mailbox(self, message_id: str, now: Callable[[], datetime]):
        end = time.monotonic() + 60
        context = ssl.create_default_context()
        while time.monotonic() < end:
            imap = imaplib.IMAP4_SSL(IMAP_HOST, 993, ssl_context=context, timeout=30)
            try:
                imap.login(self.address, self.password)
                status, select_data = imap.select("INBOX")
                if status != "OK":
                    raise ValueError("Gmail Inbox unavailable")
                uidvalidity = str(imap.response("UIDVALIDITY")[1][0].decode())
                status, data = imap.uid("SEARCH", None, "HEADER", "Message-ID", message_id)
                uids = data[0].split() if status == "OK" and data else []
                if uids:
                    uid = uids[-1]
                    imap.uid("STORE", uid, "+X-GM-LABELS", f'("{self.label}")')
                    status, rows = imap.uid("FETCH", uid, "(RFC822 X-GM-MSGID INTERNALDATE)")
                    raw = next((part[1] for part in rows if isinstance(part, tuple)), b"")
                    meta = next((part[0] for part in rows if isinstance(part, tuple)), b"")
                    gmail_id = meta.decode("ascii", "replace")
                    return now(), uidvalidity, uid.decode(), gmail_id, raw
            finally:
                try:
                    imap.logout()
                except Exception:
                    pass
            time.sleep(2)
        raise ValueError("Gmail mailbox delivery receipt timed out")

    def poll_ack(self, digest: str, after: datetime, now: Callable[[], datetime]):
        context = ssl.create_default_context()
        imap = imaplib.IMAP4_SSL(IMAP_HOST, 993, ssl_context=context, timeout=30)
        try:
            imap.login(self.address, self.password)
            imap.select("INBOX")
            for parent in self.message_ids:
                status, data = imap.uid("SEARCH", None, "HEADER", "In-Reply-To", parent)
                for uid in (data[0].split() if status == "OK" and data else []):
                    status, rows = imap.uid("FETCH", uid, "(RFC822 INTERNALDATE)")
                    raw = next((part[1] for part in rows if isinstance(part, tuple)), b"")
                    parsed = email.message_from_bytes(raw)
                    if parsed.get("Message-ID") in self.message_ids:
                        continue
                    meta = next((part[0] for part in rows if isinstance(part, tuple)), b"")
                    match = re.search(rb'INTERNALDATE "([^"]+)"', meta)
                    if not match:
                        continue
                    when = parsedate_to_datetime(match.group(1).decode("ascii"))
                    payload = parsed.get_payload(decode=True) or b""
                    exact_ack = any(line.strip() == f"ACK {digest}"
                                    for line in payload.decode("utf-8", "replace").splitlines())
                    if when.astimezone(timezone.utc) >= after and exact_ack:
                        return {"acknowledged_utc": _iso(when), "channel": "EMAIL",
                                "imap_uid": uid.decode(), "raw_message": raw.decode("utf-8", "replace")}
        finally:
            imap.logout()
        return None


class TelegramChannel:
    def __init__(self, token: str, config: dict[str, Any]):
        self.token = token
        self.chat_id = int(config["telegram_chat_id"])
        self.user_id = int(config["telegram_user_id"])
        self.bot_id = int(config["bot_id"])
        self.offset = int(config["telegram_update_offset"])

    def preflight(self) -> None:
        me = _telegram(self.token, "getMe")
        webhook = _telegram(self.token, "getWebhookInfo")
        if int(me.get("id", -1)) != self.bot_id or webhook.get("url"):
            raise ValueError("Telegram bot binding or webhook state changed")

    def send(self, subject: str, body: str, digest: str, attempt: int,
             now: Callable[[], datetime]) -> dict[str, Any]:
        sent = now()
        message = _telegram(self.token, "sendMessage", {
            "chat_id": self.chat_id, "text": f"{subject}\n\n{body}",
            "disable_web_page_preview": "true",
        })
        accepted = now()
        return {"sent_utc": _iso(sent), "received_utc": _iso(accepted),
                "provider_semantics": "Telegram Bot API accepted/persisted; not a read receipt",
                "message_id": int(message["message_id"]), "chat_id": self.chat_id}

    def poll_ack(self, digest: str, after: datetime, now: Callable[[], datetime]):
        updates = _telegram(self.token, "getUpdates", {
            "offset": self.offset, "timeout": 1,
            "allowed_updates": json.dumps(["message"]),
        })
        for update in updates:
            self.offset = max(self.offset, int(update["update_id"]) + 1)
            message = update.get("message") or {}
            sender = message.get("from") or {}
            chat = message.get("chat") or {}
            when = datetime.fromtimestamp(int(message.get("date", 0)), timezone.utc)
            if (sender.get("id") == self.user_id == chat.get("id")
                    and chat.get("type") == "private"
                    and message.get("text") == f"ACK {digest}" and when >= after):
                return {"acknowledged_utc": _iso(when), "channel": "TELEGRAM_PUSH",
                        "update_id": int(update["update_id"]),
                        "message_id": int(message["message_id"]), "chat_id": self.chat_id}
        return None


def _write_receipt(output: Path, channel: str, attempt: int, data: dict[str, Any]) -> Path:
    path = output / f"PRIVATE_{channel}_{attempt:02d}_RECEIPT.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def execute(output: Path, config: dict[str, Any], gmail: Any, telegram: Any, *,
            now: Callable[[], datetime] = utc_now,
            sleeper: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    if config.get("schema") != "gate0-private-dual-sender-1.0":
        raise ValueError("private sender configuration invalid")
    if config.get("external_python_trading_required_state") != "DISABLED":
        raise ValueError("external Python trading state contract invalid")
    gmail.preflight(); telegram.preflight()
    prepared = prepare(output, created_utc=_iso(now()))
    digest = prepared["canary_sha256"]
    created = datetime.fromisoformat(prepared["created_utc"].replace("Z", "+00:00"))
    body = canary_body(digest)
    deadline = created + timedelta(minutes=15)
    for attempt in ATTEMPTS:
        due = created + timedelta(minutes=attempt)
        while now() < due:
            ack = telegram.poll_ack(digest, created, now) or gmail.poll_ack(digest, created, now)
            if ack:
                return _finish_ack(output, ack)
            sleeper(min(2.0, max(0.0, (due - now()).total_seconds())))
        if now() > deadline + timedelta(seconds=1):
            break
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            email_future = pool.submit(gmail.send, SUBJECT, body, digest, attempt, now)
            telegram_future = pool.submit(telegram.send, SUBJECT, body, digest, attempt, now)
            results = {"EMAIL": email_future.result(), "TELEGRAM_PUSH": telegram_future.result()}
        starts = [datetime.fromisoformat(row["sent_utc"].replace("Z", "+00:00")) for row in results.values()]
        if (max(starts) - min(starts)).total_seconds() > 2:
            raise ValueError("dual-channel launch skew exceeded two seconds")
        for channel, receipt in results.items():
            path = _write_receipt(output, channel, attempt, receipt)
            record_receipt(output, channel=channel, attempt_minute=attempt,
                           sent_utc=receipt["sent_utc"], received_utc=receipt["received_utc"],
                           transport_receipt_file=path)
        ack = telegram.poll_ack(digest, created, now) or gmail.poll_ack(digest, created, now)
        if ack:
            return _finish_ack(output, ack)
        if attempt == 15:
            break
    return {"status": "FAIL_CLOSED", "reasons": ["ACK_DEADLINE_EXPIRED"],
            "risk_authority_restored": False}


def _finish_ack(output: Path, ack: dict[str, Any]) -> dict[str, Any]:
    path = output / "PRIVATE_OWNER_ACK.json"
    path.write_text(json.dumps(ack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    record_ack(output, acknowledged_utc=ack["acknowledged_utc"],
               acknowledgement_evidence_file=path)
    return verify_private_evidence(output)


def _read_secrets() -> tuple[str, str]:
    token = sys.stdin.readline().rstrip("\r\n")
    password = sys.stdin.readline().rstrip("\r\n")
    if not token or not password:
        raise ValueError("two secrets are required on redirected standard input")
    return token, password


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        token, password = _read_secrets()
        config = json.loads(args.config.read_text(encoding="utf-8"))
        result = execute(args.output, config,
                         GmailChannel(config["email"], password, config["gmail_label"]),
                         TelegramChannel(token, config))
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("status") == "PASS_SPEC_ONLY" else 2
    except Exception as exc:
        print(f"FAIL CLOSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
