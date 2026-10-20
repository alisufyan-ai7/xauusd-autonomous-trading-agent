"""Create one sealed APC-DEMO-CANARY archive (offline CI, never VPS).

Archive contains the reviewed isolated demo wheel, attended operator,
read-only Python/PS5.1 preflight, and a byte-hashed provenance manifest.
It has NO activation permit or runtime secrets and is NOT authority to deploy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

REQUIRED_SCRIPTS = (
    "demo_adapter/scripts/apc_demo_canary_attended_operator.py",
    "demo_adapter/scripts/apc_demo_canary_s2_isolated_loader.py",
    "demo_adapter/scripts/apc_demo_canary_readonly_preflight.py",
    "demo_adapter/scripts/apc-demo-canary-readonly-preflight.ps1",
)
_FIXED_ZIP_DATE = (2026, 10, 20, 0, 0, 0)


def _bytes_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def seal(
    *, repo_root: Path, wheel_dir: Path, production_wheel_dir: Path,
    output: Path, head: str,
) -> dict[str, object]:
    if re.fullmatch(r"[0-9a-f]{40}", head) is None:
        raise ValueError("EXACT_GITHUB_COMMIT_HEAD_REQUIRED")
    wheels = sorted(wheel_dir.glob("xauusd_demo_adapter-*.whl"))
    if len(wheels) != 1 or any(p.is_symlink() for p in wheels):
        raise ValueError("ONE_ISOLATED_DEMO_WHEEL_REQUIRED")
    production_wheels = sorted(
        production_wheel_dir.glob("xauusd_production_candidate-*.whl")
    )
    if len(production_wheels) != 1 or any(p.is_symlink() for p in production_wheels):
        raise ValueError("ONE_PINNED_PRODUCTION_RISK_WHEEL_REQUIRED")
    entries: dict[str, bytes] = {
        "wheel/" + wheels[0].name: wheels[0].read_bytes(),
        "wheel/" + production_wheels[0].name: production_wheels[0].read_bytes(),
    }
    for relative in REQUIRED_SCRIPTS:
        source = repo_root / relative
        if not source.is_file() or source.is_symlink():
            raise ValueError("MISSING_OR_SYMLINKED_ATTENDED_SOURCE_" + relative)
        entries["source/" + relative] = source.read_bytes()
    # These code paths must remain exact source bytes: no CRLF transformations.
    for relative in REQUIRED_SCRIPTS:
        if b"\r\n" in entries["source/" + relative]:
            raise ValueError("NONCANONICAL_CRLF_ATTENDED_SOURCE_" + relative)
    manifest = {
        "schema": "APC_DEMO_CANARY_OFFLINE_BUNDLE_V1",
        "exact_git_head": head,
        "classification": "DEMO_CANARY_ONLY__OWNER_APPROVAL_REQUIRED",
        "broker_action_authorized": False,
        "vps_staging_authorized": False,
        "mt5_python_execution_authorized": False,
        "source_files": [
            {"path": name, "bytes": len(payload), "sha256": _bytes_sha256(payload)}
            for name, payload in sorted(entries.items())
        ],
    }
    entries["manifest.json"] = (
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    if output.exists():
        raise ValueError("SEALED_ARCHIVE_ALREADY_EXISTS_NO_OVERWRITE")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in sorted(entries.items()):
            info = zipfile.ZipInfo(name, _FIXED_ZIP_DATE)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o600 << 16
            archive.writestr(info, payload)
    return {
        "exact_git_head": head,
        "archive_name": output.name,
        "archive_sha256": _bytes_sha256(output.read_bytes()),
        "isolated_wheel_sha256": _bytes_sha256(wheels[0].read_bytes()),
        "production_risk_wheel_sha256": _bytes_sha256(
            production_wheels[0].read_bytes()
        ),
        "entry_count": len(entries),
        "attended_python_source_sha256": _bytes_sha256(
            entries["source/demo_adapter/scripts/apc_demo_canary_readonly_preflight.py"]
        ),
        "attended_ps51_source_sha256": _bytes_sha256(
            entries["source/demo_adapter/scripts/apc-demo-canary-readonly-preflight.ps1"]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--production-wheel-dir", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    path = args.outdir / ("apc-demo-canary-" + args.head + ".zip")
    result = seal(
        repo_root=args.repo_root, wheel_dir=args.wheel_dir,
        production_wheel_dir=args.production_wheel_dir,
        output=path, head=args.head,
    )
    for key, value in result.items():
        print("APC_CANARY_" + key.upper() + "=" + str(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
