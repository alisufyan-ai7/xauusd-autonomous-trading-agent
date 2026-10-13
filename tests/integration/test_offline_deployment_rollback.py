from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from xauusd_agent.ops.deployment import (
    DeploymentValidationError,
    rollback_release_offline,
    stage_release_offline,
    verify_release_directory,
)
from xauusd_agent.ops.release import assemble_release


def _release(tmp_path: Path, release_id: str) -> Path:
    wheel = tmp_path / f"{release_id}.whl"
    wheel.write_bytes(("wheel-" + release_id).encode("ascii"))
    deployment = tmp_path / f"deploy-{release_id}"
    deployment.mkdir()
    (deployment / "candidate.settings.json").write_text(
        json.dumps(
            {
                "execution_enabled": False,
                "execution_mode": "DISABLED_NO_ADAPTER",
                "broker_action_count_limit": 0,
                "analyst_transport_enabled": False,
                "alert_delivery_enabled": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    for name in (
        "Install-ExecutionDisabledCandidate.ps1",
        "Invoke-ExecutionDisabledRollback.ps1",
        "Test-ExecutionDisabledCandidate.ps1",
    ):
        (deployment / name).write_text("# offline test payload\n", encoding="utf-8")
    root = tmp_path / f"release-{release_id}"
    assemble_release(
        root,
        wheel=wheel,
        deployment_root=deployment,
        release_id=release_id,
        created_at=datetime(2026, 10, 8, tzinfo=UTC),
        source_revision="d" * 40,
    )
    return root


def test_offline_stage_two_releases_and_rollback_marker_without_service_action(
    tmp_path: Path,
) -> None:
    install = tmp_path / "install"
    first_root = _release(tmp_path, "rc1")
    second_root = _release(tmp_path, "rc2")

    first = stage_release_offline(first_root, install, release_id="rc1")
    second = stage_release_offline(second_root, install, release_id="rc2")
    assert first.service_started is False
    assert second.execution_enabled is False
    assert (install / "active-release.txt").read_text(encoding="utf-8") == "rc2\n"
    assert (install / "previous-release.txt").read_text(encoding="utf-8") == "rc1\n"

    rolled_back = rollback_release_offline(install)
    assert rolled_back.status == "ROLLED_BACK_MARKER"
    assert rolled_back.service_started is False
    assert rolled_back.reconciliation_required is True
    assert (install / "active-release.txt").read_text(encoding="utf-8") == "rc1\n"


def test_offline_stage_refuses_tampered_artifact_before_install(tmp_path: Path) -> None:
    release = _release(tmp_path, "rc1")
    package = next((release / "package").glob("*.whl"))
    package.write_bytes(b"tamperxxx")
    with pytest.raises(DeploymentValidationError, match="hash mismatch"):
        stage_release_offline(release, tmp_path / "install", release_id="rc1")


def test_offline_rollback_refuses_tampered_previous_release(tmp_path: Path) -> None:
    install = tmp_path / "install"
    first_root = _release(tmp_path, "rc1")
    second_root = _release(tmp_path, "rc2")
    stage_release_offline(first_root, install, release_id="rc1")
    stage_release_offline(second_root, install, release_id="rc2")
    package = next((install / "releases" / "rc1" / "package").glob("*.whl"))
    package.write_bytes(b"tamperxxx")
    with pytest.raises(DeploymentValidationError, match="hash mismatch"):
        rollback_release_offline(install)
    assert (install / "active-release.txt").read_text(encoding="utf-8") == "rc2\n"


def test_offline_verifier_rejects_unsafe_manifest_path(tmp_path: Path) -> None:
    release = _release(tmp_path, "rc1")
    manifest = release / "release-manifest.json"
    text = manifest.read_text(encoding="utf-8").replace(
        '"path": "candidate-metadata.json"',
        '"path": "../candidate-metadata.json"',
    )
    manifest.write_text(text, encoding="utf-8")
    with pytest.raises(DeploymentValidationError, match="path is unsafe"):
        verify_release_directory(release)
