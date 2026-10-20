"""APC-DEMO-CANARY prospective operator runner — NO approval or auto activation.

Do not run on VPS without a *separate*, exact-head APC-DEMO-CANARY owner
authorization and a separately approved isolated execution-off stage.
No account selection/login, symbols except XAUUSD or autonomous loop.
One explicit operator entry command, one explicit operator close command.
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from xauusd_demo.canary_lifecycle import (
    CANARY_APC_TOKEN,
    CanaryJournal,
    DemoCanaryLifecycle,
    exact_demo_identity,
)
from xauusd_demo.control import ARM_CONFIRMATION, DemoControlState, DemoControlStore
from xauusd_demo.envelope import (
    DemoActivationPermit,
    DemoOrderRequest,
    DemoSafetyError,
    DemoSide,
)

PYTHON_EXE = r"C:\Program Files\Python312\python.exe"
TERMINAL_EXE = r"C:\Program Files\MetaTrader 5\terminal64.exe"
PRIVATE_SUBDIR = "XAUUSD-APC-DEMO-CANARY-S2"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OWNER GATED single demo canary only")
    parser.add_argument("--mode", choices=("entry", "close"), required=True)
    parser.add_argument("--owner-apc", default="")
    parser.add_argument("--activation-id", required=True)
    parser.add_argument("--expires-utc", required=True)
    parser.add_argument("--side", choices=("BUY", "SELL"))
    parser.add_argument("--stop", type=Decimal)
    args = parser.parse_args(argv)

    if args.owner_apc != CANARY_APC_TOKEN:
        raise DemoSafetyError("EXPLICIT_APC_DEMO_CANARY_OWNER_AUTHORIZATION_REQUIRED")
    if sys.platform != "win32" or sys.version_info[:2] != (3, 12):
        raise DemoSafetyError("CANARY_REQUIRES_WIN_PYTHON_312")
    if sys.executable.casefold() != PYTHON_EXE.casefold():
        raise DemoSafetyError("CANARY_PINNED_INTERPRETER_MISMATCH")
    if args.mode == "entry" and (args.side is None or args.stop is None):
        raise DemoSafetyError("CANARY_EXACT_ENTRY_SIDE_AND_STOP_REQUIRED")
    if args.mode == "close" and (args.side is not None or args.stop is not None):
        raise DemoSafetyError("CANARY_CLOSE_MUST_NOT_CREATE_NEW_RISK")
    now = datetime.now(UTC)
    try:
        expiry = datetime.fromisoformat(args.expires_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DemoSafetyError("CANARY_INVALID_APC_EXPIRY") from exc
    if expiry.tzinfo is None or expiry.utcoffset() is None:
        raise DemoSafetyError("CANARY_APC_EXPIRY_MUST_BE_UTC_AWARE")
    expiry = expiry.astimezone(UTC)
    if expiry <= now or expiry > now + timedelta(minutes=20):
        raise DemoSafetyError("CANARY_APC_WINDOW_MUST_BE_WITHIN_20MIN")
    permit = DemoActivationPermit(
        activation_id=args.activation_id,
        account_id_sha256=exact_demo_identity().account_id_sha256,
        server=exact_demo_identity().server,
        max_daily_submissions=1,
        not_before_utc=now - timedelta(minutes=1),
        expires_utc=expiry,
    )
    permit.validate(now=now)
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise DemoSafetyError("CANARY_PRIVATE_STAGING_LOCATION_MISSING")
    private_dir = Path(base) / PRIVATE_SUBDIR
    if not private_dir.is_dir():
        raise DemoSafetyError("CANARY_EXECUTION_OFF_STAGE_NOT_PRESENT")
    if not (private_dir / "control.sqlite3").is_file():
        raise DemoSafetyError("CANARY_DURABLE_KILL_CONTROL_NOT_STAGED")
    if not (private_dir / "canary.sqlite3").is_file():
        raise DemoSafetyError("CANARY_DURABLE_ONCE_LEDGER_NOT_STAGED")

    # Only AFTER all owner, interpreter, expiry and isolated stage checks.
    mt5 = importlib.import_module("MetaTrader5")
    if not mt5.initialize(path=TERMINAL_EXE, timeout=10000):
        raise DemoSafetyError("CANARY_EXISTING_TERMINAL_ATTACH_FAILED")
    try:
        with (
            DemoControlStore(private_dir / "control.sqlite3") as control,
            CanaryJournal(private_dir / "canary.sqlite3") as journal,
        ):
            lifecycle = DemoCanaryLifecycle(mt5, control, journal)
            if args.mode == "entry":
                if control.snapshot().state is not DemoControlState.KILLED:
                    raise DemoSafetyError("CANARY_ARM_REQUIRES_KILLED")
                if journal.stage() != "UNUSED":
                    raise DemoSafetyError("CANARY_ALREADY_ATTEMPTED")
                # This owner APC must independently authorize the exact
                # side and SL; no automated signal can choose them.
                control.arm(
                    permit=permit, identity=exact_demo_identity(),
                    now=now, confirmation_phrase=ARM_CONFIRMATION,
                )
                assert args.side is not None and args.stop is not None
                result = lifecycle.open_once(
                    request=DemoOrderRequest(
                        request_id=str(uuid.uuid4()), symbol="XAUUSD",
                        side=DemoSide(args.side), volume_lots=Decimal("0.01"),
                        stop_loss=args.stop,
                    ),
                    permit=permit, now=now, apc_token=CANARY_APC_TOKEN,
                )
                print("ONE_DEMO_ENTRY_RECONCILED_TICKET=" + result.ticket)
                print("DEMO_SCENARIO_WORST_LOSS_USD=" + str(result.worst_loss_usd))
                print("DEMO_SCENARIO_POLICY_A_CAP_USD=" + str(result.risk_cap_usd))
                print("CANARY_REQUIRES_SEPARATE_ATTENDED_CLOSE_INVOCATION")
            else:
                if control.snapshot().state is not DemoControlState.ACTIVE:
                    raise DemoSafetyError("CANARY_NOT_ACTIVE_FOR_OWNER_CLOSE")
                result = lifecycle.close_once(
                    permit=permit, now=now, apc_token=CANARY_APC_TOKEN,
                )
                print(result)
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
