import json
from pathlib import Path

ROOT = Path(__file__).parents[3]
WINDOWS = ROOT / "deploy" / "windows"


def test_windows_settings_are_execution_disabled():
    settings = json.loads((WINDOWS / "candidate.settings.json").read_text(encoding="utf-8"))
    assert settings["execution_enabled"] is False
    assert settings["execution_mode"] == "DISABLED_NO_ADAPTER"
    assert settings["broker_action_count_limit"] == 0
    assert settings["analyst_transport_enabled"] is False
    assert settings["alert_delivery_enabled"] is False


def test_installer_and_rollback_require_exact_confirmation_tokens():
    installer = (WINDOWS / "Install-ExecutionDisabledCandidate.ps1").read_text(encoding="utf-8")
    rollback = (WINDOWS / "Invoke-ExecutionDisabledRollback.ps1").read_text(encoding="utf-8")
    assert 'ValidateSet("INSTALL-EXECUTION-DISABLED-CANDIDATE")' in installer
    assert 'ValidateSet("ROLLBACK-EXECUTION-DISABLED-CANDIDATE")' in rollback
    assert "service_started = $false" in installer
    assert "service_restarted = $false" in rollback


def test_preflight_requires_hash_manifest_and_zero_capability():
    preflight = (WINDOWS / "Test-ExecutionDisabledCandidate.ps1").read_text(encoding="utf-8")
    assert 'Join-Path $ReleaseRoot "release-manifest.json"' in preflight
    assert "Get-FileHash -LiteralPath $FilePath -Algorithm SHA256" in preflight
    assert "Manifest broker action limit is not zero" in preflight
