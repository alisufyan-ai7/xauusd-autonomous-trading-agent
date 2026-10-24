"""Exact source-only, no-permission zip sealing tests."""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from scripts.seal_v11_readonly_capture import FILES, seal


def test_reproducible_offline_execution_off_capture_bundle() -> None:
    repo = Path(__file__).resolve().parents[2]
    first = seal(repo=repo, exact_head="a" * 40)
    assert first == seal(repo=repo, exact_head="a" * 40)
    with zipfile.ZipFile(io.BytesIO(first)) as z:
        names = z.namelist()
        assert len(names) == len(set(names)) == len(FILES) + 1
        manifest = json.loads(z.read("manifest.json"))
        assert manifest["exact_git_head"] == "a" * 40
        assert manifest["mt5_broker_action_authorized"] is False
        assert manifest["mt5_external_python_trading_enable_authorized"] is False
        assert manifest["vps_capture_owner_approved"] is False
        assert manifest["run_registration_filled"] is False
        assert {x["path"] for x in manifest["components"]} == set(FILES)
        for component in manifest["components"]:
            raw = z.read(component["path"])
            assert hashlib.sha256(raw).hexdigest() == component["sha256"]
            assert len(raw) == component["bytes"]
            assert b"\r" not in raw


def test_invalid_or_missing_exact_head_is_rejected() -> None:
    repo = Path(__file__).resolve().parents[2]
    for bad in ("", "not-a-sha", "0" * 39, "f" * 64):
        with pytest.raises(ValueError, match="exact final"):
            seal(repo=repo, exact_head=bad)
