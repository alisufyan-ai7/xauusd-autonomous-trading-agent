"""Assemble an offline execution-disabled release; never deploy or start it."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from xauusd_agent.ops.release import assemble_release


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--created-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--deployment-root", type=Path, default=Path("deploy/windows"))
    args = parser.parse_args()
    seal = assemble_release(
        args.output,
        wheel=args.wheel,
        deployment_root=args.deployment_root,
        release_id=args.release_id,
        created_at=args.created_at,
        source_revision=args.source_revision,
    )
    print(json.dumps(asdict(seal), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
