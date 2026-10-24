"""Entry point for the persistent, multiple-trade Exness Pro DEMO service.

Usage on the dedicated Windows VPS only:
  python -m xauusd_demo.run_exness_demo --activate
  python -m xauusd_demo.run_exness_demo --run

No MT5 login/account switching, terminal configuration mutation or LIVE modes.
The operator's one-time --activate authorizes 0.01-lot experimental DEMO
operations, not a fixed number of lifetime orders. Default three new entry
submissions per UTC day; continuing daily pending/fill/position supervision.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from contextlib import ExitStack
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from .broker_money_readonly import EXPECTED_ACCOUNT_SHA256
from .continuous_coordinator import ContinuousDemoCoordinator
from .control import ARM_CONFIRMATION, DemoControlStore
from .demo_forever_worker import ContinuousDemoWorker
from .envelope import DemoActivationPermit, DemoIdentity, DemoPolicy, DemoSafetyError
from .ledger import DemoSubmissionLedger
from .mt5_demo import DemoMT5Adapter
from .mt5_experimental_demo_sources import ExperimentalDemoCostSources
from .mt5_sevenframe_source import ReadOnlyMT5SevenFrameSource
from .mt5_tpb_strategy_source import MT5ExperimentalTPBPlanSource
from .ops_safety_watchdog import PersistentDemoSafetyWatchdog
from .prospective_cash_journal import ProspectiveDemoCashJournal
from .risk_binding import DEMO_LIFECYCLE_SCOPE, DemoRiskCalibration
from .s2_qualified_coordinator_port import QualifiedS2CoordinatorPort

PER_DAY = 3
SERVICE_ID = "XAUUSD-EXNESS-PRO-DEMO-AUTONOMOUS-V0-20261024"
START = datetime(2026, 10, 24, tzinfo=UTC)
END = datetime(2036, 10, 24, tzinfo=UTC)
WATCHDOG_ARM = "P1-ARM-DEMO-WATCHDOG"
COORDINATOR_ARM = "ARM-CONTINUOUS-PRO-DEMO-XAUUSD"


def _ident() -> DemoIdentity:
    return DemoIdentity(
        "Exness Technologies Ltd",
        "Exness-MT5Trial15",
        EXPECTED_ACCOUNT_SHA256,
        "USD",
    )


def _permit() -> DemoActivationPermit:
    return DemoActivationPermit(
        activation_id=SERVICE_ID,
        account_id_sha256=EXPECTED_ACCOUNT_SHA256,
        server="Exness-MT5Trial15",
        max_daily_submissions=PER_DAY,
        not_before_utc=START,
        expires_utc=END,
    )


def _calibration() -> DemoRiskCalibration:
    # Fixed conservative 0.01-lot DEMO reserve pre-entry. Broker-derived
    # dynamic spread/gap/fee stress is calculated independently in S2.
    return DemoRiskCalibration(
        calibration_id="EXNESS_PRO_DEMO_REPEATED_EXPERIMENT_V0",
        source_sha256=hashlib.sha256(
            b"exness-pro-demo-0.01-only|current-adverse-usd10|stress-usd20"
        ).hexdigest(),
        scope=DEMO_LIFECYCLE_SCOPE,
        current_adverse_cost=Decimal("10"),
        stressed_adverse_cost=Decimal("20"),
    )


def serve(*, activate: bool, directory: Path, mt5: Any) -> None:
    now = datetime.now(UTC)
    ident = _ident()
    calibration = _calibration()
    permit = _permit()
    # One state root with no historic file copying, login changes or key
    # storage. Credentials stay inside the operator's existing MT5 terminal.
    directory.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        ledger = stack.enter_context(DemoSubmissionLedger(
            directory / "requests.sqlite", max_daily_submissions=PER_DAY
        ))
        control = stack.enter_context(DemoControlStore(directory / "control.sqlite"))
        cash = stack.enter_context(ProspectiveDemoCashJournal(
            directory / "cash.sqlite"
        ))
        coordinator = stack.enter_context(ContinuousDemoCoordinator(
            directory / "coordinator.sqlite",
            account_fingerprint=EXPECTED_ACCOUNT_SHA256,
        ))
        watchdog = stack.enter_context(PersistentDemoSafetyWatchdog(
            directory / "watchdog.sqlite", max_age_seconds=1800
        ))
        adapter = stack.enter_context(DemoMT5Adapter(
            ident, DemoPolicy(PER_DAY, calibration.sha256()),
            ledger, control=control, module=mt5,
        ))
        preflight = adapter.preflight()
        if not preflight["demo_identity_match"]:
            raise DemoSafetyError("attached MT5 is not exact pinned DEMO")
        if preflight["external_python_trading_enabled"] is not True:
            raise DemoSafetyError(
                "MT5 external Python trading option is DISABLED. "
                "Enable it only in the verified Exness Pro DEMO terminal "
                "before running this operator-confirmed service."
            )
        if activate:
            if preflight["open_positions"] or preflight["pending_orders"]:
                raise DemoSafetyError("cannot initialize a new campaign with exposure")
            control.arm(
                permit=permit, identity=ident, now=now,
                confirmation_phrase=ARM_CONFIRMATION,
            )
            coordinator.arm_attended(
                confirmation=COORDINATOR_ARM, broker_flat_confirmed=True,
            )
            watchdog.arm_attended(
                now=now, confirmation_phrase=WATCHDOG_ARM,
            )
        else:
            control.assert_active(permit=permit, identity=ident, now=now)
        sources = ExperimentalDemoCostSources(mt5=mt5, cash_journal=cash)
        plan = MT5ExperimentalTPBPlanSource(
            broker_bars=ReadOnlyMT5SevenFrameSource(mt5),
            sources=sources, account_fingerprint=EXPECTED_ACCOUNT_SHA256,
        )
        port = QualifiedS2CoordinatorPort(
            adapter=adapter, plan_source=plan, sources=sources,
            activation=permit, risk_calibration=calibration,
        )
        print(
            "EXNESS_DEMO_CONTINUOUS_SERVICE_ACTIVE__REAL_SERVER_VIRTUAL_MONEY"
            " __NOT_LIVE__ONE_WRITER__MULTIPLE_DAYS",
            flush=True,
        )
        ContinuousDemoWorker(
            coordinator=coordinator, port=port, watchdog=watchdog,
            state_directory=directory, polling_seconds=5,
        ).serve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--activate", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--preflight", action="store_true")
    args = parser.parse_args(argv)
    if os.name != "nt":
        print("DEMO_EXECUTION_REQUIRES_WINDOWS_FOREXVPS", file=sys.stderr)
        return 2
    directory = Path(os.environ.get("LOCALAPPDATA", "")) / "XAUUSD-DemoService"
    try:
        import MetaTrader5 as mt5
        if args.preflight:
            with ExitStack() as stack:
                ledger = stack.enter_context(DemoSubmissionLedger(
                    directory / "requests.sqlite",
                    max_daily_submissions=PER_DAY,
                ))
                adapter = stack.enter_context(DemoMT5Adapter(
                    _ident(), DemoPolicy(PER_DAY, _calibration().sha256()),
                    ledger, module=mt5,
                ))
                health = adapter.preflight()
                print(
                    "EXNESS_DEMO_PREFLIGHT:"
                    + str({
                        "account_verified": health["demo_identity_match"],
                        "external_python_enabled": health[
                            "external_python_trading_enabled"
                        ],
                        "open_positions": health["open_positions"],
                        "pending_orders": health["pending_orders"],
                    }),
                    flush=True,
                )
                if health["external_python_trading_enabled"] is not True:
                    raise DemoSafetyError("external Python trading still disabled")
        else:
            serve(activate=bool(args.activate), directory=directory, mt5=mt5)
    except (DemoSafetyError, OSError, ValueError) as exc:
        # No private account, login, deal history, access token or raw quote.
        print(
            f"DEMO_SERVICE_FAIL_CLOSED__{type(exc).__name__}: "
            f"{str(exc)[:180]}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
