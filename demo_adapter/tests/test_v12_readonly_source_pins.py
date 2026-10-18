"""Independently recompute published SHA-256 from exact checkout file bytes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / (
    "phase0/roadmap/DEMO_V12_READONLY_SOURCE_SHA256_PIN_MANIFEST_2026-10-19.json"
)


def test_published_sha256_source_bytes_match_both_os_checkouts() -> None:
    packet = json.loads(MANIFEST.read_text("utf-8"))
    assert packet["status"] == "REVIEWED_CODE_HASHES_ONLY_NEVER_OWNER_RUN_PERMIT"
    assert len(packet["files"]) == 7
    for entry in packet["files"]:
        raw = (ROOT / entry["path"]).read_bytes()
        assert b"\r\n" not in raw, entry["path"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"], entry["path"]


def test_frozen_methods_and_actual_source_permissions_still_denied() -> None:
    record = json.loads(MANIFEST.read_text("utf-8"))
    assert record["owner_approved_design_pr13_sha"] == (
        "847829378956670e8936bf46c82e685de41145fd"
    )
    assert record["offline_preflight_pr14_sha"] == (
        "9d768fcfd160b3ccfc92ecef44fe040da6b77db6"
    )
    assert record["real_broker_and_official_sources_sha256_verified"] is False
    assert record["official_exness_date_specific_xauusd_sha256"] is None
    assert record["event_guard_health_for_window_sha256"] is None
    assert record["exact_utc_capture_window"] is None
    assert record["independent_first_actual_execution_approval_id"] is None
    assert record["private_vps_output_path"] is None


def test_readonly_ps_byte_pins_are_never_reinterpreted_as_run_permission() -> None:
    record = json.loads(MANIFEST.read_text("utf-8"))
    pinned = {entry["path"]: entry for entry in record["files"]}
    for filename in ("v12-readonly-collector.ps1", "v12-readonly-verifier.ps1"):
        relative = "demo_adapter/scripts/" + filename
        assert relative in pinned
        assert len(pinned[relative]["sha256"]) == 64
    assert record["no_execution_trading_permit"] is True
