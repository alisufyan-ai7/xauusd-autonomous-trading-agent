"""Offline deployment/rollback primitives for an execution-disabled release.

These functions only stage files and atomically update local marker files.  They
have no service-control, broker, network, credential, or execution capability.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .release import scan_capabilities

_RELEASE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class DeploymentValidationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DeploymentResult:
    status: str
    release_id: str
    target: str
    service_started: bool = False
    execution_enabled: bool = False
    reconciliation_required: bool = True


def _load_object(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DeploymentValidationError(f"invalid JSON artifact: {path.name}") from exc
    if not isinstance(loaded, dict):
        raise DeploymentValidationError(f"JSON artifact must be an object: {path.name}")
    return loaded


def verify_release_directory(release_root: Path) -> str:
    root = release_root.resolve()
    settings = _load_object(root / "deploy" / "windows" / "candidate.settings.json")
    required_settings = {
        "execution_enabled": False,
        "execution_mode": "DISABLED_NO_ADAPTER",
        "broker_action_count_limit": 0,
        "analyst_transport_enabled": False,
        "alert_delivery_enabled": False,
    }
    if any(settings.get(key) != value for key, value in required_settings.items()):
        raise DeploymentValidationError("candidate settings are not execution-disabled")

    metadata = _load_object(root / "candidate-metadata.json")
    if metadata.get("execution_enabled") is not False:
        raise DeploymentValidationError("candidate metadata permits execution")
    if metadata.get("broker_action_count_limit") != 0:
        raise DeploymentValidationError("candidate metadata broker action limit is not zero")
    release_id = metadata.get("release_id")
    if not isinstance(release_id, str) or _RELEASE_ID.fullmatch(release_id) is None:
        raise DeploymentValidationError("candidate release identity is invalid")

    manifest = _load_object(root / "release-manifest.json")
    if manifest.get("execution_enabled") is not False:
        raise DeploymentValidationError("release manifest permits execution")
    if manifest.get("broker_action_count_limit") != 0:
        raise DeploymentValidationError("release manifest broker action limit is not zero")
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise DeploymentValidationError("release manifest files are invalid")
    for entry in entries:
        if not isinstance(entry, dict):
            raise DeploymentValidationError("release manifest entry is invalid")
        relative = entry.get("path")
        if not isinstance(relative, str) or not relative:
            raise DeploymentValidationError("release manifest path is invalid")
        posix = PurePosixPath(relative)
        windows = PureWindowsPath(relative)
        if (
            posix.is_absolute()
            or windows.is_absolute()
            or ".." in posix.parts
            or ".." in windows.parts
        ):
            raise DeploymentValidationError("release manifest path is unsafe")
        artifact = root.joinpath(*posix.parts)
        try:
            artifact.resolve().relative_to(root)
        except (OSError, ValueError) as exc:
            raise DeploymentValidationError("release manifest path escapes root") from exc
        if not artifact.is_file():
            raise DeploymentValidationError(f"release manifest file is missing: {relative}")
        content = artifact.read_bytes()
        if entry.get("size") != len(content):
            raise DeploymentValidationError(f"release manifest size mismatch: {relative}")
        if entry.get("sha256") != hashlib.sha256(content).hexdigest():
            raise DeploymentValidationError(f"release manifest hash mismatch: {relative}")
    findings = scan_capabilities(root, ignore=(root / "release-manifest.json",))
    if findings:
        raise DeploymentValidationError(f"forbidden capability in release: {findings!r}")
    return release_id


def _write_marker_atomic(path: Path, value: str) -> None:
    temporary = path.with_name(path.name + ".next")
    temporary.write_text(value + "\n", encoding="utf-8")
    os.replace(temporary, path)


def stage_release_offline(
    release_root: Path, install_root: Path, *, release_id: str
) -> DeploymentResult:
    if _RELEASE_ID.fullmatch(release_id) is None:
        raise DeploymentValidationError("release_id is invalid")
    sealed_id = verify_release_directory(release_root)
    if sealed_id != release_id:
        raise DeploymentValidationError("release_id does not match sealed metadata")
    target = install_root / "releases" / release_id
    if target.exists():
        raise FileExistsError(f"release target already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(release_root, target)
    verify_release_directory(target)
    active = install_root / "active-release.txt"
    previous = install_root / "previous-release.txt"
    if active.is_file():
        shutil.copy2(active, previous)
    _write_marker_atomic(active, release_id)
    return DeploymentResult("STAGED", release_id, str(target))


def rollback_release_offline(install_root: Path) -> DeploymentResult:
    previous_marker = install_root / "previous-release.txt"
    if not previous_marker.is_file():
        raise DeploymentValidationError("previous release marker is missing")
    previous_id = previous_marker.read_text(encoding="utf-8").strip()
    if _RELEASE_ID.fullmatch(previous_id) is None:
        raise DeploymentValidationError("previous release identifier is invalid")
    target = install_root / "releases" / previous_id
    sealed_id = verify_release_directory(target)
    if sealed_id != previous_id:
        raise DeploymentValidationError("previous marker does not match sealed metadata")
    _write_marker_atomic(install_root / "active-release.txt", previous_id)
    return DeploymentResult("ROLLED_BACK_MARKER", previous_id, str(target))
