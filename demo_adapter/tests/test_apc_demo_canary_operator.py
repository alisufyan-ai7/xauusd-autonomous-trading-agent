"""Offline-only guardrails for the *unapproved* attended demo operator script."""
from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from xauusd_demo.envelope import DemoSafetyError

RUNNER = Path(__file__).resolve().parents[1] / (
    "scripts/apc_demo_canary_attended_operator.py"
)


def test_operator_defaults_to_denial_before_any_mt5_import_or_stage() -> None:
    script = runpy.run_path(str(RUNNER), run_name="offline_only")
    main = script["main"]
    with pytest.raises(DemoSafetyError, match="OWNER_AUTHORIZATION_REQUIRED"):
        main([
            "--mode", "entry", "--activation-id", "DENIED",
            "--expires-utc", "2026-10-20T16:00:00Z",
            "--side", "BUY", "--stop", "1990.00",
        ])


def test_operator_no_live_select_no_auto_loop_or_retry() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    for forbidden in (
        "mt5.login(", "mt5.account_select(", "symbol_select(", "order_send(",
        "subprocess.run(", "Register-ScheduledTask", "Start-ScheduledTask",
        "import MetaTrader5", "while True:", "for signal in",
    ):
        assert forbidden not in source, forbidden
    assert "EXPLICIT_APC_DEMO_CANARY_OWNER_AUTHORIZATION_REQUIRED" in source
    assert "CANARY_DURABLE_ONCE_LEDGER_NOT_STAGED" in source
    assert "CANARY_REQUIRES_SEPARATE_ATTENDED_CLOSE_INVOCATION" in source


def test_operator_is_separate_from_production_sealed_shadow() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "DemoCanaryLifecycle" in source
    assert "DemoControlStore" in source
    assert "CanaryJournal" in source
    assert "C:\\Program Files\\Python312\\python.exe" in source
    assert "C:\\Program Files\\MetaTrader 5\\terminal64.exe" in source
    assert "max_daily_submissions=1" in source
