"""Synthetic one-shot execution-OFF staging; never touch MT5 or VPS."""
from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

from scripts.seal_v11_readonly_capture import seal
from scripts.v11_readonly_executionoff_stage import STAGE, stage

ROOT = Path(__file__).resolve().parents[2]
HEAD = "b" * 40


def outer_artifact(inner: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as a:
        a.writestr("v11-readonly-source-" + HEAD + ".zip", inner)
    return buf.getvalue()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _stage(tmp_path: Path, outer: bytes, inner: bytes) -> dict[str, object]:
    return stage(
        outer,
        expected_outer_sha256=digest(outer),
        expected_inner_sha256=digest(inner),
        expected_head=HEAD,
        target=tmp_path / STAGE,
    )


def test_execution_off_only_correct_exact_source_and_no_second_stage(
    tmp_path: Path,
) -> None:
    inner = seal(repo=ROOT, exact_head=HEAD)
    outer = outer_artifact(inner)
    report = _stage(tmp_path, outer, inner)
    assert report["status"] == "V11_EXECUTION_OFF_STAGED_NO_CAPTURE"
    assert report["broker_actions"] == 0
    assert report["mt5_imported"] is False
    assert report["capture_authorized"] is False
    assert (tmp_path / STAGE / "EXECUTION_OFF__NO_CAPTURE_AUTHORIZED").is_file()
    assert (tmp_path / STAGE / "scripts" / "v11_windows_readonly_capture.ps1").is_file()
    assert "MetaTrader5" not in sys.modules
    with pytest.raises(ValueError, match="stage exists"):
        _stage(tmp_path, outer, inner)


def test_wrong_outer_inner_and_missing_zip_fail_before_target_creation(
    tmp_path: Path,
) -> None:
    inner = seal(repo=ROOT, exact_head=HEAD)
    outer = outer_artifact(inner)
    with pytest.raises(ValueError, match="outer artifact"):
        stage(
            outer,
            expected_outer_sha256="0" * 64,
            expected_inner_sha256=digest(inner),
            expected_head=HEAD,
            target=tmp_path / STAGE,
        )
    assert not (tmp_path / STAGE).exists()
    with pytest.raises(ValueError, match="inner source"):
        stage(
            outer,
            expected_outer_sha256=digest(outer),
            expected_inner_sha256="0" * 64,
            expected_head=HEAD,
            target=tmp_path / STAGE,
        )
    assert not (tmp_path / STAGE).exists()


def test_mismatched_manifest_authority_denied_without_creating_stage(
    tmp_path: Path,
) -> None:
    inner = seal(repo=ROOT, exact_head=HEAD)
    with zipfile.ZipFile(io.BytesIO(inner)) as a:
        items = {name: a.read(name) for name in a.namelist()}
    manifest = json.loads(items["manifest.json"])
    manifest["mt5_broker_action_authorized"] = True
    items["manifest.json"] = json.dumps(manifest).encode()
    with io.BytesIO() as buf:
        with zipfile.ZipFile(buf, "w") as a:
            for name, data in items.items():
                a.writestr(name, data)
        altered = buf.getvalue()
    with pytest.raises(ValueError, match="authority"):
        _stage(tmp_path, outer_artifact(altered), altered)
    assert not (tmp_path / STAGE).exists()
