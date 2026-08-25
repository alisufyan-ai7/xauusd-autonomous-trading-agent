import ast
import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from phase0.validation.alert_sender.dual_channel_canary import (
    SUBJECT, canary_body, execute,
)
from phase0.validation.alert_sender.sender_setup import bind_telegram, private_target


class Clock:
    def __init__(self):
        self.value = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
        self.lock = threading.Lock()

    def now(self):
        with self.lock:
            return self.value

    def sleep(self, seconds):
        with self.lock:
            self.value += timedelta(seconds=seconds)


class FakeChannel:
    def __init__(self, name, clock, acknowledge_after=None):
        self.name, self.clock, self.acknowledge_after = name, clock, acknowledge_after
        self.calls = []

    def preflight(self):
        return None

    def send(self, subject, body, digest, attempt, now):
        sent = now()
        self.calls.append((subject, body, digest, attempt))
        stamp = sent.isoformat().replace("+00:00", "Z")
        return {"sent_utc": stamp, "received_utc": stamp,
                "provider_semantics": "fixture", "receipt": f"{self.name}-{attempt}"}

    def poll_ack(self, digest, after, now):
        if self.acknowledge_after is None or not self.calls:
            return None
        if now() >= after + timedelta(minutes=self.acknowledge_after):
            return {"acknowledged_utc": now().isoformat().replace("+00:00", "Z"),
                    "channel": self.name, "fixture": True}
        return None


def config():
    return {"schema": "gate0-private-dual-sender-1.0",
            "external_python_trading_required_state": "DISABLED"}


class AlertSenderTests(unittest.TestCase):
    def _output(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name) / "private-evidence"

    def test_simultaneous_identical_canary_passes_on_bound_ack(self):
        clock = Clock()
        gmail = FakeChannel("EMAIL", clock)
        telegram = FakeChannel("TELEGRAM_PUSH", clock, acknowledge_after=0)
        result = execute(self._output(), config(), gmail, telegram,
                         now=clock.now, sleeper=clock.sleep)
        self.assertEqual("PASS_SPEC_ONLY", result["status"], result.get("reasons"))
        self.assertEqual(1, len(gmail.calls)); self.assertEqual(1, len(telegram.calls))
        self.assertEqual(gmail.calls[0], telegram.calls[0])
        self.assertTrue(gmail.calls[0][0].startswith("[XAUUSD GATE0 TEST]"))
        self.assertIn("No trading or broker action", gmail.calls[0][1])

    def test_retries_at_frozen_offsets_stop_after_ack(self):
        clock = Clock()
        gmail = FakeChannel("EMAIL", clock)
        telegram = FakeChannel("TELEGRAM_PUSH", clock, acknowledge_after=6)
        result = execute(self._output(), config(), gmail, telegram,
                         now=clock.now, sleeper=clock.sleep)
        self.assertEqual("PASS_SPEC_ONLY", result["status"], result.get("reasons"))
        self.assertEqual([0, 5], [call[3] for call in gmail.calls])
        self.assertEqual(gmail.calls, telegram.calls)

    def test_no_ack_runs_exact_frozen_attempts_then_fails_closed(self):
        clock = Clock()
        gmail = FakeChannel("EMAIL", clock)
        telegram = FakeChannel("TELEGRAM_PUSH", clock)
        result = execute(self._output(), config(), gmail, telegram,
                         now=clock.now, sleeper=clock.sleep)
        self.assertEqual("FAIL_CLOSED", result["status"])
        self.assertEqual([0, 5, 10, 15], [call[3] for call in gmail.calls])
        self.assertEqual(gmail.calls, telegram.calls)

    def test_invalid_external_python_contract_fails_before_preflight(self):
        bad = config(); bad["external_python_trading_required_state"] = "ENABLED"
        with self.assertRaisesRegex(ValueError, "external Python"):
            execute(self._output(), bad, None, None)

    def test_private_binding_requires_empty_webhook_nonce_identity_and_private_chat(self):
        calls = []
        def telegram(_token, method, payload=None):
            calls.append(method)
            if method == "getMe": return {"id": 91, "username": "gate0_fixture_bot"}
            if method == "getWebhookInfo": return {"url": ""}
            return [{"update_id": 7, "message": {
                "text": "/start nonce", "from": {"id": 42, "username": "OwnerFixture"},
                "chat": {"id": 42, "type": "private"}}}]
        result = bind_telegram("fixture-token", "ownerfixture", "nonce",
                               deadline_seconds=1, telegram=telegram, sleeper=lambda _: None)
        self.assertEqual(42, result["telegram_chat_id"])
        self.assertEqual(8, result["telegram_update_offset"])
        self.assertEqual(["getMe", "getWebhookInfo", "getUpdates"], calls)

    def test_webhook_fails_before_getupdates(self):
        def telegram(_token, method, payload=None):
            return {"id": 1, "username": "fixture_bot"} if method == "getMe" else {"url": "https://invalid"}
        with self.assertRaisesRegex(ValueError, "webhook"):
            bind_telegram("fixture", "owner", "nonce", telegram=telegram)

    def test_messages_are_sanitized_and_bound_to_digest(self):
        digest = "a" * 64
        body = canary_body(digest)
        self.assertEqual(2, body.count(digest))
        for forbidden in ("password", "token", "account number", "order", "BUY", "SELL"):
            self.assertNotIn(forbidden, (SUBJECT + body).lower())

    def test_modules_have_no_broker_or_process_capability(self):
        folder = Path(__file__).parent
        for name in ("sender_setup.py", "dual_channel_canary.py"):
            tree = ast.parse((folder / name).read_text(encoding="utf-8"))
            imports = set(); calls = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])
                elif isinstance(node, ast.Call):
                    calls.add(node.func.id if isinstance(node.func, ast.Name)
                              else node.func.attr if isinstance(node.func, ast.Attribute) else "")
            self.assertNotIn("MetaTrader5", imports)
            self.assertFalse(imports & {"subprocess", "requests", "telegram"})
            self.assertFalse(calls & {"order_send", "order_check", "Popen", "run", "system"})

    def test_powershell_uses_dpapi_acl_stdin_and_no_secret_arguments(self):
        folder = Path(__file__).parent
        setup = (folder / "setup_private_sender.ps1").read_text(encoding="utf-8")
        runner = (folder / "run_dual_channel_canary.ps1").read_text(encoding="utf-8")
        self.assertIn("ConvertFrom-SecureString", setup)
        self.assertIn("Set-Acl", setup)
        self.assertIn("outside the repository", setup)
        self.assertIn("|\n        & py", setup)
        self.assertIn("|\n        & py", runner)
        for text in (setup, runner):
            self.assertNotIn("--token", text)
            self.assertNotIn("--password", text)
            self.assertNotIn("MetaTrader5", text)

    def test_sender_configuration_cannot_be_written_in_repository(self):
        with self.assertRaisesRegex(ValueError, "outside repository"):
            private_target(Path(__file__).parent / "forbidden")


if __name__ == "__main__":
    unittest.main()
