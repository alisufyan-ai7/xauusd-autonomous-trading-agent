"""Private SMTP and Telegram incident delivery; no account/order authority."""

from __future__ import annotations

import json
import os
import smtplib
import ssl
import urllib.parse
import urllib.request
from email.message import EmailMessage

from .envelope import DemoSafetyError


class VPSDualAlertTransport:
    def __init__(self) -> None:
        self.host = os.getenv("XAUUSD_SMTP_HOST", "")
        self.user = os.getenv("XAUUSD_SMTP_USER", "")
        self.password = os.getenv("XAUUSD_SMTP_PASSWORD", "")
        self.port = int(os.getenv("XAUUSD_SMTP_PORT", "465"))
        self.recipient = os.getenv("XAUUSD_ALERT_EMAIL", "")
        self.bot = os.getenv("XAUUSD_TELEGRAM_BOT_TOKEN", "")
        self.chat = os.getenv("XAUUSD_TELEGRAM_CHAT_ID", "")

    @property
    def configured(self) -> bool:
        return bool(
            self.host and self.user and self.password and self.recipient
            and self.bot and self.chat and 1 <= self.port <= 65535
        )

    def send_email(self, incident_key: str, message: str) -> None:
        if not self.configured:
            raise DemoSafetyError("incident transport not configured")
        mail = EmailMessage()
        mail["From"], mail["To"] = self.user, self.recipient
        mail["Subject"] = "[XAUUSD DEMO] " + incident_key[:12]
        mail.set_content(message)
        with smtplib.SMTP_SSL(
            self.host, self.port, timeout=10, context=ssl.create_default_context(),
        ) as conn:
            conn.login(self.user, self.password)
            conn.send_message(mail)

    def send_telegram(self, incident_key: str, message: str) -> None:
        if not self.configured:
            raise DemoSafetyError("incident transport not configured")
        payload = urllib.parse.urlencode({
            "chat_id": self.chat, "text": message + "\nincident=" + incident_key[:12],
        }).encode()
        request = urllib.request.Request(
            "https://api.telegram.org/bot" + self.bot + "/sendMessage",
            payload, method="POST",
        )
        # Never print or log the URL: it includes the Telegram secret.
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            reply = json.loads(response.read(4096))
        if reply.get("ok") is not True:
            raise DemoSafetyError("Telegram incident rejected")
