"""Attended EXNESS DEMO quarantine recovery: one stopped writer, broker-flat only.

Called solely by the native Windows guarded cutover script. This module
never sends/checks/modifies a broker order, switches MT5 accounts, configures
a terminal, reads OpenAI credentials, or alters historical trade journals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

from xauusd_demo.broker_money_readonly import EXPECTED_ACCOUNT_SHA256
from xauusd_demo.continuous_coordinator import ContinuousDemoCoordinator
from xauusd_demo.demo_forever_worker import one_os_process_lock
from xauusd_demo.ops_safety_watchdog import PersistentDemoSafetyWatchdog

START = datetime(2026, 10, 24, 16, 48, tzinfo=UTC)
JOURNALS = (
    "coordinator.sqlite", "watchdog.sqlite", "control.sqlite",
    "requests.sqlite", "cash.sqlite", "ai_reviews.sqlite",
    "position_protection.sqlite", "ai_position_actions.sqlite",
)


class RecoveryHold(Exception):
    """A release guard refused the attended operation; never auto-retry."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RecoveryHold("RECOVERY_HOLD_" + code)


def read_one(state: Path, filename: str, sql: str) -> tuple[Any, ...] | None:
    uri = "file:" + quote((state / filename).resolve().as_posix(), safe="/:") + "?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=1) as db:
        return db.execute(sql).fetchone()


def require_idle_journals(state: Path) -> None:
    require(all((state / name).is_file() for name in JOURNALS), "MISSING_LEDGER")
    require(
        read_one(
            state, "coordinator.sqlite",
            "SELECT state,reason,fingerprint FROM agent_control WHERE id=1",
        ) == ("QUARANTINED", "SOURCE_OR_FEATURE_EXCEPTION", EXPECTED_ACCOUNT_SHA256),
        "COORDINATOR_NOT_EXACT_SOURCE_QUARANTINE",
    )
    for table in ("agent_cycles", "agent_pending_receipts", "agent_broker_receipts"):
        require(
            read_one(state, "coordinator.sqlite", "SELECT COUNT(*) FROM " + table) == (0,),
            "EXISTING_ORDER_INTENT_OR_RECEIPT",
        )
    require(
        read_one(state, "requests.sqlite", "SELECT COUNT(*) FROM demo_submission") == (0,),
        "EXISTING_BROKER_SUBMISSION",
    )
    require(
        read_one(
            state, "control.sqlite",
            "SELECT state, account_id_sha256 FROM demo_control WHERE singleton_id=1",
        ) == ("ACTIVE", EXPECTED_ACCOUNT_SHA256),
        "DEMO_CONTROL_NOT_EXACT_ACTIVE_ACCOUNT",
    )
    require(
        read_one(state, "watchdog.sqlite", "SELECT state FROM watchdog WHERE id=1")
        == ("ACTIVE",),
        "WATCHDOG_STATE_CHANGED_MANUAL_REVIEW",
    )


def broker_flat(mt5: Any, now: datetime) -> None:
    term, acc = mt5.terminal_info(), mt5.account_info()
    require(term is not None and acc is not None, "TERMINAL_OR_ACCOUNT_INFO_MISSING")
    require(term.connected is True, "DEMO_TERMINAL_DISCONNECTED")
    require(term.tradeapi_disabled is False, "EXTERNAL_PYTHON_DISABLED")
    raw = f"{acc.company}|{acc.server}|{acc.login}|{acc.currency}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    require(
        acc.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
        and acc.company == "Exness Technologies Ltd"
        and acc.server == "Exness-MT5Trial15"
        and acc.currency == "USD"
        and digest == EXPECTED_ACCOUNT_SHA256,
        "WRONG_OR_UNVERIFIED_DEMO_ACCOUNT",
    )
    positions, orders = mt5.positions_get(), mt5.orders_get()
    require(
        positions is not None and orders is not None
        and len(positions) == 0 and len(orders) == 0,
        "BROKER_NOT_PROVEN_FLAT",
    )
    historical_deals = mt5.history_deals_get(START, now)
    historical_orders = mt5.history_orders_get(START, now)
    require(
        historical_deals is not None and historical_orders is not None
        and len(historical_deals) == 0 and len(historical_orders) == 0,
        "BROKER_ORDER_OR_DEAL_HISTORY_NOT_EMPTY",
    )
    symbol, tick = mt5.symbol_info("XAUUSD"), mt5.symbol_info_tick("XAUUSD")
    require(
        symbol is not None and tick is not None
        and symbol.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL,
        "BROKER_MARKET_NOT_TRADABLE",
    )
    tick_ms = tick.time_msc
    require(
        type(tick_ms) is int and tick_ms > 0
        and 0 <= now.timestamp() - tick_ms / 1000 <= 5,
        "XAUUSD_TICK_NOT_FRESH",
    )
    bars = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15, 1, 2)
    require(bars is not None and len(bars) >= 1, "M15_HISTORY_MISSING")
    close = max(int(bar["time"]) for bar in bars) + 15 * 60
    require(0 <= now.timestamp() - close <= 20 * 60, "M15_CLOSE_STALE")


def preserve_before_state(state: Path, vault: Path) -> None:
    require(vault.is_dir() and not any(vault.iterdir()), "PRIVATE_VAULT_NOT_EMPTY")
    for original in state.iterdir():
        if not original.is_file():
            continue
        if original.name.endswith(".sqlite"):
            uri = (
                "file:" + quote(original.resolve().as_posix(), safe="/:") + "?mode=ro"
            )
            source = sqlite3.connect(uri, uri=True, timeout=2)
            destination = sqlite3.connect(str(vault / original.name))
            try:
                source.backup(destination)
                require(
                    destination.execute("PRAGMA quick_check").fetchone() == ("ok",),
                    "SQLITE_BACKUP_INTEGRITY",
                )
            finally:
                destination.close()
                source.close()
        elif original.name != "openai_key.dpapi" and (
            original.suffix in (".json", ".jsonl", ".log")
            or original.name.startswith("service-console.log")
        ):
            shutil.copy2(original, vault / original.name)
    require(
        all((vault / name).is_file() for name in JOURNALS),
        "PRIVATE_JOURNAL_BACKUP_INCOMPLETE",
    )
    (vault / "recovery_prestate_manifest.json").write_text(
        json.dumps(
            {
                "classification": "PRIVATE_LOCAL_RECOVERY_EVIDENCE",
                "stage": "BACKUP_BEFORE_CONTROL_RECOVERY",
                "utc": datetime.now(UTC).isoformat(),
                "historical_broker_orders_since_deployment": 0,
                "historical_broker_deals_since_deployment": 0,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def attended_recover(
    state: Path, vault: Path, terminal: str, mt5: Any,
    now_func: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> None:
    """Caller has already proved one existing task is stopped and same user."""
    with one_os_process_lock(state / "writer.lock"):
        require(
            bool(mt5.initialize(path=terminal, timeout=10000)),
            "PINNED_DEMO_MT5_INITIALIZE_FAILED",
        )
        try:
            broker_flat(mt5, now_func())
            require_idle_journals(state)
            preserve_before_state(state, vault)
            # Repeat actual MT5 exposure+identity after backup, at mutation time.
            instant = now_func()
            broker_flat(mt5, instant)
            require_idle_journals(state)
            with ContinuousDemoCoordinator(
                state / "coordinator.sqlite",
                account_fingerprint=EXPECTED_ACCOUNT_SHA256,
            ) as coordinator, PersistentDemoSafetyWatchdog(
                state / "watchdog.sqlite", max_age_seconds=1800,
            ) as watchdog:
                require(
                    coordinator.status() == "QUARANTINED"
                    and watchdog.status() == "ACTIVE",
                    "STATE_CHANGED_BEFORE_REARM",
                )
                coordinator.kill("OWNER_ATTENDED_BROKER_FLAT_SOURCE_RECOVERY")
                coordinator.arm_attended(
                    confirmation="ARM-CONTINUOUS-PRO-DEMO-XAUUSD",
                    broker_flat_confirmed=True,
                )
                watchdog.kill(
                    now=instant,
                    reason="OWNER_ATTENDED_WATCHDOG_STALE_HEARTBEAT_RECOVERY",
                )
                watchdog.arm_attended(
                    now=instant, confirmation_phrase="P1-ARM-DEMO-WATCHDOG",
                )
                require(
                    coordinator.status() == "ACTIVE"
                    and watchdog.status() == "ACTIVE",
                    "REARM_DID_NOT_COMMIT",
                )
        finally:
            mt5.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--terminal", required=True)
    parser.add_argument(
        "--attended-confirmation",
        choices=("RECOVER-PINNED-EXNESS-DEMO-OWNER-ATTENDED",),
        required=True,
    )
    args = parser.parse_args()
    try:
        import MetaTrader5 as mt5

        attended_recover(args.state, args.vault, args.terminal, mt5)
    except RecoveryHold as exc:
        print(str(exc), flush=True)
        return 1
    except Exception as exc:
        # Do not emit MT5 errors, broker account identities or filenames.
        print("RECOVERY_HOLD_UNEXPECTED_" + type(exc).__name__, flush=True)
        return 1
    print("RECOVERY_CONTROL_AND_WATCHDOG_ACTIVE_BROKER_FLAT_NO_ORDER", flush=True)
    print("RECOVERY_PRIVATE_BEFORE_STATE_BACKUP_VERIFIED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
