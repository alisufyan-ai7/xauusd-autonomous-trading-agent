"""Future owner-approved *execution-off* stage of the sealed v1.1 source ZIP.

This pure-stdlib script has NO MetaTrader5 import and never launches the
collector, broker terminal, or scheduler. One new private directory, no retry.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path

COMPONENTS = frozenset({
    "demo_adapter/scripts/v11_readonly_collector.py",
    "demo_adapter/scripts/v11_quote_coverage.py",
    "demo_adapter/scripts/v11_windows_readonly_host.py",
    "demo_adapter/scripts/v11_policy_a_source_bridge.py",
    "demo_adapter/scripts/v11_windows_readonly_capture.ps1",
})
STAGE = "XAUUSD-DEMO-V11-READONLY"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def stage(
    outer: bytes, *,
    expected_outer_sha256: str,
    expected_inner_sha256: str,
    expected_head: str,
    target: Path,
) -> dict[str, object]:
    if (not re.fullmatch(r"[0-9a-f]{40}", expected_head)
            or any(not re.fullmatch(r"[0-9a-f]{64}", x)
                   for x in (expected_outer_sha256, expected_inner_sha256))):
        raise ValueError("untrusted exact source pins")
    if target.exists() or target.is_symlink() or target.name != STAGE:
        raise ValueError("stage exists or unexpected isolated root; no retry")
    if sha(outer) != expected_outer_sha256:
        raise ValueError("outer artifact bytes differ")
    with zipfile.ZipFile(io.BytesIO(outer)) as a:
        entries = [x for x in a.infolist() if not x.is_dir()]
        if len(entries) != 1 or len(a.infolist()) != 1:
            raise ValueError("outer artifact contains unexpected payloads")
        inner = a.read(entries[0])
    if sha(inner) != expected_inner_sha256:
        raise ValueError("inner source bundle bytes differ")
    with zipfile.ZipFile(io.BytesIO(inner)) as a:
        names = a.namelist()
        if len(names) != len(set(names)) or set(names) != COMPONENTS | {"manifest.json"}:
            raise ValueError("unexpected archive member set")
        if any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise ValueError("path traversal in bundle")
        manifest_bytes = a.read("manifest.json")
        manifest = json.loads(manifest_bytes)
        if (manifest.get("schema") != "DEMO_V11_READ_ONLY_EXECUTION_OFF_BUNDLE_V1"
                or manifest.get("exact_git_head") != expected_head
                or manifest.get("mt5_broker_action_authorized") is not False
                or manifest.get("mt5_external_python_trading_enable_authorized") is not False
                or manifest.get("vps_capture_owner_approved") is not False
                or manifest.get("run_registration_filled") is not False):
            raise ValueError("bundle authority/identity mismatch")
        details = manifest.get("components")
        if not isinstance(details, list) or {x["path"] for x in details} != COMPONENTS:
            raise ValueError("manifest component set mismatch")
        checked: dict[str, bytes] = {}
        for entry in details:
            name = entry["path"]
            data = a.read(name)
            if (len(data) != entry["bytes"] or sha(data) != entry["sha256"]
                    or b"\r" in data):
                raise ValueError("component hash/size or LF mismatch")
            checked[Path(name).name] = data
        if len(checked) != len(COMPONENTS):
            raise ValueError("duplicate stage file base name")
    # No target files or directories created until ALL hashes pass.
    target.mkdir(mode=0o700, parents=False, exist_ok=False)
    scripts = target / "scripts"
    scripts.mkdir(mode=0o700)
    for name, data in checked.items():
        with (scripts / name).open("xb") as out:
            out.write(data)
        if (scripts / name).read_bytes() != data:
            raise ValueError("written component verification failed")
    with (target / "source-manifest.json").open("xb") as out:
        out.write(manifest_bytes)
    # No schedule, broker API, connection, activation, or capture capability.
    (target / "EXECUTION_OFF__NO_CAPTURE_AUTHORIZED").write_text(
        "NO_CAPTURE_NO_BROKER_ACTIONS_NO_REAL_MONEY\n", encoding="ascii"
    )
    report: dict[str, object] = {
        "status": "V11_EXECUTION_OFF_STAGED_NO_CAPTURE",
        "original_source_head": expected_head,
        "source_zip_sha256": expected_inner_sha256,
        "manifest_sha256": sha(manifest_bytes),
        "component_count": len(checked),
        "broker_actions": 0,
        "mt5_imported": "MetaTrader5" in sys.modules,
        "capture_authorized": False,
    }
    if report["mt5_imported"]:
        raise ValueError("MetaTrader5 unexpectedly imported during stage")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outer-zip", type=Path, required=True)
    parser.add_argument("--outer-sha256", required=True)
    parser.add_argument("--inner-sha256", required=True)
    parser.add_argument("--source-head", required=True)
    args = parser.parse_args()
    if os.name != "nt" or sys.version_info[:2] != (3, 12):
        raise ValueError("native Windows Python 3.12 required")
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise ValueError("Python -B -I required")
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        raise ValueError("LOCALAPPDATA not set")
    target = Path(root) / STAGE
    report = stage(
        args.outer_zip.read_bytes(),
        expected_outer_sha256=args.outer_sha256,
        expected_inner_sha256=args.inner_sha256,
        expected_head=args.source_head,
        target=target,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
