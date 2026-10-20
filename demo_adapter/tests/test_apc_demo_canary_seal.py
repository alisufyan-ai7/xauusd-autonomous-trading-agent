"""Offline-only integrity tests for a single sealed canary artifact."""
from __future__ import annotations

import hashlib
import json
import runpy
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKER = ROOT / "demo_adapter/scripts/pack_apc_demo_canary.py"


def _seal() -> object:
    return runpy.run_path(str(PACKER), run_name="canary_pack_test")["seal"]


def _copy_sources(destination: Path) -> None:
    for rel in (
        "demo_adapter/scripts/apc_demo_canary_attended_operator.py",
        "demo_adapter/scripts/apc_demo_canary_readonly_preflight.py",
        "demo_adapter/scripts/apc-demo-canary-readonly-preflight.ps1",
    ):
        path = destination / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / rel).read_bytes())


def test_sealed_canary_contains_exact_manifest_and_only_allowed_sources(
    tmp_path: Path,
) -> None:
    wheel_dir = tmp_path / "wheel"
    wheel_dir.mkdir()
    fake_wheel = wheel_dir / "xauusd_demo_adapter-0.1.0.dev0-py3-none-any.whl"
    fake_wheel.write_bytes(b"SYNTHETIC_FAKE_WHEEL_NOT_REAL")
    _copy_sources(tmp_path)
    output = tmp_path / "first.zip"
    seal = _seal()
    head = "c" * 40
    record = seal(repo_root=tmp_path, wheel_dir=wheel_dir, output=output, head=head)
    assert record["archive_name"] == "first.zip"
    assert record["entry_count"] == 5
    assert record["isolated_wheel_sha256"] == hashlib.sha256(
        fake_wheel.read_bytes()
    ).hexdigest()
    assert record["archive_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    with zipfile.ZipFile(output) as archive:
        assert len(archive.namelist()) == 5
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["exact_git_head"] == head
        assert manifest["broker_action_authorized"] is False
        assert manifest["vps_staging_authorized"] is False
        assert manifest["mt5_python_execution_authorized"] is False
        assert len(manifest["source_files"]) == 4
        for item in manifest["source_files"]:
            payload = archive.read(item["path"])
            assert len(payload) == item["bytes"]
            assert hashlib.sha256(payload).hexdigest() == item["sha256"]
        assert all("login" not in name for name in archive.namelist())
    with pytest.raises(ValueError, match="ALREADY_EXISTS"):
        seal(repo_root=tmp_path, wheel_dir=wheel_dir, output=output, head=head)
    second = tmp_path / "second.zip"
    seal(repo_root=tmp_path, wheel_dir=wheel_dir, output=second, head=head)
    assert output.read_bytes() == second.read_bytes()


def test_sealing_rejects_multiple_wheels_and_invalid_sha(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "wheel"
    wheel_dir.mkdir()
    _copy_sources(tmp_path)
    seal = _seal()
    with pytest.raises(ValueError, match="ONE_ISOLATED"):
        seal(repo_root=tmp_path, wheel_dir=wheel_dir, output=tmp_path / "out.zip",
             head="a" * 40)
    first = wheel_dir / "xauusd_demo_adapter-1-py3-none-any.whl"
    first.write_bytes(b"FAKE")
    with pytest.raises(ValueError, match="EXACT_GITHUB"):
        seal(repo_root=tmp_path, wheel_dir=wheel_dir, output=tmp_path / "out.zip",
             head="not-a-valid-sha")
    (wheel_dir / "xauusd_demo_adapter-2-py3-none-any.whl").write_bytes(b"FAKE2")
    with pytest.raises(ValueError, match="ONE_ISOLATED"):
        seal(repo_root=tmp_path, wheel_dir=wheel_dir, output=tmp_path / "out.zip",
             head="a" * 40)
