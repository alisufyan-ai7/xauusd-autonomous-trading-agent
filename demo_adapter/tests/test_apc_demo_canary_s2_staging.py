"""S2 execution-off stage helper: parse and embedded source safety, no VPS runs."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "phase0/ops/apc-demo-canary-s2-execution-off-stage.ps1"
FROZEN_S2_HEAD = "89711065a3a2d38fe02282fff3ad1782aabda0d2"
FROZEN_S2_SHA = "6c37704c7d2d661ccb2b8fd4fbd5340ec35fb210f1cf9528452bc89bd08c1a4e"
FROZEN_MANIFEST = "70bf8637208772e91a64b7af2cc06997847dc557752b05d9225b735b30ff13be"


def _embedded_python() -> str:
    source = SCRIPT.read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^\$StagePython = @'\n(.*?)\n'@\n\$Canonical",
        source,
    )
    assert match is not None
    # Mirror ACTUAL PowerShell: here-string value may end with LF already.
    return match.group(1).rstrip("\r\n") + "\n"


def test_s2_staging_embedded_python_exact_hash_and_compile_only() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert hashlib.sha256(SCRIPT.read_bytes()).hexdigest() == (
        "fdb5624830b0741437b0a7e8697491db687c7e2d8af9b0ef494217d5556951e1"
    )
    artifact_default = next(
        line for line in source.splitlines()
        if line.strip().startswith("[string] $Artifact =")
    )
    assert "github-actions-artifact-12289594320.zip" in artifact_default
    assert "12289113540" not in artifact_default
    assert "github-actions-artifact-12289113540.zip" not in source
    assert "$ExpectedStageScriptSHA = " in source
    embedded = _embedded_python()
    sha = hashlib.sha256(embedded.encode("ascii")).hexdigest()
    assert sha == "3cf6ad71737766365874eef4d950fc93ae4169c60e1158ff1735e9dabf82a648"
    assert sha in source
    compile(embedded, str(SCRIPT) + ":in-memory-embedded-python", "exec")
    assert FROZEN_S2_HEAD in embedded
    assert FROZEN_S2_SHA in embedded
    assert FROZEN_MANIFEST in embedded
    assert "XAUUSD-APC-DEMO-CANARY-S2" in source
    assert "XAUUSD-APC-DEMO-CANARY-S2-S2" not in source
    assert "ISOLATED_STAGE_ALREADY_EXISTS_NO_RETRY_NO_OVERWRITE" in embedded
    assert "STAGED_SOURCE_OR_WHEEL_COPY_SHA_MISMATCH" in embedded
    assert "UNAUTHORIZED_METATRADER5_IMPORT_IN_OFFLINE_STAGE" in embedded
    assert "APC_STAGE_SUCCESS_EXECUTION_OFF_NO_TRADING" in embedded
    assert "APC_STAGE_VERIFIED__KILLED__UNUSED__MT5_UNTOUCHED" in source
    # Confirm the in-memory source is pinned independently from the PS wrapper.
    assert "3cf6ad71737766365874eef4d950fc93ae4169c60e1158ff1735e9dabf82a648" in source
    assert "github-actions-artifact-12289594320.zip" in source
    for forbidden in (
        "mt5.initialize(", "mt5.order_send(", "mt5.login(",
        "Register-ScheduledTask", "Start-ScheduledTask",
    ):
        assert forbidden not in source


@pytest.mark.skipif(sys.platform != "win32", reason="native PS5.1 parser only")
def test_s2_stage_ps51_syntax_without_execution() -> None:
    shell = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    assert shell.is_file()
    parser = (
        "$err=$null;$tokens=$null;"
        "[System.Management.Automation.Language.Parser]::ParseFile("
        "'" + str(SCRIPT).replace("'", "''") + "',"
        "[ref]$tokens,[ref]$err)|Out-Null;"
        "if($err.Count -gt 0){$err|Format-List;exit 18};"
        "'S2_STAGE_PS51_PARSER_PASS'"
    )
    result = subprocess.run(  # noqa: S603 (CI parser only; no stage or Python)
        [str(shell), "-NoProfile", "-NonInteractive", "-Command", parser],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_main_state_source_of_truth_points_to_live_main_and_preserves_history() -> None:
    current = "ccaa8338aecee8bd3afbc358644410dff6c512e5"
    old_merge = "33b7ebb664d4c343dd6d8dc77544cfdb17bab6bf"
    md = (ROOT / "phase0/roadmap/CURRENT_PROJECT_STATE.md").read_text(
        encoding="utf-8"
    )
    state = json.loads(
        (ROOT / "phase0/roadmap/CURRENT_PROJECT_STATE_2026-10-18.json").read_text(
            encoding="utf-8"
        )
    )
    assert f"**Current merged `main`:** `{current}`" in md
    assert state["authoritative_main_sha"] == current
    assert state["pr6"]["merge_sha"] == old_merge
    # The historic PR6 merge SHA may also be cited in the new correction note.
    # Enforce its factual lineage, not an arbitrary number of mentions.
    assert old_merge in md
    assert json.dumps(state).count(old_merge) == 1


@pytest.mark.skipif(sys.platform != "win32", reason="native PS5.1 AST only")
def test_s2_stage_native_ps51_here_string_value_hash_matches_pin() -> None:
    """Hash the native AST-decoded here-string, never execute staging source."""
    shell = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    assert shell.is_file()
    source = str(SCRIPT).replace("'", "''")
    command = (
        "$ErrorActionPreference='Stop';"
        "$err=$null;$tok=$null;"
        "$ast=[System.Management.Automation.Language.Parser]::ParseFile("
        "'" + source + "',[ref]$tok,[ref]$err);"
        "if($err.Count){throw 'PS51_SYNTAX_ERROR'};"
        "$nodes=@($ast.FindAll({param($n)"
        "$n -is [System.Management.Automation.Language.StringConstantExpressionAst]"
        " -and $n.Extent.Text.StartsWith(\"@'\")},$true));"
        "if($nodes.Count -ne 1){throw 'PS51_HERESTRING_COUNT_MISMATCH'};"
        "$canonical=$nodes[0].Value.Replace(\"`r`n\",\"`n\").Replace(\"`r\",\"`n\");"
        "$canonical=$canonical.TrimEnd([char[]]@([char]13,[char]10))+\"`n\";"
        "$bytes=[Text.Encoding]::ASCII.GetBytes($canonical);"
        "$h=[Security.Cryptography.SHA256]::Create();"
        "try{$actual=[BitConverter]::ToString($h.ComputeHash($bytes))"
        ".Replace('-','').ToLowerInvariant()}finally{$h.Dispose()};"
        "if($actual -cne '3cf6ad71737766365874eef4d950fc93ae4169c60e1158ff1735e9dabf82a648')"
        "{throw ('PS51_ACTUAL_HASH_DIFFERS='+$actual)};"
        "Write-Output ('PS51_STAGING_HELPER_CANONICAL_SHA256='+$actual)"
    )
    result = subprocess.run(  # noqa: S603 (native AST-only; no execution)
        [str(shell), "-NoProfile", "-NonInteractive", "-Command", command],
        check=False, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    marker = "PS51_STAGING_HELPER_CANONICAL_SHA256="
    assert marker + "3cf6ad71737766365874eef4d950fc93ae4169c60e1158ff1735e9dabf82a648" in result.stdout
