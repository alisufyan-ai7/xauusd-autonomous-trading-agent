"""Reproducible release manifests and conservative capability scanning."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

_SCANNED_SUFFIXES = {".py", ".ps1", ".psm1", ".json", ".toml", ".yaml", ".yml"}
_FORBIDDEN = {
    "order" + "_send(": "MT5 order submission",
    "trade" + "_action_deal": "MT5 deal action",
    "trade" + "_action_pending": "MT5 pending action",
    "position" + "_close(": "position close capability",
    "order" + "_delete(": "order delete capability",
    "execution" + "_enabled=true": "execution enabled configuration",
    '"execution' + '_enabled": true': "execution enabled configuration",
}


@dataclass(frozen=True, slots=True)
class CapabilityFinding:
    path: str
    line: int
    capability: str


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    path: str
    sha256: str
    size: int


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    release_id: str
    created_at: str
    execution_enabled: bool
    broker_action_count_limit: int
    files: tuple[ManifestEntry, ...]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"


@dataclass(frozen=True, slots=True)
class RollbackPlan:
    release_id: str
    previous_release_id: str
    precondition: str = "execution-disabled target manifest verified"
    steps: tuple[str, ...] = (
        "quarantine candidate",
        "verify previous release hashes and execution-disabled settings",
        "atomically repoint active-release marker",
        "restart only through separately authorized host control",
        "reconcile health and zero broker actions",
    )


@dataclass(frozen=True, slots=True)
class ReleaseSeal:
    release_id: str
    release_root: str
    package_path: str
    package_sha256: str
    manifest_sha256: str


def scan_capabilities(root: Path, *, ignore: Iterable[Path] = ()) -> tuple[CapabilityFinding, ...]:
    ignored = {path.resolve() for path in ignore}
    findings: list[CapabilityFinding] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _SCANNED_SUFFIXES:
            continue
        if path.resolve() in ignored:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            findings.append(CapabilityFinding(str(path.relative_to(root)), 0, "non-UTF8 source"))
            continue
        for number, line in enumerate(lines, 1):
            lowered = "".join(line.lower().split())
            for needle, label in _FORBIDDEN.items():
                normalized = "".join(needle.lower().split())
                if normalized in lowered:
                    findings.append(CapabilityFinding(str(path.relative_to(root)), number, label))
    return tuple(findings)


def build_manifest(root: Path, *, release_id: str, created_at: datetime) -> ReleaseManifest:
    if not release_id.strip():
        raise ValueError("release_id must be non-empty")
    findings = scan_capabilities(root)
    if findings:
        raise ValueError(f"forbidden capabilities detected: {findings!r}")
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    entries: list[ManifestEntry] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        content = path.read_bytes()
        entries.append(
            ManifestEntry(
                str(path.relative_to(root)).replace("\\", "/"),
                hashlib.sha256(content).hexdigest(),
                len(content),
            )
        )
    timestamp = created_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return ReleaseManifest(release_id, timestamp, False, 0, tuple(entries))


def assemble_release(
    release_root: Path,
    *,
    wheel: Path,
    deployment_root: Path,
    release_id: str,
    created_at: datetime,
    source_revision: str,
) -> ReleaseSeal:
    """Create an immutable-input, execution-disabled release directory.

    The destination must not exist, preventing an earlier release from being
    overwritten or silently extended after its manifest is produced.
    """

    if release_root.exists():
        raise FileExistsError(f"release root already exists: {release_root}")
    if not wheel.is_file() or wheel.suffix != ".whl":
        raise ValueError("wheel must be an existing .whl file")
    if not deployment_root.is_dir():
        raise ValueError("deployment_root must be an existing directory")
    if len(source_revision) != 40 or any(
        char not in "0123456789abcdef" for char in source_revision
    ):
        raise ValueError("source_revision must be a lowercase 40-character Git object id")

    package_dir = release_root / "package"
    deploy_target = release_root / "deploy" / "windows"
    package_dir.mkdir(parents=True)
    deploy_target.mkdir(parents=True)
    package_target = package_dir / wheel.name
    shutil.copy2(wheel, package_target)
    for source in sorted(deployment_root.iterdir()):
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"deployment payload must contain regular files only: {source}")
        shutil.copy2(source, deploy_target / source.name)

    metadata = {
        "broker_action_count_limit": 0,
        "execution_enabled": False,
        "release_id": release_id,
        "source_revision": source_revision,
    }
    (release_root / "candidate-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = build_manifest(release_root, release_id=release_id, created_at=created_at)
    manifest_path = release_root / "release-manifest.json"
    manifest_path.write_text(manifest.to_json(), encoding="utf-8")
    package_sha256 = hashlib.sha256(package_target.read_bytes()).hexdigest()
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return ReleaseSeal(
        release_id=release_id,
        release_root=str(release_root),
        package_path=str(package_target),
        package_sha256=package_sha256,
        manifest_sha256=manifest_sha256,
    )
