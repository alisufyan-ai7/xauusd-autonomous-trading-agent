"""Synthetic-only v1.2 read-only host, PS5.1 parser and approval-gate tests."""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import shutil
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts import v12_windows_mt5_readonly_host as host
from scripts.v11_readonly_collector import CaptureSafetyError

BASE = Path(__file__).resolve().parents[1]
SCRIPTS = BASE / "scripts"


def fixture() -> dict[str, Any]:
    rec: dict[str, Any] = {
        "exact_window_start_utc": "2026-10-26T12:30:00Z",
        "exact_window_end_utc": "2026-10-26T16:30:00Z",
        "v12_overlap_start_utc": "2026-10-26T13:30:00Z",
        "v12_overlap_end_utc": "2026-10-26T16:30:00Z",
        "expected_demo_identity_fingerprint_sha256": host.EXPECTED_IDENTITY,
        "registration_sha256": "a" * 64,
        "exact_collector_source_sha256": "b" * 64,
        "broker_xauusd_session_source_sha256": "c" * 64,
        "official_event_guard_health_and_event_schedule_sha256": "d" * 64,
        "exact_owner_approval_id": "SYNTHETIC_NOT_REAL_APPROVAL",
        "owner_first_run_confirmation_id": "SYNTHETIC_NOT_REAL_APPROVAL",
        "owner_capture_decision": "OWNER_APPROVED_READ_ONLY_XAUUSD_V11_CAPTURE",
        "approval_for_vps_capture": "EXPLICIT_OWNER_APPROVED",
        "output_scope": "PRIVATE_LOCAL_EXNESS_DEMO_ONLY",
        "approved_pr13_design_sha": host.DESIGN_SHA,
        "approved_pr14_evidence_sha": host.PREP_SHA,
        "calibration_status": "NOT_ADMITTED",
        "tradeapi_disabled_required": True,
        "known_positions_zero_required": True,
        "source_origin_review_is_not_hash_authentication": True,
        "real_window_prospective_frozen": True,
        "xauusd_date_specific_open_full": True,
        "event_guard_healthy_now": True,
        "window_no_blocked_events_verified": True,
        "owner_validated_private_destination": True,
    }
    for source in (
        "holiday_dst_sha256", "bls_sha256", "bea_sha256",
        "fed_sha256", "census_sha256", "dol_sha256",
        "symbol_and_fee_source_sha256", "pre_demo_slippage_proxy_sha256",
        "gap_proxy_sha256", "independent_source_origin_review_sha256",
        "collector_ps_sha256", "verifier_ps_sha256",
        "risk_source_sha256", "read_only_core_source_sha256",
    ):
        rec[source] = "e" * 64
    return rec


def test_injected_synthetic_complete_registration_never_proves_authenticity() -> None:
    contract = host._preregistered(fixture(), "SYNTHETIC_NOT_REAL_APPROVAL")
    assert contract.end_utc - contract.start_utc == timedelta(hours=4)
    assert contract.expected_identity_sha256 == host.EXPECTED_IDENTITY


@pytest.mark.parametrize(("name", "bad"), [
    ("approved_pr13_design_sha", "1" * 40),
    ("approved_pr14_evidence_sha", "1" * 40),
    ("exact_owner_approval_id", "PENDING"),
    ("owner_first_run_confirmation_id", None),
    ("approval_for_vps_capture", "NOT_APPROVED"),
    ("owner_capture_decision", "FUTURE"),
    ("output_scope", "GITHUB_PUBLIC"),
    ("real_window_prospective_frozen", False),
    ("xauusd_date_specific_open_full", None),
    ("event_guard_healthy_now", False),
    ("window_no_blocked_events_verified", False),
    ("tradeapi_disabled_required", False),
    ("calibration_status", "ADMITTED"),
    ("bls_sha256", None),
    ("read_only_core_source_sha256", "f"),
])
def test_unapproved_broker_or_provenance_record_fails_closed(
    name: str, bad: Any
) -> None:
    rec = fixture()
    rec[name] = bad
    with pytest.raises(CaptureSafetyError):
        host._preregistered(rec, "SYNTHETIC_NOT_REAL_APPROVAL")


def test_overlap_must_stay_inside_full_four_hour_window() -> None:
    rec = fixture()
    rec["v12_overlap_start_utc"] = "2026-10-26T11:30:00Z"
    with pytest.raises(CaptureSafetyError, match="overlap"):
        host._preregistered(rec, "SYNTHETIC_NOT_REAL_APPROVAL")


def test_static_meta_trader_calls_exact_readonly_whitelist() -> None:
    source = inspect.getsource(host)
    for bad in ("order_" + "send(", "order_" + "check(",
                "order_" + "calc_margin(", "order_" + "calc_profit(",
                "order_" + "cancel(", "order_" + "close(",
                "login(", "symbol_select(", "subprocess.", "os.system("):
        assert bad not in source
    assert 'history_deals_get(start - timedelta(days=7), end, group="XAUUSD")' in source
    assert "mt5.initialize(str(x.terminal_path))" in source
    assert "mt5.shutdown()" in source


def test_registration_exact_file_sha_fails_if_tampered(tmp_path: Path) -> None:
    registration = tmp_path / "rehearsal.json"
    registration.write_text(json.dumps(fixture()), encoding="utf-8")
    good = hashlib.sha256(registration.read_bytes()).hexdigest()
    assert host._read_verified(registration, good)["approved_pr13_design_sha"] == host.DESIGN_SHA
    registration.write_text(json.dumps(fixture()) + " ", encoding="utf-8")
    with pytest.raises(CaptureSafetyError, match="SHA mismatch"):
        host._read_verified(registration, good)


def test_raw_history_zero_does_not_create_calibration(tmp_path: Path) -> None:
    class FakeMT5:
        def history_deals_get(self, start: Any, end: Any, group: str) -> list[Any]:
            assert group == "XAUUSD"
            assert end - start == timedelta(days=7, hours=4)
            return []
    from datetime import UTC, datetime

    st = datetime(2026, 10, 26, 12, 30, tzinfo=UTC)
    res = host._history(FakeMT5(), st, st + timedelta(hours=4))
    assert res["status"] == "READ_ONLY_ACCOUNT_SPECIFIC_HISTORY_NOT_RECONCILED"
    assert res["deal_count"] == 0
    assert res["deals"] == []


def test_no_ps_scheduled_task_mutations_and_verifier_no_mt5() -> None:
    collect = (SCRIPTS / "v12-readonly-collector.ps1").read_text("utf-8").lower()
    verify = (SCRIPTS / "v12-readonly-verifier.ps1").read_text("utf-8").lower()
    for item in ("register-scheduledtask", "set-scheduledtask", "unregister-scheduledtask",
                 "start-scheduledtask", "stop-scheduledtask", "schtasks.exe",
                 "order_send(", "order_check(", "order_calc_margin("):
        assert item not in collect
        assert item not in verify
    assert "get-filehash" in collect and "get-filehash" in verify
    assert "terminal_info" not in verify
    assert "python.exe" in collect


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PS5.1 parser only")
def test_windows_powershell_v12_collector_and_verifier_parse_only() -> None:
    shell = shutil.which("powershell.exe") or shutil.which("powershell")
    if shell is None:
        pytest.skip("Windows PowerShell 5.1 binary missing")
    for filename in ("v12-readonly-collector.ps1", "v12-readonly-verifier.ps1"):
        path = SCRIPTS / filename
        ps = (
            "$tokens=$null;$errors=$null;"
            "[System.Management.Automation.Language.Parser]::ParseFile("
            f"'{str(path).replace(chr(39), chr(39) + chr(39))}',"
            "[ref]$tokens,[ref]$errors)|Out-Null;"
            "if($errors.Count -ne 0){$errors|Out-String|Write-Host;exit 91}"
        )
        result = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=20, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        assert result.returncode == 0, result.stdout + result.stderr
