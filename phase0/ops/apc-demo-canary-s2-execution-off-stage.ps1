# APC-DEMO-CANARY S2 prospective execution-OFF STAGING ONLY. NEW approval required.
# No MT5 import, MT5 initialize, login, quote read, order API or scheduler changes.
# Exact S2 successor bundle; no Git/network or worktree changes. NOT YET AUTHORIZED.
[CmdletBinding()]
param(
    [string] $Artifact = (Join-Path $env:USERPROFILE 'Downloads\github-actions-artifact-12289113540.zip')
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$PythonExe = 'C:\Program Files\Python312\python.exe'
$StageRoot = Join-Path $env:LOCALAPPDATA 'XAUUSD-APC-DEMO-CANARY-S2'
$ExpectedTerminal = 'C:\Program Files\MetaTrader 5\terminal64.exe'
$ExpectedStageScriptSHA = 'b9d2a6e09e7c4eb57633938bc7150ed2391feb5e4c6e8787a53004b853e1bbf5'

if (-not [IO.File]::Exists($PythonExe)) {
    throw 'APC_STAGE_PINNED_PYTHON_NOT_FOUND__NO_STAGE'
}
if (-not [IO.File]::Exists($Artifact)) {
    throw ('APC_STAGE_GITHUB_ARTIFACT_MISSING__' + $Artifact)
}
if (Test-Path -LiteralPath $StageRoot) {
    throw 'APC_STAGE_ROOT_ALREADY_EXISTS__NO_RETRY_OR_OVERWRITE'
}
$ExistingTerminal = @(Get-Process -Name terminal64 -ErrorAction SilentlyContinue)
if ($ExistingTerminal.Count -ne 1) {
    throw 'APC_STAGE_TERMINAL_SINGLETON_NOT_PRESERVED__NO_STAGE'
}
if (-not [string]::Equals($ExistingTerminal[0].Path, $ExpectedTerminal,
                        [StringComparison]::OrdinalIgnoreCase)) {
    throw 'APC_STAGE_EXISTING_TERMINAL_PATH_MISMATCH__NO_STAGE'
}
$BeforeTerminalPid = [int]$ExistingTerminal[0].Id

$StagePython = @'
"""APC demo execution-OFF staging. No MetaTrader5 import/attach or orders.

Runs only from a separately owner-approved attended Windows PowerShell wrapper.
All mutations confined to a NEW %LOCALAPPDATA%/XAUUSD-APC-DEMO-CANARY-S2 tree.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import zipfile

HEAD = "ac54a99e4d9ad2ea2b88725824a7b5ece54a12f4"
INNER_NAME = f"apc-demo-canary-{HEAD}.zip"
INNER_SHA = "e51a8f9a2820352f63c0fe4b51dcdd9b72f8b01554f73b72590f10f2c78583d1"
MANIFEST_SHA = "02fc91865aa7db2cf40feb81d236fa2ebba5db7318e6e815ac4ec4c4d903ccd7"
FILES = {
    "source/demo_adapter/scripts/apc-demo-canary-readonly-preflight.ps1":
        "11db0ba0877f29ddf62ff0b626dc060d80393176f79d97f7e8dca32f20154519",
    "source/demo_adapter/scripts/apc-demo-canary-s2-attended.ps1":
        "59bcc2b329313120fb1421e0cd98697b24c6f7989ad5075f3ed10aaec6cac7a7",
    "source/demo_adapter/scripts/apc_demo_canary_attended_operator.py":
        "44279a0b806f131e73c6637d38943a1c1f9e34b1c8226281b0a886765ac75278",
    "source/demo_adapter/scripts/apc_demo_canary_readonly_preflight.py":
        "484348e154e3072192b9a4b1fa8031b457355e6c46035bc1696ee22afcfabfc6",
    "source/demo_adapter/scripts/apc_demo_canary_s2_isolated_loader.py":
        "70ae8a926015f3ebbdc22a64b5d7fe14d532539e09f244c62b3eed148f881bc0",
    "wheel/xauusd_demo_adapter-0.1.0.dev0-py3-none-any.whl":
        "b09ffe222f4529a56c9bf46e08e1aa4837c5434085167067eced0e1c92cbea5e",
    "wheel/xauusd_production_candidate-0.1.0.dev0-py3-none-any.whl":
        "67ca587d565af88f55289f726468333c730325e11fd8714fc56f3267cea6537b",
}
EXPECTED_PYTHON = r"C:\Program Files\Python312\python.exe"


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_inner(inner_data: bytes) -> tuple[dict[str, bytes], dict[str, object]]:
    if digest(inner_data) != INNER_SHA:
        raise ValueError("SEALED_INNER_SHA256_MISMATCH_NO_STAGE")
    with zipfile.ZipFile(io.BytesIO(inner_data)) as archive:
        if set(archive.namelist()) != {"manifest.json", *FILES}:
            raise ValueError("SEALED_INNER_ENTRY_LIST_MISMATCH")
        if len(archive.infolist()) != 8:
            raise ValueError("SEALED_INNER_DUPLICATE_OR_EXTRA_ENTRY")
        manifest_bytes = archive.read("manifest.json")
        if digest(manifest_bytes) != MANIFEST_SHA:
            raise ValueError("MANIFEST_SHA_MISMATCH")
        manifest = json.loads(manifest_bytes)
        if (manifest.get("exact_git_head") != HEAD or
            manifest.get("broker_action_authorized") is not False or
            manifest.get("vps_staging_authorized") is not False or
            manifest.get("mt5_python_execution_authorized") is not False):
            raise ValueError("UNAPPROVED_OR_WRONG_GITHUB_PROVENANCE")
        items = manifest.get("source_files")
        if not isinstance(items, list) or len(items) != len(FILES):
            raise ValueError("MANIFEST_COMPONENT_COUNT_MISMATCH")
        listed = {v["path"]: v["sha256"] for v in items}
        if listed != FILES:
            raise ValueError("MANIFEST_COMPONENT_HASH_MISMATCH")
        payloads = {}
        for meta in archive.infolist():
            if meta.is_dir() or meta.file_size > 2_000_000:
                raise ValueError("UNEXPECTED_ARCHIVE_FILE_SIZE_OR_DIRECTORY")
            if stat.S_ISLNK(meta.external_attr >> 16):
                raise ValueError("SYMLINK_DISALLOWED")
            content = archive.read(meta)
            if meta.filename != "manifest.json":
                if digest(content) != FILES[meta.filename]:
                    raise ValueError("BAD_COMPONENT_SHA_" + meta.filename)
                if len(content) != next(item["bytes"] for item in items
                                        if item["path"] == meta.filename):
                    raise ValueError("BAD_COMPONENT_LENGTH")
            payloads[meta.filename] = content
    return payloads, manifest


def validate_outer(path: Path) -> tuple[bytes, dict[str, bytes], dict[str, object]]:
    if not path.is_file() or path.stat().st_size > 10_000_000:
        raise ValueError("MISSING_OR_OVERSIZED_GITHUB_TRANSPORT_ZIP")
    with zipfile.ZipFile(path) as transport:
        if transport.namelist() != [INNER_NAME]:
            raise ValueError("GITHUB_OUTER_ARTIFACT_UNEXPECTED_ENTRIES")
        entry = transport.infolist()[0]
        if entry.file_size > 5_000_000:
            raise ValueError("GITHUB_OUTER_INNER_OVERSIZED")
        inner_data = transport.read(entry)
    entries, manifest = validate_inner(inner_data)
    return inner_data, entries, manifest


def unpack_pure_wheels(contents: dict[str, bytes], site: Path) -> int:
    count = 0
    for name in sorted(k for k in contents if k.startswith("wheel/")):
        wheel = zipfile.ZipFile(io.BytesIO(contents[name]))
        with wheel:
            info = wheel.infolist()
            if len(info) > 500:
                raise ValueError("WHEEL_TOO_MANY_FILES")
            meta = [x for x in info if x.filename.endswith(".dist-info/WHEEL")]
            if len(meta) != 1:
                raise ValueError("WHEEL_METADATA_MISMATCH")
            metadata = wheel.read(meta[0]).decode("ascii")
            if "Root-Is-Purelib: true" not in metadata or "Tag: py3-none-any" not in metadata:
                raise ValueError("NOT_PURE_PYTHON_ISOLATED_WHEEL")
            for item in info:
                parts = item.filename.split("/")
                if (item.is_dir() or not parts or any(p in ("", ".", "..") for p in parts)
                    or "\\" in item.filename or ":" in item.filename
                    or item.file_size > 2_000_000
                    or stat.S_ISLNK(item.external_attr >> 16)):
                    raise ValueError("UNSAFE_WHEEL_ARCHIVE_ENTRY")
                if not (parts[0] in {"xauusd_agent", "xauusd_demo"}
                        or parts[0].endswith(".dist-info")):
                    raise ValueError("UNEXPECTED_WHEEL_PACKAGE_PATH")
                target = site.joinpath(*parts)
                if target.exists():
                    raise ValueError("CROSS_WHEEL_FILE_COLLISION")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(wheel.read(item))
                count += 1
    return count


def apply_windows_acl(root: Path, user_sid: str) -> None:
    if not user_sid.startswith("S-1-"):
        raise ValueError("MISSING_OWNER_WINDOWS_SID")
    acl_args = [
        "icacls.exe", str(root), "/inheritance:r", "/grant:r",
        "*" + user_sid + ":(OI)(CI)F",
        "*S-1-5-18:(OI)(CI)F",  # SYSTEM
        "*S-1-5-32-544:(OI)(CI)F",  # Administrators
    ]
    check = subprocess.run(acl_args, check=False, capture_output=True, text=True)
    if check.returncode != 0:
        raise RuntimeError("FAILED_TO_RESTRICT_STAGING_ACL: " + check.stderr[:200])


def stage(artifact: Path, root: Path, user_sid: str, *, skip_acl: bool = False) -> None:
    if root.exists():
        raise ValueError("ISOLATED_STAGE_ALREADY_EXISTS_NO_RETRY_NO_OVERWRITE")
    inner, contents, manifest = validate_outer(artifact)
    # NOTHING has been written before this point. Now only approved isolated tree.
    root.mkdir(parents=False, exist_ok=False)
    if skip_acl:
        root.chmod(0o700)  # offline synthetic test, not available in VPS entrypoint
    else:
        apply_windows_acl(root, user_sid)
    (root / "site").mkdir()
    (root / "wheels").mkdir()
    (root / "sources").mkdir()
    (root / "sealed.zip").write_bytes(inner)
    (root / "manifest.json").write_bytes(contents["manifest.json"])
    for name in FILES:
        folder = root / ("wheels" if name.startswith("wheel/") else "sources")
        (folder / name.split("/")[-1]).write_bytes(contents[name])
    unpacked = unpack_pure_wheels(contents, root / "site")
    # Re-read ALL disk copies, not only the in-memory ZIP payloads.
    if digest((root / "sealed.zip").read_bytes()) != INNER_SHA:
        raise ValueError("STAGED_SEALED_COPY_SHA_MISMATCH")
    if digest((root / "manifest.json").read_bytes()) != MANIFEST_SHA:
        raise ValueError("STAGED_MANIFEST_COPY_SHA_MISMATCH")
    for name, expected_sha in FILES.items():
        folder = root / ("wheels" if name.startswith("wheel/") else "sources")
        if digest((folder / name.split("/")[-1]).read_bytes()) != expected_sha:
            raise ValueError("STAGED_SOURCE_OR_WHEEL_COPY_SHA_MISMATCH")
    # Import only audited LOCAL pure-Python modules; no MetaTrader5 module or broker.
    sys.path.insert(0, str(root / "site"))
    try:
        from xauusd_demo.control import DemoControlState, DemoControlStore
        from xauusd_demo.canary_lifecycle import CanaryJournal
        with DemoControlStore(root / "control.sqlite3") as control:
            snap = control.snapshot()
            if (snap.state is not DemoControlState.KILLED or snap.activation_id is not None
                or snap.account_id_sha256 is not None):
                raise ValueError("DEFAULT_CONTROL_NOT_KILLED_OR_NOT_UNBOUND")
        with CanaryJournal(root / "canary.sqlite3") as journal:
            if journal.stage() != "UNUSED":
                raise ValueError("CANARY_ONCE_BUDGET_NOT_UNUSED")
        with DemoControlStore(root / "control.sqlite3") as control:
            if control.snapshot().state is not DemoControlState.KILLED:
                raise ValueError("CONTROL_PERSISTENCE_FAILURE")
        with CanaryJournal(root / "canary.sqlite3") as journal:
            if journal.stage() != "UNUSED":
                raise ValueError("CANARY_JOURNAL_PERSISTENCE_FAILURE")
        if "MetaTrader5" in sys.modules:
            raise ValueError("UNAUTHORIZED_METATRADER5_IMPORT_IN_OFFLINE_STAGE")
    finally:
        sys.path.remove(str(root / "site"))
    stage_info = {
        "classification": "APC_DEMO_CANARY_STAGING_EXECUTION_OFF_ONLY",
        "exact_git_head": HEAD,
        "sealed_sha256": digest(inner),
        "manifest_sha256": MANIFEST_SHA,
        "control": "KILLED",
        "canary_journal": "UNUSED",
        "python_trading_enablement": False,
        "broker_access": False,
        "mt5_module_imported": False,
        "unpacked_wheel_files": unpacked,
    }
    (root / "staging_evidence.json").write_text(
        json.dumps(stage_info, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print("APC_STAGE_SEALED_SHA256=" + digest(inner))
    print("APC_STAGE_GITHUB_HEAD=" + HEAD)
    print("APC_STAGE_CONTROL=KILLED")
    print("APC_STAGE_JOURNAL=UNUSED")
    print("APC_STAGE_METATRADER5_NOT_IMPORTED=True")
    print("APC_STAGE_BROKER_ACTIONS=0")
    print("APC_STAGE_DIRECTORY=" + str(root))
    print("APC_STAGE_SUCCESS_EXECUTION_OFF_NO_TRADING")


def main() -> None:
    if sys.platform != "win32" or sys.version_info[:2] != (3, 12):
        raise RuntimeError("STAGING_REQUIRES_WINDOWS_PYTHON312")
    if os.path.normcase(sys.executable) != os.path.normcase(EXPECTED_PYTHON):
        raise RuntimeError("WRONG_PYTHON_EXECUTABLE")
    base = os.environ.get("LOCALAPPDATA")
    source = os.environ.get("APC_STAGE_ARTIFACT")
    sid = os.environ.get("APC_STAGE_OWNER_SID")
    if not base or not source or not sid:
        raise RuntimeError("STAGING_MISSING_APPROVED_PATH_OR_USER_SID")
    root = Path(base) / "XAUUSD-APC-DEMO-CANARY-S2"
    if not Path(base).is_dir() or root.parent.resolve() != Path(base).resolve():
        raise RuntimeError("UNTRUSTED_STAGING_PARENT")
    stage(Path(source), root, sid)


if __name__ == "__main__":
    main()

'@
$Canonical = $StagePython.Replace("`r`n", "`n").Replace("`r", "`n")
$Canonical = $Canonical.TrimEnd([char[]]@([char]13, [char]10)) + "`n"
$StageBytes = [Text.Encoding]::ASCII.GetBytes($Canonical)
if ([Text.Encoding]::ASCII.GetString($StageBytes) -cne $Canonical) {
    throw 'APC_STAGE_HELPER_NON_ASCII__NO_STAGE'
}
$Hash = [Security.Cryptography.SHA256]::Create()
try {
    $ActualSHA = [BitConverter]::ToString($Hash.ComputeHash($StageBytes)).Replace('-', '').ToLowerInvariant()
}
finally { $Hash.Dispose() }
Write-Output ('APC_STAGE_HELPER_SHA256=' + $ActualSHA)
if ($ActualSHA -cne $ExpectedStageScriptSHA) {
    throw 'APC_STAGE_HELPER_SHA256_MISMATCH__NOT_EXECUTED'
}
Write-Output 'APC_STAGE_HELPER_SHA_VERIFIED'
Write-Output ('APC_STAGE_ARTIFACT_PATH=' + $Artifact)
Write-Output ('APC_STAGE_PREEXISTING_MT5_PID=' + $BeforeTerminalPid)

$env:APC_STAGE_ARTIFACT = (Resolve-Path -LiteralPath $Artifact).Path
$env:APC_STAGE_OWNER_SID = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$PythonExit = 900
$PythonLines = @()
try {
    # Python -B -I - accepts stdin source; no legacy PS5.1 -c quote mangling.
    # Importing isolated wheels for SQLite initialization MUST NOT import MetaTrader5.
    $ErrorActionPreference = 'Continue'
    try {
        $PythonLines = @($Canonical | & $PythonExe -B -I - 2>&1)
        $PythonExit = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = 'Stop'
    }
}
finally {
    Remove-Item Env:APC_STAGE_ARTIFACT -ErrorAction SilentlyContinue
    Remove-Item Env:APC_STAGE_OWNER_SID -ErrorAction SilentlyContinue
}
foreach ($Line in $PythonLines) { Write-Output ([string]$Line) }
if ($PythonExit -ne 0) {
    throw ('APC_STAGE_PYTHON_FAILED__EXIT=' + $PythonExit + '__STOP_NO_RETRY')
}
$AfterTerminal = @(Get-Process -Name terminal64 -ErrorAction SilentlyContinue)
if ($AfterTerminal.Count -ne 1 -or $AfterTerminal[0].Id -ne $BeforeTerminalPid -or
    -not [string]::Equals($AfterTerminal[0].Path, $ExpectedTerminal,
                         [StringComparison]::OrdinalIgnoreCase)) {
    throw 'APC_STAGE_TERMINAL_CHANGED__FAIL_CLOSED'
}
if ($PythonLines -notcontains 'APC_STAGE_SUCCESS_EXECUTION_OFF_NO_TRADING') {
    throw 'APC_STAGE_SUCCESS_MARKER_ABSENT__FAIL_CLOSED'
}
Write-Output 'APC_STAGE_VERIFIED__KILLED__UNUSED__MT5_UNTOUCHED'
