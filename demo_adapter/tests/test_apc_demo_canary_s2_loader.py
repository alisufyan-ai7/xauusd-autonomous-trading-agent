"""Synthetic S2 sealed-stage loader tests; never import or attach MetaTrader5."""
from __future__ import annotations

import hashlib
import io
import json
import os
import runpy
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LOADER = ROOT / "scripts/apc_demo_canary_s2_isolated_loader.py"
OPERATOR = ROOT / "scripts/apc_demo_canary_attended_operator.py"
PREFLIGHT = ROOT / "scripts/apc_demo_canary_readonly_preflight.py"
PREFLIGHT_PS = ROOT / "scripts/apc-demo-canary-readonly-preflight.ps1"


def _zip(items: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, contents in sorted(items.items()):
            archive.writestr(path, contents)
    return buffer.getvalue()


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def synthetic_stage(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "XAUUSD-APC-DEMO-CANARY-S2"
    (root / "wheels").mkdir(parents=True)
    (root / "sources").mkdir()
    (root / "site").mkdir()
    wheel_a = _zip({"xauusd_demo/__init__.py": b"DEMO_CANARY=1\n"})
    wheel_b = _zip({"xauusd_agent/__init__.py": b"RISK_ENGINE=1\n"})
    files = {
        "wheel/xauusd_demo_adapter-0.1.0.dev0-py3-none-any.whl": wheel_a,
        "wheel/xauusd_production_candidate-0.1.0.dev0-py3-none-any.whl": wheel_b,
        "source/demo_adapter/scripts/apc_demo_canary_attended_operator.py": (
            OPERATOR.read_bytes()
        ),
        "source/demo_adapter/scripts/apc_demo_canary_readonly_preflight.py": (
            PREFLIGHT.read_bytes()
        ),
        "source/demo_adapter/scripts/apc-demo-canary-readonly-preflight.ps1": (
            PREFLIGHT_PS.read_bytes()
        ),
        "source/demo_adapter/scripts/apc_demo_canary_s2_isolated_loader.py": (
            LOADER.read_bytes()
        ),
    }
    for key, data in files.items():
        destination = root / ("wheels" if key.startswith("wheel/") else "sources")
        (destination / key.split("/")[-1]).write_bytes(data)
    for name, data in {**{
        "xauusd_demo/__init__.py": b"DEMO_CANARY=1\n",
        "xauusd_agent/__init__.py": b"RISK_ENGINE=1\n",
    }}.items():
        path = root / "site" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    head = "a" * 40
    manifest = {
        "exact_git_head": head,
        "classification": "DEMO_CANARY_ONLY__OWNER_APPROVAL_REQUIRED",
        "broker_action_authorized": False,
        "source_files": [
            {"path": name, "sha256": _sha(data), "bytes": len(data)}
            for name, data in sorted(files.items())
        ],
    }
    manifest_bytes = (
        json.dumps(manifest, sort_keys=True) + "\n"
    ).encode()
    (root / "manifest.json").write_bytes(manifest_bytes)
    payload = _zip({**files, "manifest.json": manifest_bytes})
    (root / "sealed.zip").write_bytes(payload)
    with sqlite3.connect(root / "control.sqlite3") as db:
        db.execute("CREATE TABLE demo_control (singleton_id INT, state TEXT)")
        db.execute("INSERT INTO demo_control VALUES (1,'KILLED')")
    with sqlite3.connect(root / "canary.sqlite3") as db:
        db.execute("CREATE TABLE canary (id INT,stage TEXT)")
    return root, head, _sha(payload)


def test_s2_stage_verify_all_hashes_and_exact_control(tmp_path: Path) -> None:
    root, head, artifact_sha = synthetic_stage(tmp_path)
    funcs = runpy.run_path(str(LOADER), run_name="synthetic_only")
    site, operator = funcs["verify_stage"](
        root, expected_head=head, expected_archive_sha256=artifact_sha
    )
    assert site == root / "site"
    assert operator.read_bytes() == OPERATOR.read_bytes()
    assert funcs["_stage_state"](root) == ("KILLED", "UNUSED")


def test_s2_extra_site_file_and_tampered_wheel_are_denied(tmp_path: Path) -> None:
    root, head, sha = synthetic_stage(tmp_path)
    funcs = runpy.run_path(str(LOADER), run_name="synthetic_only")
    verify = funcs["verify_stage"]
    (root / "site" / "evil.py").write_text("UNLISTED=True\n")
    with pytest.raises(RuntimeError, match="S2_UNLISTED"):
        verify(root, expected_head=head, expected_archive_sha256=sha)
    (root / "site" / "evil.py").unlink()
    (root / "site/xauusd_demo/__init__.py").write_text("MODIFIED=True\n")
    with pytest.raises(RuntimeError, match="S2_SITE_MEMBER_TAMPERED"):
        verify(root, expected_head=head, expected_archive_sha256=sha)


def test_s2_sqlite_gate_requires_killed_unused_then_active_open(tmp_path: Path) -> None:
    root, _, _ = synthetic_stage(tmp_path)
    funcs = runpy.run_path(str(LOADER), run_name="synthetic_only")
    assert funcs["_stage_state"](root) == ("KILLED", "UNUSED")
    with sqlite3.connect(root / "control.sqlite3") as db:
        db.execute("UPDATE demo_control SET state='ACTIVE'")
    with sqlite3.connect(root / "canary.sqlite3") as db:
        db.execute("INSERT INTO canary VALUES (1,'OPEN')")
    assert funcs["_stage_state"](root) == ("ACTIVE", "OPEN")


def test_s2_native_process_verify_no_mt5_and_denied_entry(tmp_path: Path) -> None:
    root, head, artifact_sha = synthetic_stage(tmp_path)
    env = {**os.environ, "LOCALAPPDATA": str(tmp_path)}
    common = [
        str(LOADER), "--expected-git-head", head,
        "--expected-archive-sha256", artifact_sha,
    ]
    done = subprocess.run(  # noqa: S603 (synthetic stage only)
        [sys.executable, "-B", "-I", *common, "--mode", "verify"],
        capture_output=True, text=True, check=False, timeout=30, env=env,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "S2_VERIFY_ONLY_KILLED_UNUSED_NO_MT5" in done.stdout
    denied = subprocess.run(  # noqa: S603 (explicitly unauthorized)
        [sys.executable, "-B", "-I", *common, "--mode", "entry"],
        capture_output=True, text=True, check=False, timeout=30, env=env,
    )
    assert denied.returncode != 0
    assert "S2_EXPLICIT_NEW_OWNER_APC_REQUIRED" in denied.stderr
    assert root.is_dir()
