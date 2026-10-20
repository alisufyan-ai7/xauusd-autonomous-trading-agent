"""Offline-audited S2 isolated wheel loader; no MT5 access in verify mode.

An explicit future APC is required before use of entry/close; the hardcoded
confirmation string is defense-in-depth only, not a substitute for owner consent.
All artifacts, including extracted site files, are verified before operator import.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import runpy
import sqlite3
import sys
import zipfile
from pathlib import Path

STAGE_NAME = "XAUUSD-APC-DEMO-CANARY-S2"
OPERATOR_PATH = "source/demo_adapter/scripts/apc_demo_canary_attended_operator.py"
OWNER_TOKEN = "APC-DEMO-CANARY-ONE-ENTRY-ONE-CLOSE"


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def verify_stage(
    root: Path, *, expected_head: str, expected_archive_sha256: str,
) -> tuple[Path, Path]:
    if (root.name != STAGE_NAME or not root.is_dir() or root.is_symlink()
            or re.fullmatch(r"[0-9a-f]{40}", expected_head) is None
            or re.fullmatch(r"[0-9a-f]{64}", expected_archive_sha256) is None):
        raise RuntimeError("S2_STAGE_OR_PINS_UNTRUSTED")
    actual_zip = root / "sealed.zip"
    if actual_zip.is_symlink():
        raise RuntimeError("S2_STAGE_ZIP_SYMLINK")
    archive_bytes = actual_zip.read_bytes()
    if sha256(archive_bytes) != expected_archive_sha256:
        raise RuntimeError("S2_ARCHIVE_PIN_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or "manifest.json" not in names:
            raise RuntimeError("S2_ARCHIVE_DUPLICATE_OR_MISSING_MANIFEST")
        manifest_bytes = z.read("manifest.json")
        if sha256((root / "manifest.json").read_bytes()) != sha256(manifest_bytes):
            raise RuntimeError("S2_MANIFEST_DISK_MISMATCH")
        manifest = json.loads(manifest_bytes)
        if (manifest.get("exact_git_head") != expected_head
                or manifest.get("classification") != "DEMO_CANARY_ONLY__OWNER_APPROVAL_REQUIRED"
                or manifest.get("broker_action_authorized") is not False):
            raise RuntimeError("S2_MANIFEST_IDENTITY_OR_AUTHORITY_MISMATCH")
        files = manifest.get("source_files")
        if not isinstance(files, list) or len(files) < 6:
            raise RuntimeError("S2_MANIFEST_FILE_SET_INVALID")
        declared = {x["path"]: x for x in files}
        if len(declared) != len(files) or set(names) != set(declared) | {"manifest.json"}:
            raise RuntimeError("S2_MANIFEST_ENTRY_SET_MISMATCH")
        if OPERATOR_PATH not in declared:
            raise RuntimeError("S2_OPERATOR_MISSING")
        site = root / "site"
        if site.is_symlink() or not site.is_dir():
            raise RuntimeError("S2_SITE_MISSING")
        expected_site_files: set[str] = set()
        for name, meta in declared.items():
            path = Path(name)
            if (path.is_absolute() or ".." in path.parts or
                    not (name.startswith("wheel/") or name.startswith("source/"))):
                raise RuntimeError("S2_UNSAFE_ARCHIVE_PATH")
            data = z.read(name)
            if sha256(data) != meta["sha256"] or len(data) != meta["bytes"]:
                raise RuntimeError("S2_COMPONENT_MANIFEST_MISMATCH")
            folder = root / ("wheels" if name.startswith("wheel/") else "sources")
            target = folder / path.name
            if folder.is_symlink() or target.is_symlink() or target.read_bytes() != data:
                raise RuntimeError("S2_COMPONENT_DISK_MISMATCH")
            if name.startswith("wheel/"):
                with zipfile.ZipFile(io.BytesIO(data)) as w:
                    for member in w.namelist():
                        part = Path(member)
                        if part.is_absolute() or ".." in part.parts:
                            raise RuntimeError("S2_UNSAFE_WHEEL_MEMBER")
                        disk = site / part
                        if member in expected_site_files:
                            raise RuntimeError("S2_DUPLICATE_WHEEL_MEMBER")
                        expected_site_files.add(member)
                        if (disk.is_symlink() or any(parent.is_symlink() for parent in
                                disk.parents if parent != site and site in parent.parents)
                                or not disk.is_file()):
                            raise RuntimeError("S2_SITE_MEMBER_MISSING")
                        if disk.read_bytes() != w.read(member):
                            raise RuntimeError("S2_SITE_MEMBER_TAMPERED")
        observed_site_files = {
            p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file()
        }
        if observed_site_files != expected_site_files:
            raise RuntimeError("S2_UNLISTED_OR_MISSING_SITE_FILE")
    ctrl = root / "control.sqlite3"
    journal = root / "canary.sqlite3"
    if ctrl.is_symlink() or journal.is_symlink():
        raise RuntimeError("S2_CONTROL_SYMLINK")
    return site, root / "sources" / Path(OPERATOR_PATH).name


def _stage_state(root: Path) -> tuple[str, str]:
    control = root / "control.sqlite3"
    journal = root / "canary.sqlite3"
    with sqlite3.connect(f"file:{control.as_posix()}?mode=ro", uri=True) as db:
        rows = db.execute("SELECT state FROM demo_control WHERE singleton_id=1").fetchall()
        if len(rows) != 1:
            raise RuntimeError("S2_CONTROL_ROW_UNKNOWN")
        state = str(rows[0][0])
    with sqlite3.connect(f"file:{journal.as_posix()}?mode=ro", uri=True) as db:
        rows = db.execute("SELECT stage FROM canary WHERE id=1").fetchall()
        if len(rows) > 1:
            raise RuntimeError("S2_JOURNAL_ROW_UNKNOWN")
        status = "UNUSED" if not rows else str(rows[0][0])
    return state, status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("verify", "entry", "close"), required=True)
    parser.add_argument("--expected-git-head", required=True)
    parser.add_argument("--expected-archive-sha256", required=True)
    parser.add_argument("--owner-apc", default="")
    parser.add_argument("--activation-id", default="")
    parser.add_argument("--expires-utc", default="")
    parser.add_argument("--side", choices=("BUY", "SELL"))
    parser.add_argument("--stop")
    parser.add_argument("--price-limit")
    args = parser.parse_args(argv)
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise RuntimeError("S2_PYTHON_REQUIRES_B_I")
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise RuntimeError("S2_LOCALAPPDATA_MISSING")
    if args.mode != "verify" and args.owner_apc != OWNER_TOKEN:
        raise RuntimeError("S2_EXPLICIT_NEW_OWNER_APC_REQUIRED")
    root = Path(base) / STAGE_NAME
    site, operator = verify_stage(
        root, expected_head=args.expected_git_head,
        expected_archive_sha256=args.expected_archive_sha256,
    )
    state, status = _stage_state(root)
    if args.mode in ("verify", "entry"):
        if (state, status) != ("KILLED", "UNUSED"):
            raise RuntimeError("S2_ENTRY_NOT_KILLED_UNUSED")
    elif (state, status) != ("ACTIVE", "OPEN"):
        raise RuntimeError("S2_CLOSE_NOT_EXACT_KNOWN_ACTIVE_OPEN")
    if args.mode == "verify":
        if "MetaTrader5" in sys.modules:
            raise RuntimeError("S2_VERIFY_MUST_NOT_IMPORT_MT5")
        print("S2_VERIFY_ONLY_KILLED_UNUSED_NO_MT5")
        return 0
    if not args.activation_id or not args.expires_utc:
        raise RuntimeError("S2_OWNER_ACTIVATION_PARAMETERS_REQUIRED")
    if args.mode == "entry":
        if args.side is None or args.stop is None or args.price_limit is None:
            raise RuntimeError("S2_EXACT_OWNER_SIDE_STOP_REQUIRED")
    elif args.side is not None or args.stop is not None or args.price_limit is not None:
        raise RuntimeError("S2_CLOSE_CANNOT_CREATE_NEW_EXPOSURE")
    params = [
        "--mode", args.mode, "--owner-apc", OWNER_TOKEN,
        "--activation-id", args.activation_id,
        "--expires-utc", args.expires_utc,
    ]
    if args.mode == "entry":
        params.extend(["--side", args.side or "", "--stop", args.stop or "",
                       "--price-limit", args.price_limit or ""])
    sys.path.insert(0, str(site))
    try:
        script = runpy.run_path(str(operator), run_name="apc_s2_owner_gated")
        return int(script["main"](params))
    finally:
        sys.path.remove(str(site))


if __name__ == "__main__":
    raise SystemExit(main())
