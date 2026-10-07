import ast
import json
import tempfile
import unittest
from pathlib import Path

from phase0.validation.alert_evidence.alert_oracle import canary_digest
from phase0.validation.alert_evidence.private_delivery_evidence import (
    record_ack,
    record_receipt,
    verify_private_evidence,
)


class PrivateDeliveryEvidenceTests(unittest.TestCase):
    def _prepared(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        output = Path(temp.name) / "private"
        output.mkdir()
        digest = canary_digest("fixture")
        bundle = {
            "schema": "a1-private-delivery-evidence-1.0",
            "created_utc": "2026-08-24T12:00:00Z",
            "canary_sha256": digest,
            "designated_ack_role": "OWNER_DESIGNEE",
            "local_audit_record_sha256": None,
            "local_audit_chain_valid": False,
            "receipts": [],
            "acknowledged_utc": None,
            "ack_canary_sha256": digest,
        }
        (output / "PRIVATE_RECEIPT_TEMPLATE.json").write_text(
            json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return output

    @staticmethod
    def _evidence(output, name, content):
        path = output / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_dual_path_receipts_ack_and_audit_pass(self):
        output = self._prepared()
        email = self._evidence(output, "email-receipt.txt", "fixture email receipt")
        telegram = self._evidence(output, "telegram-receipt.txt", "fixture telegram receipt")
        ack = self._evidence(output, "ack.txt", "fixture acknowledgement")
        record_receipt(
            output, channel="EMAIL", attempt_minute=0,
            sent_utc="2026-08-24T12:00:10Z", received_utc="2026-08-24T12:00:20Z",
            transport_receipt_file=email,
        )
        record_receipt(
            output, channel="TELEGRAM_PUSH", attempt_minute=0,
            sent_utc="2026-08-24T12:00:10Z", received_utc="2026-08-24T12:00:15Z",
            transport_receipt_file=telegram,
        )
        record_ack(
            output, acknowledged_utc="2026-08-24T12:01:00Z",
            acknowledgement_evidence_file=ack,
        )
        result = verify_private_evidence(output)
        self.assertEqual("PASS_SPEC_ONLY", result["status"], result["reasons"])
        self.assertFalse(result["risk_authority_restored"])
        with self.assertRaisesRegex(ValueError, "duplicate acknowledgement"):
            record_ack(
                output, acknowledged_utc="2026-08-24T12:01:30Z",
                acknowledgement_evidence_file=ack,
            )
        with self.assertRaisesRegex(ValueError, "already acknowledged"):
            record_receipt(
                output, channel="EMAIL", attempt_minute=5,
                sent_utc="2026-08-24T12:05:00Z", received_utc="2026-08-24T12:05:10Z",
                transport_receipt_file=email,
            )

    def test_duplicate_invalid_and_external_receipts_fail_closed(self):
        output = self._prepared()
        receipt = self._evidence(output, "receipt.txt", "fixture")
        record_receipt(
            output, channel="EMAIL", attempt_minute=0,
            sent_utc="2026-08-24T12:00:10Z", received_utc="2026-08-24T12:00:20Z",
            transport_receipt_file=receipt,
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            record_receipt(
                output, channel="EMAIL", attempt_minute=0,
                sent_utc="2026-08-24T12:00:10Z", received_utc="2026-08-24T12:00:20Z",
                transport_receipt_file=receipt,
            )
        with tempfile.NamedTemporaryFile() as outside:
            with self.assertRaisesRegex(ValueError, "inside private output"):
                record_receipt(
                    output, channel="TELEGRAM_PUSH", attempt_minute=0,
                    sent_utc="2026-08-24T12:00:10Z", received_utc="2026-08-24T12:00:20Z",
                    transport_receipt_file=Path(outside.name),
                )

    def test_tampered_audit_fails_closed(self):
        output = self._prepared()
        receipt = self._evidence(output, "receipt.txt", "fixture")
        record_receipt(
            output, channel="EMAIL", attempt_minute=0,
            sent_utc="2026-08-24T12:00:10Z", received_utc="2026-08-24T12:00:20Z",
            transport_receipt_file=receipt,
        )
        chain = output / "PRIVATE_ALERT_AUDIT.jsonl"
        chain.write_text(chain.read_text().replace('"attempt_minute":0', '"attempt_minute":5'))
        with self.assertRaisesRegex(ValueError, "audit chain invalid"):
            verify_private_evidence(output)

    def test_module_has_no_delivery_broker_or_process_capability(self):
        source = Path(__file__).with_name("private_delivery_evidence.py")
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imports = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                calls.add(node.func.id if isinstance(node.func, ast.Name)
                          else node.func.attr if isinstance(node.func, ast.Attribute) else "")
        self.assertFalse(imports & {
            "smtplib", "telegram", "requests", "socket", "MetaTrader5", "subprocess",
        })
        self.assertFalse(calls & {
            "sendmail", "send_message", "order_send", "order_check", "login",
            "system", "popen", "run", "Popen",
        })


if __name__ == "__main__":
    unittest.main()
