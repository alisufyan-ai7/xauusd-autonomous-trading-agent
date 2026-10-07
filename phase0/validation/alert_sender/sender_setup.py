"""Private Telegram/Gmail sender binding and non-delivery preflight."""

from __future__ import annotations

import argparse
import imaplib
import json
import secrets
import socket
import smtplib
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

TELEGRAM_ROOT = "https://api.telegram.org"
SMTP_HOST = "smtp.gmail.com"
IMAP_HOST = "imap.gmail.com"
LABEL = "XAUUSD Gate 0 Alerts"


def _telegram_failure_code(exc: BaseException) -> str:
    """Return a bounded transport code without rendering a token-bearing URL."""
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code in {401, 404}:
            return f"TOKEN_REJECTED_HTTP_{exc.code}"
        return f"HTTP_{exc.code}"
    if isinstance(exc, json.JSONDecodeError):
        return "INVALID_JSON_RESPONSE"
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, ssl.SSLCertVerificationError):
            return "TLS_CERTIFICATE_VERIFICATION_FAILED"
        if isinstance(reason, ssl.SSLError):
            return "TLS_HANDSHAKE_FAILED"
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return "NETWORK_TIMEOUT"
        if isinstance(reason, socket.gaierror):
            return "DNS_RESOLUTION_FAILED"
        if isinstance(reason, ConnectionRefusedError):
            return "CONNECTION_REFUSED"
        return "NETWORK_OR_PROXY_FAILURE"
    if isinstance(exc, ssl.SSLCertVerificationError):
        return "TLS_CERTIFICATE_VERIFICATION_FAILED"
    if isinstance(exc, ssl.SSLError):
        return "TLS_HANDSHAKE_FAILED"
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "NETWORK_TIMEOUT"
    return "UNEXPECTED_TRANSPORT_FAILURE"


def private_target(path: Path) -> Path:
    target = path.resolve()
    repo = Path(__file__).resolve().parents[3]
    if target == repo or repo in target.parents:
        raise ValueError("private sender output must be outside repository")
    return target


def _telegram(token: str, method: str, payload: dict[str, Any] | None = None,
              opener: Callable[..., Any] = urllib.request.urlopen) -> dict[str, Any]:
    body = urllib.parse.urlencode(payload or {}).encode()
    request = urllib.request.Request(
        f"{TELEGRAM_ROOT}/bot{token}/{method}", data=body, method="POST"
    )
    try:
        with opener(request, timeout=35) as response:
            result = json.loads(response.read())
    except Exception as exc:  # never expose the token-bearing request URL
        code = _telegram_failure_code(exc)
        raise ValueError(f"Telegram {method} failed closed: {code}") from None
    if result.get("ok") is not True:
        error_code = result.get("error_code")
        safe_code = f"API_REJECTED_{error_code}" if isinstance(error_code, int) else "API_REJECTED"
        raise ValueError(f"Telegram {method} failed closed: {safe_code}")
    return result["result"]


def verify_gmail(email: str, app_password: str,
                 smtp_factory: Callable[..., Any] = smtplib.SMTP_SSL,
                 imap_factory: Callable[..., Any] = imaplib.IMAP4_SSL) -> None:
    context = ssl.create_default_context()
    with smtp_factory(SMTP_HOST, 465, context=context, timeout=30) as smtp:
        smtp.login(email, app_password)
    imap = imap_factory(IMAP_HOST, 993, ssl_context=context, timeout=30)
    try:
        if imap.login(email, app_password)[0] != "OK":
            raise ValueError("Gmail IMAP authentication failed")
        status, folders = imap.list()
        if status != "OK":
            raise ValueError("Gmail label listing failed")
        if not any(LABEL.encode() in row for row in folders or []):
            if imap.create(f'"{LABEL}"')[0] != "OK":
                raise ValueError("required Gmail label could not be created")
    finally:
        try:
            imap.logout()
        except Exception:
            pass


def bind_telegram(token: str, expected_username: str, nonce: str, *,
                  deadline_seconds: int = 600,
                  telegram: Callable[..., Any] = _telegram,
                  sleeper: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    me = telegram(token, "getMe")
    webhook = telegram(token, "getWebhookInfo")
    if webhook.get("url"):
        raise ValueError("Telegram webhook must be empty before private binding")
    bot_username = str(me.get("username", ""))
    if not bot_username:
        raise ValueError("Telegram bot username is missing")
    print(f"BIND: open https://t.me/{bot_username} and send exactly: /start {nonce}")
    end = time.monotonic() + deadline_seconds
    offset: int | None = None
    while time.monotonic() < end:
        updates = telegram(token, "getUpdates", {
            "timeout": 20,
            "offset": offset or 0,
            "allowed_updates": json.dumps(["message"]),
        })
        for update in updates:
            offset = max(offset or 0, int(update["update_id"]) + 1)
            message = update.get("message") or {}
            sender = message.get("from") or {}
            chat = message.get("chat") or {}
            exact = str(message.get("text", "")) == f"/start {nonce}"
            identity = str(sender.get("username", "")).casefold() == expected_username.casefold()
            private = chat.get("type") == "private" and sender.get("id") == chat.get("id")
            if exact and identity and private:
                return {
                    "bot_id": int(me["id"]),
                    "bot_username": bot_username,
                    "telegram_username": expected_username,
                    "telegram_chat_id": int(chat["id"]),
                    "telegram_user_id": int(sender["id"]),
                    "telegram_update_offset": offset,
                }
        sleeper(0.2)
    raise ValueError("timed out waiting for exact private Telegram binding")


def configure(output: Path, email: str, telegram_username: str, token: str,
              app_password: str) -> dict[str, Any]:
    output = private_target(output)
    if output.exists() and any(output.iterdir()):
        allowed = {"telegram_token.dpapi", "gmail_app_password.dpapi"}
        if any(item.name not in allowed for item in output.iterdir()):
            raise ValueError("private sender directory already contains configuration")
    output.mkdir(parents=True, exist_ok=True)
    username = telegram_username.removeprefix("@").strip()
    if not email or not username or not token or not app_password:
        raise ValueError("all sender fields are required")
    verify_gmail(email, app_password)
    nonce = secrets.token_urlsafe(18)
    binding = bind_telegram(token, username, nonce)
    config = {
        "schema": "gate0-private-dual-sender-1.0",
        "email": email,
        "gmail_label": LABEL,
        **binding,
        "external_python_trading_required_state": "DISABLED",
        "claim_limit": "A1 test canary only; no trading or broker authority.",
    }
    path = output / "PRIVATE_SENDER_CONFIG.json"
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "CONFIGURED_NOT_SENT", "bot_id": binding["bot_id"]}


def _read_private_input() -> tuple[str, str, str, str]:
    email = sys.stdin.readline().rstrip("\r\n")
    username = sys.stdin.readline().rstrip("\r\n")
    token = sys.stdin.readline().rstrip("\r\n")
    app_password = sys.stdin.readline().rstrip("\r\n")
    if not email or not username or not token or not app_password:
        raise ValueError("private setup input is incomplete")
    return email, username, token, app_password


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        email, username, token, app_password = _read_private_input()
        result = configure(args.output, email, username, token, app_password)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
