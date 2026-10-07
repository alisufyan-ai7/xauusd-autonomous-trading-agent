import json
from datetime import UTC, datetime

import pytest

from xauusd_agent.ops.release import assemble_release, build_manifest, scan_capabilities


def test_manifest_is_execution_disabled_and_hashes_files(tmp_path):
    (tmp_path / "safe.py").write_text("VALUE = 1\n", encoding="utf-8")
    manifest = build_manifest(tmp_path, release_id="rc1", created_at=datetime.now(UTC))
    assert manifest.execution_enabled is False
    assert manifest.broker_action_count_limit == 0
    assert manifest.files[0].path == "safe.py"
    assert len(manifest.files[0].sha256) == 64


def test_forbidden_capability_blocks_manifest(tmp_path):
    (tmp_path / "unsafe.py").write_text("client.order_send(request)\n", encoding="utf-8")
    assert scan_capabilities(tmp_path)
    with pytest.raises(ValueError):
        build_manifest(tmp_path, release_id="bad", created_at=datetime.now(UTC))


def test_manifest_rejects_naive_creation_time(tmp_path):
    (tmp_path / "safe.py").write_text("VALUE = 1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        build_manifest(tmp_path, release_id="bad-clock", created_at=datetime.now())


def test_assemble_release_seals_wheel_and_execution_disabled_payload(tmp_path):
    wheel = tmp_path / "candidate.whl"
    wheel.write_bytes(b"offline-wheel")
    deployment = tmp_path / "deployment"
    deployment.mkdir()
    (deployment / "candidate.settings.json").write_text(
        '{"execution_enabled":false,"broker_action_count_limit":0}\n', encoding="utf-8"
    )
    release_root = tmp_path / "release"

    seal = assemble_release(
        release_root,
        wheel=wheel,
        deployment_root=deployment,
        release_id="apc-0.1.0-dev0",
        created_at=datetime(2026, 10, 7, tzinfo=UTC),
        source_revision="d" * 40,
    )

    manifest = json.loads((release_root / "release-manifest.json").read_text())
    metadata = json.loads((release_root / "candidate-metadata.json").read_text())
    assert len(seal.package_sha256) == 64
    assert len(seal.manifest_sha256) == 64
    assert manifest["execution_enabled"] is False
    assert manifest["broker_action_count_limit"] == 0
    assert metadata["execution_enabled"] is False
    assert metadata["broker_action_count_limit"] == 0
    assert all(item["path"] != "release-manifest.json" for item in manifest["files"])


def test_assemble_release_refuses_to_overwrite_existing_root(tmp_path):
    release_root = tmp_path / "existing"
    release_root.mkdir()
    wheel = tmp_path / "candidate.whl"
    wheel.write_bytes(b"offline-wheel")
    deployment = tmp_path / "deployment"
    deployment.mkdir()
    with pytest.raises(FileExistsError):
        assemble_release(
            release_root,
            wheel=wheel,
            deployment_root=deployment,
            release_id="apc-0.1.0-dev0",
            created_at=datetime(2026, 10, 7, tzinfo=UTC),
            source_revision="d" * 40,
        )
