"""S2 execution-off stage helper: parse and embedded source safety, no VPS runs."""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "phase0/ops/apc-demo-canary-s2-execution-off-stage.ps1"
FROZEN_S2_HEAD = "ac54a99e4d9ad2ea2b88725824a7b5ece54a12f4"
FROZEN_S2_SHA = "e51a8f9a2820352f63c0fe4b51dcdd9b72f8b01554f73b72590f10f2c78583d1"
FROZEN_MANIFEST = "02fc91865aa7db2cf40feb81d236fa2ebba5db7318e6e815ac4ec4c4d903ccd7"


def _embedded_python() -> str:
    source = SCRIPT.read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^\$StagePython = @'\n(.*?)\n'@\n\$Canonical",
        source,
    )
    assert match is not None
    return match.group(1) + "\n"


def test_s2_staging_embedded_python_exact_hash_and_compile_only() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    embedded = _embedded_python()
    sha = hashlib.sha256(embedded.encode("ascii")).hexdigest()
    assert sha == "b9d2a6e09e7c4eb57633938bc7150ed2391feb5e4c6e8787a53004b853e1bbf5"
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
