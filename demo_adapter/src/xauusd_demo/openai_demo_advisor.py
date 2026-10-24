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
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .envelope import DemoSafetyError
from .openai_demo_connectivity import CANDIDATE_MODELS

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
    """Single-writer model cache, priced daily cash budget; not 32-review cap."""

    def __init__(
        self, path: Path, *, api_key: str | None = None,
        model: str = "gpt-5.6-luna", daily_budget_usd: Decimal | None = None,
    ) -> None:
        self._key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self._key:
            raise DemoSafetyError(
                "OpenAI API key not configured on VPS; AI DEMO trading not armed"
            )
        if model not in CANDIDATE_MODELS:
            raise DemoSafetyError("unreviewed OpenAI model")
        try:
            budget = (
                daily_budget_usd if daily_budget_usd is not None
                else Decimal(os.environ.get("XAUUSD_OPENAI_DAILY_BUDGET_USD", "2.00"))
            )
        except (ValueError, InvalidOperation) as exc:
            raise DemoSafetyError("invalid OpenAI USD budget setting") from exc
        if not budget.is_finite() or not Decimal("0.01") <= budget <= Decimal("100"):
            raise DemoSafetyError("OpenAI daily USD budget must be 0.01..100")
        self._model = model
        self._budget = budget
        # One conservative 1-cent reserved liability per call while a network
        # request is outstanding; actual usage reduces the final charge.
        # Reserve a bounded cost BEFORE each network request. Larger
        # models receive higher initial liability; settle by API usage.
        self._reserved_usd = {
            "gpt-5.6-luna": Decimal("0.01"),
            "gpt-5.6-terra": Decimal("0.05"),
            "gpt-5.6-sol": Decimal("0.10"),
        }[model]
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
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS ai_spend ("
            "review_key TEXT PRIMARY KEY, utc_day TEXT NOT NULL, "
            "charged_usd TEXT NOT NULL, requested_utc TEXT NOT NULL)"
        )
        self._db.commit()
        self.last_reason = "NOT_CALLED"

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> OpenAIDemoAdvisor:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _invoke(
        self, market: dict[str, object], *,
        instructions: str, schema: dict[str, Any], name: str,
    ) -> dict[str, Any]:
        input_text = json.dumps(
            market, sort_keys=True, separators=(",", ":"),
        )
        if len(input_text) > 16000:
            raise DemoSafetyError("AI prompt unexpectedly large")
        payload = {
            "model": self._model,
            "instructions": instructions,
            "input": input_text,
            "store": False,
            "max_output_tokens": 512,
            "text": {"format": {
                "type": "json_schema", "name": name,
                "strict": True, "schema": schema,
            }},
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
        if type(answer) is not dict:
            raise DemoSafetyError("OpenAI JSON response not an object")
        if set(answer) != set(schema["required"]):
            raise DemoSafetyError("OpenAI schema mismatch")
        for field, allowed in schema["properties"].items():
            if answer[field] not in allowed["enum"]:
                raise DemoSafetyError("OpenAI JSON enumerations invalid")
        # Model API usage is authoritative when available, not guessed from
        # number of requests. Ignore cached-token discount conservatively.
        usage = result.get("usage", {})
        if not isinstance(usage, dict):
            usage = {}
        answer["_usage"] = usage
        return answer

    def _request(self, market: dict[str, object]) -> dict[str, Any]:
        return self._invoke(
            market, instructions=_INSTRUCTIONS,
            schema=_DECISION_SCHEMA, name="xauusd_demo_review",
        )

    def _position_request(self, market: dict[str, object]) -> dict[str, Any]:
        return self._invoke(
            market, instructions=(
                "You evaluate an ALREADY OPEN, DEAL-VERIFIED Exness XAUUSD "
                "DEMO position, with risk protected by actual broker SL. "
                "Choose HOLD, EARLY_EXIT or TIGHTEN_TP based only on the "
                "provided position's favorable/adverse movement, current "
                "bid/ask, structure and regime. Reject speculative actions. "
                "TIGHTEN_TP means move target inward, NEVER widen risk. "
                "You cannot set prices, lot sizes or issue MT5 orders."
            ),
            schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": [
                        "HOLD", "EARLY_EXIT", "TIGHTEN_TP",
                    ]},
                    "reason_code": {"type": "string", "enum": [
                        "STRUCTURE_INVALID", "VOLATILITY_SPIKE",
                        "PROTECT_PROFIT", "TREND_CONTINUES", "NO_EDGE",
                    ]},
                },
                "required": ["action", "reason_code"],
                "additionalProperties": False,
            },
            name="xauusd_known_position_advice",
        )

    def _usage_cost(self, usage: Any) -> Decimal | None:
        if not isinstance(usage, dict):
            return None
        inp = usage.get("input_tokens")
        out = usage.get("output_tokens")
        if (
            type(inp) is not int or type(out) is not int
            or inp < 0 or out < 0 or inp > 200000 or out > 5000
        ):
            return None
        # GPT-5.6 Standard rates are charged by the selected model.
        # Deliberately ignore cached discounts and bill higher bounded
        # reservation on missing usage receipts.
        # Rates per million tokens are deliberately conservative ceilings
        # for the reviewed fallbacks, not a promise of actual billed totals.
        # Official GPT-5.6 STANDARD token rates, USD per million as at
        # 2026-10-24. Ignore caching discounts (conservative estimate).
        input_rate, output_rate = {
            "gpt-5.6-luna": (Decimal("0.20"), Decimal("1.20")),
            "gpt-5.6-terra": (Decimal("2.00"), Decimal("12.00")),
            "gpt-5.6-sol": (Decimal("4.00"), Decimal("20.00")),
        }[self._model]
        return (
            Decimal(inp) * input_rate + Decimal(out) * output_rate
        ) / Decimal(1000000)

    def _reserve(
        self, *, review_key: str, observed_utc: datetime,
    ) -> bool:
        day = observed_utc.astimezone(UTC).date().isoformat()
        rows = self._db.execute(
            "SELECT charged_usd FROM ai_spend WHERE utc_day=?", (day,),
        ).fetchall()
        spent = sum((Decimal(str(x[0])) for x in rows), Decimal(0))
        existing = self._db.execute(
            "SELECT 1 FROM ai_spend WHERE review_key=?", (review_key,),
        ).fetchone()
        if existing is not None:
            # Power loss after a billable request but before the answer was
            # committed: never repay/retry an uncertain provider outcome.
            self.last_reason = "AI_PREVIOUS_REQUEST_OUTCOME_UNKNOWN"
            return False
        if spent + self._reserved_usd > self._budget:
            self.last_reason = "AI_DAILY_USD_BUDGET_PROTECTED"
            return False
        # Reservation is DURABLE before making an actual billable request.
        # Across a power loss this protects against unknown-charge retries.
        self._db.execute(
            "INSERT INTO ai_spend VALUES (?,?,?,?)",
            (
                review_key, day, str(self._reserved_usd),
                observed_utc.isoformat(),
            ),
        )
        self._db.commit()
        return True

    def _actual_spend(
        self, *, review_key: str, usage: Any,
    ) -> None:
        cost = self._usage_cost(usage)
        if cost is None:
            return
        # Usage is source-reported; treat both allowed models at their
        # conservative published Standard, non-cached USD/token rates.
        self._db.execute(
            "UPDATE ai_spend SET charged_usd=? WHERE review_key=?",
            (str(cost), review_key),
        )
        self._db.commit()

    def approve(
        self, *, setup_key: str, proposed_side: str,
        observed_utc: datetime, market: dict[str, object],
    ) -> bool:
        if len(setup_key) != 64 or proposed_side not in ("BUY", "SELL"):
            raise DemoSafetyError("invalid candidate sent to OpenAI")
        if observed_utc.tzinfo is None or observed_utc.utcoffset() != timedelta(0):
            raise DemoSafetyError("AI setup timestamp not UTC")
        cached = self._db.execute(
            "SELECT decision,reason FROM ai_reviews WHERE setup_key=?",
            (setup_key,),
        ).fetchone()
        if cached is not None:
            self.last_reason = str(cached[1])
            return str(cached[0]) == proposed_side
        day = observed_utc.astimezone(UTC).date().isoformat()
        if not self._reserve(
            review_key="entry:" + setup_key, observed_utc=observed_utc,
        ):
            return False
        outcome, reason = "NO_TRADE", "AI_UNAVAILABLE_OR_REJECTED"
        try:
            result = self._request(market)
            self._actual_spend(
                review_key="entry:" + setup_key,
                usage=result.get("_usage"),
            )
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

    def manage_position(
        self, *, review_key: str, observed_utc: datetime,
        market: dict[str, object],
    ) -> str:
        """At most once per known-position M15 bar; shared USD cost budget."""
        if not review_key.startswith("position:") or len(review_key) > 160:
            raise DemoSafetyError("position advice key invalid")
        if observed_utc.tzinfo is None or observed_utc.utcoffset() != timedelta(0):
            raise DemoSafetyError("position review timestamp not UTC")
        cached = self._db.execute(
            "SELECT decision,reason FROM ai_reviews WHERE setup_key=?",
            (review_key,),
        ).fetchone()
        if cached is not None:
            self.last_reason = str(cached[1])
            return str(cached[0])
        if not self._reserve(
            review_key=review_key, observed_utc=observed_utc,
        ):
            return "HOLD"
        outcome, reason = "HOLD", "POSITION_AI_UNAVAILABLE"
        try:
            result = self._position_request(market)
            self._actual_spend(
                review_key=review_key, usage=result.get("_usage"),
            )
            outcome = str(result["action"])
            reason = "AI_POSITION_" + str(result["reason_code"])
            if outcome not in ("HOLD", "EARLY_EXIT", "TIGHTEN_TP"):
                outcome, reason = "HOLD", "AI_INVALID_POSITION_ACTION"
        except (
            DemoSafetyError, ValueError, TypeError, OSError,
            urllib.error.URLError, json.JSONDecodeError,
        ):
            pass
        day = observed_utc.astimezone(UTC).date().isoformat()
        self._db.execute(
            "INSERT OR IGNORE INTO ai_reviews VALUES (?,?,?,?,?)",
            (review_key, day, outcome, reason, self._model),
        )
        self._db.commit()
        self.last_reason = reason
        return outcome
