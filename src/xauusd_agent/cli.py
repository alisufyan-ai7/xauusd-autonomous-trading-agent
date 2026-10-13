"""Command-line entry point for the execution-disabled shadow artifact."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .config import RuntimeConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xauusd-shadow")
    parser.add_argument("--state-directory", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--print-preflight",
        action="store_true",
        help="Print the static execution-disabled preflight and exit.",
    )
    mode.add_argument(
        "--broker-preflight",
        action="store_true",
        help="Verify guarded live MT5 access and zero exposure, then exit.",
    )
    mode.add_argument(
        "--run-service",
        action="store_true",
        help="Run continuous guarded read-only shadow service.",
    )
    mode.add_argument(
        "--once",
        action="store_true",
        help="Run exactly one guarded read-only shadow cycle and exit.",
    )
    parser.add_argument("--interval-seconds", type=int, default=15)
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

    from .host import broker_preflight, run_shadow_host

    if args.broker_preflight:
        print(json.dumps(broker_preflight(), sort_keys=True, separators=(",", ":")))
        return 0
    return run_shadow_host(
        config.state_directory,
        interval_seconds=args.interval_seconds,
        once=bool(args.once),
    )


if __name__ == "__main__":
    raise SystemExit(main())
