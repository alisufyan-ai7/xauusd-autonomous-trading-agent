# ruff: noqa: S105, S106
# ruff: noqa: I001
from __future__ import annotations

import json

import pytest

from xauusd_demo.alert_delivery import SmtpTelegramIncidentTransport
from xauusd_demo.envelope import DemoSafetyError

KEY = "a" * 64
SECRET = "bot-secret-123"


class FakeSMTP:
    def __init__(self, host, port, *, timeout, context):
        assert host == "smtp.gmail.com" and port == 465 and timeout == 10
        assert context.verify_mode
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def login(self, user, password):
        assert user == "sender@example.com"
        assert password == "app-password"

    def send_message(self, msg):
        self.sent.append(msg)
        return {}


class FakeResponse:
    status = 200

    def __init__(self, body=None):
        self.body = body if body is not None else b'{"ok":true,"result":{"message_id":123}}'

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, n):
        assert n == 32769
        return self.body


def sender(*, web=None, smtp=None, chat_id=123456):
    return SmtpTelegramIncidentTransport(
        smtp_username="sender@example.com",
        smtp_app_password="app-password",
        email_recipient="receiver@example.com",
        telegram_bot_token=SECRET,
        telegram_chat_id=chat_id,
        smtp_factory=smtp or FakeSMTP,
        urlopen=web or (lambda req, *, timeout: FakeResponse()),
    )


def test_two_real_transport_contracts_mocked_no_live_delivery():
    out = []

    def fake_web(request, *, timeout):
        out.append(request)
        assert timeout == 10
        assert request.get_method() == "POST"
        return FakeResponse()

    transport = sender(web=fake_web)
    transport.send_email(KEY, "operator drill fake")
    transport.send_telegram(KEY, "operator drill fake")
    assert len(out) == 1
    assert out[0].full_url.startswith("https://api.telegram.org/bot")
    payload = json.loads(out[0].data)
    assert payload["chat_id"] == 123456
    assert payload["text"].endswith("incident=" + KEY[:16])


@pytest.mark.parametrize("body", [
    b'{"ok":false}', b'{"ok":true,"result":{}}',
    b'{"ok":true,"result":{"message_id":0}}', b"invalid JSON",
])
def test_telegram_unconfirmed_never_delivered(body):
    transport = sender(web=lambda req, *, timeout: FakeResponse(body))
    with pytest.raises(DemoSafetyError, match="not confirmed") as raised:
        transport.send_telegram(KEY, "safety quarantine")
    assert SECRET not in str(raised.value)


def test_numeric_verified_chat_id_mandatory():
    with pytest.raises(DemoSafetyError, match="numeric"):
        sender(chat_id="@alisufyanme")


def test_smtp_exception_is_sanitized():
    def failing(*args, **kwargs):
        raise OSError("smtp password app-password accidentally leaked")
    transport = sender(smtp=failing)
    with pytest.raises(DemoSafetyError, match="not confirmed") as raised:
        transport.send_email(KEY, "incident")
    assert "app-password" not in str(raised.value)


def test_invalid_incident_key_never_networks():
    transport = sender()
    with pytest.raises(DemoSafetyError, match="key"):
        transport.send_telegram("wrong", "incident")
    with pytest.raises(DemoSafetyError, match="key"):
        transport.send_email("wrong", "incident")


def test_network_failure_does_not_expose_telegram_secret():
    def failing(*args, **kwargs):
        raise OSError("https://api.telegram.org/bot" + SECRET + "/sendMessage")
    transport = sender(web=failing)
    with pytest.raises(DemoSafetyError) as raised:
        transport.send_telegram(KEY, "incident")
    assert SECRET not in str(raised.value)
