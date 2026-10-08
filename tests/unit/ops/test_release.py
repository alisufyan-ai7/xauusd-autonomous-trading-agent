import hashlib
import json
from datetime import UTC, datetime, timedelta, timezone, tzinfo
from pathlib import Path

import pytest

from xauusd_agent.ops.release import (
    CapabilityFinding,
    ReleaseManifest,
    ReleaseSeal,
    assemble_release,
    build_manifest,
    scan_capabilities,
)


class _IndeterminateTimezone(tzinfo):
    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)


def test_manifest_is_execution_disabled_and_hashes_files(tmp_path):
    (tmp_path / "safe.py").write_text("VALUE = 1\n", encoding="utf-8")
    manifest = build_manifest(tmp_path, release_id="rc1", created_at=datetime.now(UTC))
    assert manifest.execution_enabled is False
    assert manifest.broker_action_count_limit == 0
    assert manifest.files[0].path == "safe.py"
    assert len(manifest.files[0].sha256) == 64


def test_manifest_and_canonical_json_are_exact(tmp_path: Path) -> None:
    (tmp_path / "safe.py").write_text("VALUE = 1\n", encoding="utf-8")
    manifest = build_manifest(
        tmp_path,
        release_id="rc1",
        created_at=datetime(2026, 10, 7, tzinfo=UTC),
    )
    assert manifest == ReleaseManifest(
        release_id="rc1",
        created_at="2026-10-07T00:00:00Z",
        execution_enabled=False,
        broker_action_count_limit=0,
        files=(
            manifest.files[0].__class__(
                path="safe.py",
                sha256="e13df8c44af5dea1e412403910b99cc5a48f2ccbf68a66b3374d6ab9cef9fc65",
                size=10,
            ),
        ),
    )
    assert manifest.to_json() == (
        "{\n"
        '  "broker_action_count_limit": 0,\n'
        '  "created_at": "2026-10-07T00:00:00Z",\n'
        '  "execution_enabled": false,\n'
        '  "files": [\n'
        "    {\n"
        '      "path": "safe.py",\n'
        '      "sha256": "e13df8c44af5dea1e412403910b99cc5a48f2ccbf68a66b3374d6ab9cef9fc65",\n'
        '      "size": 10\n'
        "    }\n"
        "  ],\n"
        '  "release_id": "rc1"\n'
        "}\n"
    )


@pytest.mark.parametrize(
    ("source", "capability"),
    [
        ("client.order" + "_send(request)", "MT5 order submission"),
        ("TRADE" + "_ACTION_DEAL", "MT5 deal action"),
        ("TRADE" + "_ACTION_PENDING", "MT5 pending action"),
        ("position" + "_close(ticket)", "position close capability"),
        ("order" + "_delete(ticket)", "order delete capability"),
        ("execution" + "_enabled = true", "execution enabled configuration"),
        ('{"execution' + '_enabled": true}', "execution enabled configuration"),
    ],
)
def test_capability_scan_detects_every_forbidden_form_exactly(
    tmp_path: Path, source: str, capability: str
) -> None:
    path = tmp_path / "candidate.py"
    path.write_text("safe = 1\n" + source + "\n", encoding="utf-8")
    assert scan_capabilities(tmp_path) == (CapabilityFinding("candidate.py", 2, capability),)


def test_capability_scan_normalizes_case_and_whitespace_and_reports_all_findings(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.py").write_text(
        "client. ORDER" + "_SEND ( request )\nTRADE" + "_ACTION_DEAL\n",
        encoding="utf-8",
    )
    assert scan_capabilities(tmp_path) == (
        CapabilityFinding("a.py", 1, "MT5 order submission"),
        CapabilityFinding("a.py", 2, "MT5 deal action"),
    )


def test_capability_scan_suffix_ignore_regular_file_and_non_utf8_boundaries(
    tmp_path: Path,
) -> None:
    ignored = tmp_path / "ignored.py"
    ignored.write_text("client.order" + "_send(request)\n", encoding="utf-8")
    (tmp_path / "safe.txt").write_text("client.order" + "_send(request)\n", encoding="utf-8")
    (tmp_path / "directory.py").mkdir()
    binary = tmp_path / "binary.py"
    binary.write_bytes(b"\xff\xfe")
    assert scan_capabilities(tmp_path, ignore=(ignored,)) == (
        CapabilityFinding("binary.py", 0, "non-UTF8 source"),
    )


def test_capability_scan_ignore_skips_only_that_file_and_continues(tmp_path: Path) -> None:
    ignored = tmp_path / "a-ignored.py"
    ignored.write_text("client.order" + "_send(request)\n", encoding="utf-8")
    unsafe = tmp_path / "z-unsafe.py"
    unsafe.write_text("client.order" + "_send(request)\n", encoding="utf-8")
    assert scan_capabilities(tmp_path, ignore=(ignored,)) == (
        CapabilityFinding("z-unsafe.py", 1, "MT5 order submission"),
    )


def test_capability_scan_skips_unscanned_entry_and_continues(tmp_path: Path) -> None:
    (tmp_path / "a-decoy.txt").write_text("safe\n", encoding="utf-8")
    unsafe = tmp_path / "z-unsafe.py"
    unsafe.write_text("client.order" + "_send(request)\n", encoding="utf-8")
    assert scan_capabilities(tmp_path) == (
        CapabilityFinding("z-unsafe.py", 1, "MT5 order submission"),
    )


def test_capability_scan_reports_non_utf8_then_continues(tmp_path: Path) -> None:
    (tmp_path / "a-binary.py").write_bytes(b"\xff\xfe")
    unsafe = tmp_path / "z-unsafe.py"
    unsafe.write_text("client.order" + "_send(request)\n", encoding="utf-8")
    assert scan_capabilities(tmp_path) == (
        CapabilityFinding("a-binary.py", 0, "non-UTF8 source"),
        CapabilityFinding("z-unsafe.py", 1, "MT5 order submission"),
    )


def test_capability_scan_passes_explicit_utf8_to_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "safe.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    original = Path.read_text
    encodings: list[str | None] = []

    def observed_read_text(path: Path, *, encoding: str | None = None, errors: str | None = None):
        encodings.append(encoding)
        return original(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", observed_read_text)
    assert scan_capabilities(tmp_path) == ()
    assert encodings == ["utf-8"]


def test_forbidden_capability_blocks_manifest(tmp_path):
    (tmp_path / "unsafe.py").write_text("client.order_send(request)\n", encoding="utf-8")
    assert scan_capabilities(tmp_path)
    with pytest.raises(ValueError):
        build_manifest(tmp_path, release_id="bad", created_at=datetime.now(UTC))


def test_manifest_rejects_naive_creation_time(tmp_path):
    (tmp_path / "safe.py").write_text("VALUE = 1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        build_manifest(tmp_path, release_id="bad-clock", created_at=datetime.now())


@pytest.mark.parametrize("release_id", ["", "   "])
def test_manifest_rejects_empty_release_identity_exactly(
    tmp_path: Path, release_id: str
) -> None:
    with pytest.raises(ValueError) as exc_info:
        build_manifest(tmp_path, release_id=release_id, created_at=datetime.now(UTC))
    assert str(exc_info.value) == "release_id must be non-empty"


def test_manifest_rejects_naive_creation_time_exactly(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as exc_info:
        build_manifest(tmp_path, release_id="rc1", created_at=datetime(2026, 10, 7))
    assert str(exc_info.value) == "created_at must be timezone-aware"


def test_manifest_rejects_indeterminate_timezone(tmp_path: Path) -> None:
    created_at = datetime(2026, 10, 7, tzinfo=_IndeterminateTimezone())
    with pytest.raises(ValueError) as exc_info:
        build_manifest(tmp_path, release_id="rc1", created_at=created_at)
    assert str(exc_info.value) == "created_at must be timezone-aware"


def test_manifest_normalizes_non_utc_creation_time_to_utc(tmp_path: Path) -> None:
    timezone_plus_five = timezone(timedelta(hours=5))
    manifest = build_manifest(
        tmp_path,
        release_id="rc1",
        created_at=datetime(2026, 10, 7, 5, tzinfo=timezone_plus_five),
    )
    assert manifest.created_at == "2026-10-07T00:00:00Z"


def test_manifest_normalizes_windows_relative_separators(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "safe.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    original = Path.relative_to

    class _WindowsRelative:
        def __str__(self) -> str:
            return "nested\\safe.py"

    def windows_relative(path: Path, *other: object, **kwargs: object):
        if path == source:
            return _WindowsRelative()
        return original(path, *other, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "relative_to", windows_relative)
    manifest = build_manifest(
        tmp_path,
        release_id="rc1",
        created_at=datetime(2026, 10, 7, tzinfo=UTC),
    )
    assert manifest.files[0].path == "nested/safe.py"


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


def test_assemble_release_exact_layout_metadata_and_seal(tmp_path: Path) -> None:
    wheel = tmp_path / "candidate.whl"
    wheel.write_bytes(b"offline-wheel")
    deployment = tmp_path / "deployment"
    deployment.mkdir()
    (deployment / "z.ps1").write_text("$x = 1\n", encoding="utf-8")
    (deployment / "a.json").write_text("{}\n", encoding="utf-8")
    release_root = tmp_path / "release"
    seal = assemble_release(
        release_root,
        wheel=wheel,
        deployment_root=deployment,
        release_id="apc-0.1.0-dev0",
        created_at=datetime(2026, 10, 7, tzinfo=UTC),
        source_revision="d" * 40,
    )
    assert sorted(
        str(path.relative_to(release_root)).replace("\\", "/")
        for path in release_root.rglob("*")
        if path.is_file()
    ) == [
        "candidate-metadata.json",
        "deploy/windows/a.json",
        "deploy/windows/z.ps1",
        "package/candidate.whl",
        "release-manifest.json",
    ]
    assert (release_root / "candidate-metadata.json").read_text(encoding="utf-8") == (
        "{\n"
        '  "broker_action_count_limit": 0,\n'
        '  "execution_enabled": false,\n'
        '  "release_id": "apc-0.1.0-dev0",\n'
        '  "source_revision": "dddddddddddddddddddddddddddddddddddddddd"\n'
        "}\n"
    )
    package = release_root / "package" / "candidate.whl"
    manifest_path = release_root / "release-manifest.json"
    assert seal == ReleaseSeal(
        release_id="apc-0.1.0-dev0",
        release_root=str(release_root),
        package_path=str(package),
        package_sha256="9014ce81269e597bacae5594d3f84187455e0d99a17b6539f972efde545a6d75",
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    )


@pytest.mark.parametrize(
    "revision",
    ["d" * 39, "d" * 41, "D" * 40, "g" * 40, "X" * 40],
)
def test_assemble_release_rejects_noncanonical_source_revision(
    tmp_path: Path, revision: str
) -> None:
    wheel = tmp_path / "candidate.whl"
    wheel.write_bytes(b"offline-wheel")
    deployment = tmp_path / "deployment"
    deployment.mkdir()
    with pytest.raises(ValueError) as exc_info:
        assemble_release(
            tmp_path / "release",
            wheel=wheel,
            deployment_root=deployment,
            release_id="rc1",
            created_at=datetime(2026, 10, 7, tzinfo=UTC),
            source_revision=revision,
        )
    assert str(exc_info.value) == "source_revision must be a lowercase 40-character Git object id"


def test_assemble_release_rejects_bad_inputs_and_nonregular_deployment(
    tmp_path: Path,
) -> None:
    deployment = tmp_path / "deployment"
    deployment.mkdir()
    missing_wheel = tmp_path / "missing.whl"
    with pytest.raises(ValueError) as missing_error:
        assemble_release(
            tmp_path / "release-missing",
            wheel=missing_wheel,
            deployment_root=deployment,
            release_id="rc1",
            created_at=datetime(2026, 10, 7, tzinfo=UTC),
            source_revision="d" * 40,
        )
    assert str(missing_error.value) == "wheel must be an existing .whl file"

    bad_suffix = tmp_path / "candidate.zip"
    bad_suffix.write_bytes(b"offline-wheel")
    with pytest.raises(ValueError) as suffix_error:
        assemble_release(
            tmp_path / "release-suffix",
            wheel=bad_suffix,
            deployment_root=deployment,
            release_id="rc1",
            created_at=datetime(2026, 10, 7, tzinfo=UTC),
            source_revision="d" * 40,
        )
    assert str(suffix_error.value) == "wheel must be an existing .whl file"

    wheel = tmp_path / "candidate.whl"
    wheel.write_bytes(b"offline-wheel")
    with pytest.raises(ValueError) as deployment_error:
        assemble_release(
            tmp_path / "release-deployment",
            wheel=wheel,
            deployment_root=tmp_path / "absent",
            release_id="rc1",
            created_at=datetime(2026, 10, 7, tzinfo=UTC),
            source_revision="d" * 40,
        )
    assert str(deployment_error.value) == "deployment_root must be an existing directory"

    nested = deployment / "nested"
    nested.mkdir()
    with pytest.raises(ValueError) as nested_error:
        assemble_release(
            tmp_path / "release-nested",
            wheel=wheel,
            deployment_root=deployment,
            release_id="rc1",
            created_at=datetime(2026, 10, 7, tzinfo=UTC),
            source_revision="d" * 40,
        )
    assert str(nested_error.value).endswith(
        "deployment payload must contain regular files only: " + str(nested)
    )


def test_assemble_release_refuses_to_overwrite_existing_root(tmp_path):
    release_root = tmp_path / "existing"
    release_root.mkdir()
    wheel = tmp_path / "candidate.whl"
    wheel.write_bytes(b"offline-wheel")
    deployment = tmp_path / "deployment"
    deployment.mkdir()
    with pytest.raises(FileExistsError) as exc_info:
        assemble_release(
            release_root,
            wheel=wheel,
            deployment_root=deployment,
            release_id="apc-0.1.0-dev0",
            created_at=datetime(2026, 10, 7, tzinfo=UTC),
            source_revision="d" * 40,
        )
    assert str(exc_info.value) == f"release root already exists: {release_root}"
