"""R3 extension of the sealed Dukascopy corpus through 2026-08-23."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import argparse

import acquire_dukascopy as base


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("command", choices=("acquire", "derive"))
    args = parser.parse_args()
    base.START = date(2020, 1, 1)
    base.END = date(2026, 8, 23)
    if args.command == "acquire":
        base.acquire(args.private_root.resolve(), 24)
    else:
        base.derive(args.private_root.resolve())


if __name__ == "__main__":
    main()
