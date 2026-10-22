"""Safe smoke tests for the standalone *read-only* VPS diagnostic script."""

from __future__ import annotations

import ast
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

PROBE = (
    Path(__file__).resolve().parents[3]
    / "phase0/ops/v2_pr33_readonly_mt5_seven_frames_probe_20261022.py"
)


def _load() -> dict[str, object]:
    return runpy.run_path(str(PROBE), run_name="v2_broker_probe_library_no_main")


def test_probe_source_parses_and_has_no_mt5_order_mutation_calls() -> None:
    parsed = ast.parse(PROBE.read_text(encoding="utf-8"))
    forbidden = {
        "order_send", "order_check", "positions_close", "terminal_set",
        "login", "symbol_select",
    }
    invoked = {
        node.func.attr
        for node in ast.walk(parsed)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not forbidden.intersection(invoked)


def test_probe_requires_explicit_readonly_flag(
    monkeypatch, capsys,
) -> None:
    data = _load()
    monkeypatch.setattr(sys, "argv", ["test-probe"])
    assert data["main"]() == 2
    assert "NOT_EXECUTED_REQUIRE_CONFIRM_READONLY" in capsys.readouterr().out


def test_probe_reports_synthetic_history_shortfall_as_failure(
    monkeypatch, capsys,
) -> None:
    data = _load()
    main = data["main"]
    assert callable(main)
    main.__globals__["capture"] = lambda: {
        "status": "READ_ONLY_HISTORY_SHORTFALL_FAIL_CLOSED",
        "all_requested_history_available": False,
        "order_api_calls": 0,
    }
    monkeypatch.setattr(sys, "argv", ["test-probe", "--confirm-readonly"])
    assert main() == 1
    output = capsys.readouterr().out
    assert "READ_ONLY_HISTORY_SHORTFALL_FAIL_CLOSED" in output
    assert "order_api_calls" in output



@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell 5.1 parser is Windows-only")
def test_attended_readonly_powershell_wrapper_syntax() -> None:
    script = (
        Path(__file__).resolve().parents[3]
        / "phase0/ops/v2_pr33_attended_readonly_mt5_probe_20261022.ps1"
    )
    path = str(script).replace("'", "''")
    parse = (
        "$tokens = $null; $errorsFound = $null; "
        "$null = [System.Management.Automation.Language.Parser]::ParseFile("
        f"'{path}', [ref]$tokens, [ref]$errorsFound); "
        "if ($errorsFound.Count -ne 0) {"
        " $errorsFound | Out-String | Write-Error; exit 1 }"
    )
    # Windows-hosted CI only; executable path is absolute and the quoted
    # parse target is this repository's known script, never external input.
    subprocess.run(  # noqa: S603
        [
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            "-NoProfile", "-NonInteractive", "-Command", parse,
        ],
        capture_output=True, text=True, check=True,
    )



@pytest.mark.skipif(
    sys.platform != "win32",
    reason="PowerShell native argument parsing is Windows-only",
)
def test_attended_readonly_python_version_guard_executes_under_windows_powershell() -> None:
    """Regression for user-observed stripped quotes in PowerShell -c f-strings."""
    script = (
        Path(__file__).resolve().parents[3]
        / "phase0/ops/v2_pr33_attended_readonly_mt5_probe_20261022.ps1"
    )
    version_line = next(
        line.strip()
        for line in script.read_text(encoding="utf-8-sig").splitlines()
        if line.startswith("$pyver = ")
    )
    python_exe = str(Path(sys.executable)).replace("'", "''")
    check = (
        f"$Python = '{python_exe}'; "
        f"{version_line}; "
        "if ($LASTEXITCODE -ne 0 -or $pyver.Trim() -ne '312') { "
        "throw 'Invalid Python3.12 version probe'; }; "
        "Write-Output 'PY312_NATIVE_ARG_VERSION_PASS'"
    )
    # Fixed executable and code from the checked-out project, no user input.
    result = subprocess.run(  # noqa: S603
        [
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            "-NoProfile", "-NonInteractive", "-Command", check,
        ],
        capture_output=True, text=True, check=True,
    )
    assert "PY312_NATIVE_ARG_VERSION_PASS" in result.stdout



@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("XAUUSD quote unavailable; source proof incomplete", "QUOTE_UNAVAILABLE"),
        ("QUOTE_TIMESTAMP_FUTURE", "QUOTE_TIMESTAMP_FUTURE"),
        ("QUOTE_TIMESTAMP_STALE", "QUOTE_TIMESTAMP_STALE"),
        ("W1 empty broker result", "W1_EMPTY_BROKER_HISTORY"),
        ("M1 empty broker result", "M1_EMPTY_BROKER_HISTORY"),
        ("H4 contains a forming candle", "H4_FORMING_BAR"),
        ("M5 contains a forming candle", "M5_FORMING_BAR"),
    ],
)
def test_sanitized_probe_reason_codes_never_reveal_raw_exception_details(
    message: str, expected: str
) -> None:
    mapping = _load()["_public_failure_reason"]
    assert mapping(RuntimeError(message)) == expected
    private_detail = "SYNTHETIC_SECRET_DO_NOT_PRINT"
    assert private_detail not in mapping(RuntimeError(private_detail))
    assert mapping(RuntimeError(private_detail)) == "UNCLASSIFIED_RUNTIME_ERROR"
    assert mapping(ValueError(private_detail)) == "UNCLASSIFIED_READONLY_FAILURE"


def test_probe_failure_output_includes_only_fixed_sanitized_code(
    monkeypatch, capsys
) -> None:
    data = _load()
    main = data["main"]

    def fail_as_stale_quote():
        raise RuntimeError("QUOTE_TIMESTAMP_STALE")

    main.__globals__["capture"] = fail_as_stale_quote
    monkeypatch.setattr(sys, "argv", ["probe", "--confirm-readonly"])
    assert main() == 1
    output = capsys.readouterr().out
    assert '"reason_code": "QUOTE_TIMESTAMP_STALE"' in output
    assert '"order_api_calls": 0' in output
    assert "login" not in output.casefold()
