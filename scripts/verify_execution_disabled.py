"""Fail the build if the production-candidate source exposes order capability."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable
from pathlib import Path

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "order_send",
        "order_check",
        "position_close",
        "positions_close",
        "close_position",
        "modify_order",
        "cancel_order",
        "submit_order",
        "send_order",
        "place_order",
        "enable_live_trading",
    }
)


class CapabilityViolation(RuntimeError):
    pass


def python_files(root: Path) -> Iterable[Path]:
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def scan_file(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        identifier: str | None = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            identifier = node.name
        elif isinstance(node, ast.Name):
            identifier = node.id
        elif isinstance(node, ast.Attribute):
            identifier = node.attr
        if identifier is not None and identifier.casefold() in FORBIDDEN_IDENTIFIERS:
            violations.append(f"{path}:{getattr(node, 'lineno', 0)}:{identifier}")
    return violations


def verify(root: Path) -> None:
    violations = [item for path in python_files(root) for item in scan_file(path)]
    if violations:
        raise CapabilityViolation("forbidden order capability:\n" + "\n".join(violations))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path("src/xauusd_agent"))
    args = parser.parse_args()
    verify(args.root)
    print("PASS_EXECUTION_DISABLED_CAPABILITY_SCAN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
