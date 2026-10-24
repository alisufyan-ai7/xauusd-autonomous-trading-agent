"""Read-only broker-grounded daily outcome research, no self-modifying trades.

A daily compact report retains observed deals, all-cost net P/L, winner
frequency and intra-cohort drawdown from known broker position identifiers.
No model training is implied: new strategies require offline challenge and
prospective admission before release. Reports are local, never pushed to a
public GitHub repository.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from .envelope import DemoSafetyError
from .mt5_demo import _decimal, _record


class DailyBrokerResearch:
    def __init__(
        self, *, mt5: Any, coordinator_db: Path, folder: Path,
    ) -> None:
        self._mt5 = mt5
        self._coordinator_db = coordinator_db
        self._folder = folder
        self._last_day: str | None = None

    def checkpoint(self, now: datetime) -> None:
        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise DemoSafetyError("research time not UTC")
        day = (now - timedelta(days=1)).date().isoformat()
        if day == self._last_day:
            return
        self._last_day = day
        folder = self._folder
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / (day + ".json")
        if target.exists():
            return
        if not self._coordinator_db.exists():
            return
        with sqlite3.connect(self._coordinator_db) as con:
            rows = con.execute(
                "SELECT receipt_json FROM agent_broker_receipts"
            ).fetchall()
        position_ids: set[int] = set()
        for (body,) in rows:
            try:
                pos = json.loads(body)["position_id"]
            except (ValueError, KeyError, TypeError) as exc:
                raise DemoSafetyError("invalid durable broker research receipt") from exc
            if type(pos) is not int or pos <= 0:
                raise DemoSafetyError("research position id invalid")
            position_ids.add(pos)
        results = []
        for pid in sorted(position_ids):
            raw = self._mt5.history_deals_get(position=pid)
            if raw is None:
                raise DemoSafetyError("broker deals not available for research")
            deals = tuple(_record(x, "trade deal") for x in raw)
            # Filter by settlement date, not by opening/setup date.
            owned = [
                x for x in deals
                if x.get("position_id") == pid
                and x.get("entry") == getattr(self._mt5, "DEAL_ENTRY_OUT", None)
                and x.get("symbol") == "XAUUSD"
                and type(x.get("time_msc")) is int
                and datetime.fromtimestamp(x["time_msc"] / 1000, UTC)
                    .date().isoformat() == day
            ]
            if not owned:
                continue
            amount = sum(
                (
                    _decimal(x.get("profit"), "profit")
                    + _decimal(x.get("commission"), "commission")
                    + _decimal(x.get("swap"), "swap")
                    + _decimal(x.get("fee"), "fee")
                )
                for x in owned
            )
            results.append({
                "broker_position_id": pid,
                "exits": len(owned),
                "net_usd": str(amount),
            })
        total = sum((Decimal(str(x["net_usd"])) for x in results), Decimal("0"))
        wins = sum(Decimal(x["net_usd"]) > 0 for x in results)
        report = {
            "utc_day": day,
            "account_type": "EXNESS_PRO_DEMO_ONLY",
            "known_closed_positions": len(results),
            "known_winning_positions": wins,
            "net_usd_after_broker_costs": str(total),
            "positions": results,
            "research_status": "OBSERVED_ONLY_NOT_STRATEGY_PROMOTED",
        }
        # Day reports are immutable: never rewrite an existing report.
        # No MT5 credential/login number, prompts, API key, or raw history.
        with target.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, separators=(",", ":"), sort_keys=True)
        # Compact operator reports: 45 rolling days. Durable trade data
        # remains in broker MT5 history and the coordinator's SQLite ledger.
        older = sorted(folder.glob("????-??-??.json"))
        for past in older[:-45]:
            past.unlink()
