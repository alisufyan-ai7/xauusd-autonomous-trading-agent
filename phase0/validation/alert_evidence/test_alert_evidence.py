import ast
import unittest
from pathlib import Path

from phase0.validation.alert_evidence.alert_oracle import canary_digest, verify_delivery


def bundle():
    digest=canary_digest("fixture")
    return {"schema":"a1-private-delivery-evidence-1.0","created_utc":"2026-08-23T12:00:00Z",
            "canary_sha256":digest,"designated_ack_role":"OWNER_DESIGNEE",
            "receipts":[
                {"channel":"EMAIL","attempt_minute":0,"canary_sha256":digest,"transport_receipt_sha256":"a"*64,"sent_utc":"2026-08-23T12:00:10Z","received_utc":"2026-08-23T12:00:20Z"},
                {"channel":"TELEGRAM_PUSH","attempt_minute":0,"canary_sha256":digest,"transport_receipt_sha256":"b"*64,"sent_utc":"2026-08-23T12:00:10Z","received_utc":"2026-08-23T12:00:15Z"}],
            "acknowledged_utc":"2026-08-23T12:01:00Z","ack_canary_sha256":digest}


class AlertEvidenceTests(unittest.TestCase):
    def test_dual_delivery_and_ack_pass_only_as_spec_evidence(self):
        result=verify_delivery(bundle())
        self.assertEqual("PASS_SPEC_ONLY",result["status"]); self.assertFalse(result["risk_authority_restored"])

    def test_missing_channel_fails_closed(self):
        row=bundle(); row["receipts"]=row["receipts"][:1]
        self.assertIn("DUAL_PATH_INCOMPLETE",verify_delivery(row)["reasons"])

    def test_late_delivery_or_ack_fails_closed(self):
        row=bundle(); row["receipts"][1]["received_utc"]="2026-08-23T12:16:00Z"
        self.assertIn("DELIVERY_OUTSIDE_A1_DEADLINE",verify_delivery(row)["reasons"])
        row=bundle(); row["acknowledged_utc"]="2026-08-23T12:16:00Z"
        self.assertIn("ACK_OUTSIDE_A1_DEADLINE",verify_delivery(row)["reasons"])

    def test_digest_and_receipt_binding_are_mandatory(self):
        row=bundle(); row["receipts"][0]["canary_sha256"]="0"*64
        self.assertIn("RECEIPT_BINDING_INVALID",verify_delivery(row)["reasons"])

    def test_five_minute_repeats_are_required_until_ack(self):
        row=bundle(); row["acknowledged_utc"]="2026-08-23T12:12:00Z"
        self.assertIn("REQUIRED_REPEAT_MISSING",verify_delivery(row)["reasons"])

    def test_modules_have_no_network_messaging_or_broker_capability(self):
        for name in ("alert_oracle.py","prepare_private_canary.py"):
            tree=ast.parse(Path(__file__).with_name(name).read_text(encoding="utf-8"))
            imports=set(); calls=set()
            for node in ast.walk(tree):
                if isinstance(node,ast.Import): imports.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node,ast.ImportFrom) and node.module: imports.add(node.module.split(".")[0])
                elif isinstance(node,ast.Call): calls.add(node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else "")
            self.assertFalse(imports & {"smtplib","telegram","requests","socket","MetaTrader5","subprocess"})
            self.assertFalse(calls & {"sendmail","send_message","order_send","order_check","login"})
        runner=Path(__file__).with_name("run_prepare_private_canary.ps1").read_text(encoding="utf-8")
        for forbidden in ("Send-MailMessage","Invoke-RestMethod","Invoke-WebRequest","telegram"):
            self.assertNotIn(forbidden,runner)


if __name__=="__main__": unittest.main()
