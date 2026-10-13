"""Command-line entry point for local validation of the shadow artifact."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .config import RuntimeConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xauusd-shadow")
    parser.add_argument("--state-directory", type=Path, required=True)
    parser.add_argument(
        "--print-preflight",
        action="store_true",
        help="Print the execution-disabled preflight and exit without starting a service.",
    )
    return parser


def preflight(config: RuntimeConfig) -> dict[str, object]:
    return {
        "symbol": config.symbol,
        "mode": config.mode.value,
        "execution_enabled": config.execution_enabled,
        "broker_sink": config.broker_sink,
        "analyst_transport": config.analyst_transport,
        "external_python_real_money_trading": config.external_python_real_money_trading,
        "broker_action_count": 0,
        "service_started": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = RuntimeConfig(state_directory=args.state_directory.resolve())
    if args.print_preflight:
        print(json.dumps(preflight(config), sort_keys=True, separators=(",", ":")))
        return 0
    raise SystemExit(
        "service start is not yet admitted; use --print-preflight until PCR-3 implementation passes"
    )


if __name__ == "__main__":
    raise SystemExit(main())
