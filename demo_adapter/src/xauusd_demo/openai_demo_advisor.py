"""Bounded structured OpenAI advisor for broker-observed XAUUSD DEMO setups.

The model may approve a deterministic proposed side or return NO_TRADE.
It cannot set lot size, alter SL/TP, call MT5, relax risk limits, or modify
production source. Failed requests => NO_TRADE; decisions persist by setup
key and UTC day so restart/brief outages do not trigger an API storm.
Model data sent: small closed-bar summaries, no account ID/credentials.
"""
from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .envelope import DemoSafetyError

_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "direction": {
            "type": "string",
            "enum": ["BUY", "SELL", "NO_TRADE"],
        },
        "regime": {
            "type": "string",
            "enum": ["TREND", "RANGE", "VOLATILE", "UNCERTAIN"],
        },
        "reason_code": {
            "type": "string",
            "enum": [
                "STRUCTURE_SUPPORTS_ENTRY", "COUNTER_TREND",
                "WEAK_MOMENTUM", "COST_OR_VOLATILITY",
                "CONFLICTING_TIMEFRAMES", "INSUFFICIENT_EDGE",
            ],
        },
    },
    "required": ["direction", "regime", "reason_code"],
    "additionalProperties": False,
}

_INSTRUCTIONS = (
    "You review completed-bar XAUUSD technical setups for an experimental "
    "Exness DEMO autonomous trading agent. Respond ONLY using the supplied "
    "JSON schema. Evaluate higher-timeframe alignment, price structure, "
    "breakout/retest, trend, momentum, likely stop hunting and transaction "
    "cost. You can approve the input candidate direction or choose NO_TRADE; "
    "never suggest a different direction unless the source setup supports "
    "it, and never fabricate news or broker facts. Reject weak or uncertain "
    "setups. Never propose order size or wider stops. This is DEMO research "
    "using virtual money, NOT a claim of profitability."
)


class OpenAIDemoAdvisor:
    """Single-writer SQLite cache, strict per-day budget, HTTPS only."""

    def __init__(
        self, path: Path, *, api_key: str | None = None,
        model: str = "gpt-6-luna", max_requests_utc_day: int = 32,
    ) -> None:
        self._key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self._key:
            raise DemoSafetyError(
                "OpenAI API key not configured on VPS; AI DEMO trading not armed"
            )
        if model not in ("gpt-6-luna", "gpt-6.1-sol"):
            raise DemoSafetyError("unreviewed OpenAI model")
        if not 1 <= max_requests_utc_day <= 96:
            raise DemoSafetyError("OpenAI daily call budget invalid")
        self._model = model
        self._limit = max_requests_utc_day
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS ai_reviews ("
            "setup_key TEXT PRIMARY KEY, utc_day TEXT NOT NULL, "
            "decision TEXT NOT NULL, reason TEXT NOT NULL, "
            "model TEXT NOT NULL)"
        )
        self._db.commit()
        self.last_reason = "NOT_CALLED"

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> OpenAIDemoAdvisor:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(self, market: dict[str, object]) -> dict[str, Any]:
        payload = {
            "model": self._model,
            "instructions": _INSTRUCTIONS,
            "input": json.dumps(market, sort_keys=True, separators=(",", ":")),
            "store": False,
            "max_output_tokens": 200,
            "text": {
                "format": {
                    "type": "json_schema", "name": "xauusd_demo_review",
                    "strict": True, "schema": _DECISION_SCHEMA,
                }
            },
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            json.dumps(payload).encode("utf-8"),
            {
                "Authorization": "Bearer " + self._key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as response:  # noqa: S310
            if response.status != 200:
                raise DemoSafetyError("OpenAI API non-200 response")
            data = response.read(32768)
        result = json.loads(data)
        if result.get("status") != "completed":
            raise DemoSafetyError("OpenAI incomplete response")
        texts = [
            block["text"]
            for output in result.get("output", [])
            if output.get("type") == "message"
            for block in output.get("content", [])
            if block.get("type") == "output_text"
        ]
        if len(texts) != 1:
            raise DemoSafetyError("OpenAI response text missing or ambiguous")
        answer = json.loads(texts[0])
        if (
            type(answer) is not dict or set(answer) != {"direction", "regime", "reason_code"}
            or answer["direction"] not in ("BUY", "SELL", "NO_TRADE")
            or answer["regime"] not in ("TREND", "RANGE", "VOLATILE", "UNCERTAIN")
            or answer["reason_code"] not in (
                "STRUCTURE_SUPPORTS_ENTRY", "COUNTER_TREND",
                "WEAK_MOMENTUM", "COST_OR_VOLATILITY",
                "CONFLICTING_TIMEFRAMES", "INSUFFICIENT_EDGE",
            )
        ):
            raise DemoSafetyError("OpenAI schema mismatch")
        return answer

    def approve(
        self, *, setup_key: str, proposed_side: str,
        observed_utc: datetime, market: dict[str, object],
    ) -> bool:
        if len(setup_key) != 64 or proposed_side not in ("BUY", "SELL"):
            raise DemoSafetyError("invalid candidate sent to OpenAI")
        if observed_utc.tzinfo is None or observed_utc.utcoffset().total_seconds() != 0:
            raise DemoSafetyError("AI setup timestamp not UTC")
        cached = self._db.execute(
            "SELECT decision,reason FROM ai_reviews WHERE setup_key=?",
            (setup_key,),
        ).fetchone()
        if cached is not None:
            self.last_reason = str(cached[1])
            return cached[0] == proposed_side
        day = observed_utc.astimezone(UTC).date().isoformat()
        used = self._db.execute(
            "SELECT COUNT(*) FROM ai_reviews WHERE utc_day=?", (day,),
        ).fetchone()[0]
        if used >= self._limit:
            self.last_reason = "AI_DAILY_BUDGET_EXHAUSTED"
            return False
        outcome, reason = "NO_TRADE", "AI_UNAVAILABLE_OR_REJECTED"
        try:
            result = self._request(market)
            outcome = result["direction"]
            reason = "AI_" + result["reason_code"]
            if outcome not in (proposed_side, "NO_TRADE"):
                outcome, reason = "NO_TRADE", "AI_SIDE_MISMATCH"
        except (
            DemoSafetyError, ValueError, TypeError,
            OSError, urllib.error.URLError,
            json.JSONDecodeError,
        ):
            # Do not log HTTP headers, key, raw prompts or provider payloads.
            outcome, reason = "NO_TRADE", "AI_UNAVAILABLE_OR_REJECTED"
        self._db.execute(
            "INSERT OR IGNORE INTO ai_reviews VALUES (?,?,?,?,?)",
            (setup_key, day, outcome, reason, self._model),
        )
        self._db.commit()
        self.last_reason = reason
        return outcome == proposed_side
