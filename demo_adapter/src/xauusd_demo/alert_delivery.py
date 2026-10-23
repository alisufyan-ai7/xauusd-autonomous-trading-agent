"""TLS-only SMTP + Telegram Bot API incident delivery for the DEMO watchdog.

VPS secrets are supplied at runtime, never stored in GitHub or printed.
The user handle @alisufyanme is NOT automatically a valid Telegram Bot API
user chat_id: a verified numeric chat_id from a consented bot chat is required.
Network delivery is an independent acceptance drill, not proven by CI fakes.
"""
from __future__ import annotations

import json
import re
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage
from typing import Any, Callable

from .envelope import DemoSafetyError


class SmtpTelegramIncidentTransport:
    """Dual authenticated delivery. Never order-capable or broker-connected."""

    def __init__(
        self,
        *,
        smtp_username: str,
        smtp_app_password: str,
        email_recipient: str,
        telegram_bot_token: str,
        telegram_chat_id: int,
        smtp_factory: Callable[..., Any] | None = None,
        urlopen: Callable[..., Any] | None = None,
    ) -> None:
        if any(
            not value or len(value) > 256
            for value in (
                smtp_username, smtp_app_password, email_recipient,
                telegram_bot_token,
            )
        ):
            raise DemoSafetyError("VPS alert credentials or destination missing")
        if not all(
            re.fullmatch(r"[A-Za-z0-9_.+\-]+@[A-Za-z0-9.\-]+", item)
            for item in (smtp_username, email_recipient)
        ):
            raise DemoSafetyError("invalid SMTP address")
        if (
            not re.fullmatch(r"[A-Za-z0-9:_\-]+", telegram_bot_token)
            or type(telegram_chat_id) is not int
            or telegram_chat_id == 0
        ):
            raise DemoSafetyError("numeric consented Telegram chat_id required")
        self._smtp_username = smtp_username
        self._smtp_app_password = smtp_app_password
        self._email_recipient = email_recipient
        self._bot_token = telegram_bot_token
        self._chat_id = telegram_chat_id
        self._smtp_factory = smtp_factory or smtplib.SMTP_SSL
        self._urlopen = urlopen or urllib.request.urlopen

    def send_email(self, incident_key: str, message: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", incident_key):
            raise DemoSafetyError("invalid incident receipt key")
        email = EmailMessage()
        email["From"] = self._smtp_username
        email["To"] = self._email_recipient
        email["Subject"] = f"[XAUUSD GATE0 ALERT] DEMO {incident_key[:12]}"
        email["X-XAUUSD-Incident-Key"] = incident_key
        email.set_content(message)
        try:
            with self._smtp_factory(
                "smtp.gmail.com", 465, timeout=10,
                context=ssl.create_default_context(),
            ) as smtp:
                smtp.login(self._smtp_username, self._smtp_app_password)
                rejected = smtp.send_message(email)
            if rejected:
                raise DemoSafetyError("email recipient was rejected")
        except Exception:
            # Libraries can include usernames or auth endpoints in exceptions.
            raise DemoSafetyError("SMTP alert delivery not confirmed") from None

    def send_telegram(self, incident_key: str, message: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", incident_key):
            raise DemoSafetyError("invalid incident receipt key")
        payload = json.dumps({
            "chat_id": self._chat_id,
            "text": f"{message}\nincident={incident_key[:16]}",
            "disable_web_page_preview": True,
        }).encode("utf-8")
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        request = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._urlopen(request, timeout=10) as response:
                if response.status != 200:
                    raise DemoSafetyError("Telegram response status not 200")
                raw = response.read(32769)
            if len(raw) > 32768:
                raise DemoSafetyError("Telegram response too large")
            result = json.loads(raw)
            if not (
                isinstance(result, dict)
                and result.get("ok") is True
                and isinstance(result.get("result"), dict)
                and type(result["result"].get("message_id")) is int
                and result["result"]["message_id"] > 0
            ):
                raise DemoSafetyError("Telegram delivery acknowledgement missing")
        except Exception:
            # Suppress full URL/token from urllib.HTTPError and JSON parsing.
            raise DemoSafetyError("Telegram alert delivery not confirmed") from None
