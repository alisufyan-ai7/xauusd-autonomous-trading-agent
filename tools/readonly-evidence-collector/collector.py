"""Phase 0 read-only Exness/MT5 account and Windows VPS evidence collector."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import platform
import re
import secrets
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from readonly_mt5 import ReadOnlyMT5


COLLECTOR_VERSION = "0.1.1"
POLICY_VERSION = "phase0-readonly-v1"
TIMEFRAMES = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "H1": 3600,
    "H4": 14400,
    "D1": 86400,
}
SENSITIVE_ID_KEYS = {
    "login",
    "ticket",
    "identifier",
    "order",
    "position",
    "position_id",
    "external_id",
}
REMOVE_KEYS = {"password", "token", "secret", "comment"}
PACKAGE_MANIFEST = "PACKAGE_MANIFEST.sha256"


class CollectionError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_package_manifest(base: Path) -> dict[str, Any]:
    manifest_path = base / PACKAGE_MANIFEST
    if not manifest_path.is_file():
        raise CollectionError(f"Missing {PACKAGE_MANIFEST}; use the complete verified package")
    checked = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        expected, relative = line.split("  ", 1)
        target = (base / relative).resolve()
        if target.parent != base.resolve() or not target.is_file():
            raise CollectionError(f"Invalid package manifest path: {relative}")
        actual = sha256_file(target)
        if not hmac.compare_digest(actual, expected):
            raise CollectionError(f"Package hash mismatch: {relative}")
        checked.append({"path": relative, "sha256": actual})
    return {"status": "PASS", "manifest": PACKAGE_MANIFEST, "files": checked}


def record_to_plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return iso_utc(value)
    if isinstance(value, Mapping):
        return {str(key): record_to_plain(item) for key, item in value.items()}
    if hasattr(value, "_asdict"):
        return record_to_plain(value._asdict())
    if isinstance(value, (list, tuple)):
        return [record_to_plain(item) for item in value]
    if hasattr(value, "dtype") and value.dtype.names:
        return [
            {name: record_to_plain(row[name].item() if hasattr(row[name], "item") else row[name]) for name in value.dtype.names}
            for row in value
        ]
    if hasattr(value, "item"):
        return record_to_plain(value.item())
    return str(value)


def scrub_path(value: str) -> str:
    value = re.sub(
        r"(?i)([A-Z]:\\Users\\)[^\\]+", r"\1<REDACTED_USER>", value
    )
    return re.sub(r"(?i)(/home/|/Users/)[^/]+", r"\1<REDACTED_USER>", value)


class Redactor:
    def __init__(self) -> None:
        self._key = secrets.token_bytes(32)

    def pseudonym(self, value: Any, namespace: str) -> str:
        message = f"{namespace}:{value}".encode("utf-8", errors="replace")
        digest = hmac.new(self._key, message, hashlib.sha256).hexdigest()
        return f"hmac-sha256:{digest}"

    def clean(self, value: Any, context: str = "") -> Any:
        plain = record_to_plain(value)
        if isinstance(plain, list):
            return [self.clean(item, context) for item in plain]
        if not isinstance(plain, dict):
            if isinstance(plain, str) and ("path" in context or "directory" in context):
                return scrub_path(plain)
            return plain
        output = {}
        for key, item in plain.items():
            lowered = key.lower()
            child_context = f"{context}.{lowered}" if context else lowered
            if lowered in REMOVE_KEYS:
                output[key] = "<REDACTED>"
            elif lowered == "name" and (context == "account" or context.startswith("account.")):
                output[key] = "<REDACTED>"
            elif lowered in SENSITIVE_ID_KEYS or lowered.endswith("_ticket"):
                output[key] = self.pseudonym(item, child_context)
            elif "path" in lowered or "directory" in lowered:
                output[key] = scrub_path(str(item))
            else:
                output[key] = self.clean(item, child_context)
        return output


def named_record(value: Any, label: str, api: Any) -> dict[str, Any]:
    if value is None:
        raise CollectionError(f"{label} returned no data; last_error={api.last_error()}")
    plain = record_to_plain(value)
    if not isinstance(plain, dict):
        raise CollectionError(f"{label} returned unexpected type")
    return plain


def compact_symbol(symbol: Mapping[str, Any]) -> dict[str, Any]:
    fields = [
        "name", "path", "description", "visible", "select", "custom", "digits",
        "point", "trade_mode", "trade_exemode", "filling_mode", "order_mode",
        "order_gtc_mode", "trade_calc_mode", "trade_contract_size",
        "trade_tick_size", "trade_tick_value", "trade_tick_value_profit",
        "trade_tick_value_loss", "volume_min", "volume_max", "volume_step",
        "volume_limit", "trade_stops_level", "trade_freeze_level", "spread",
        "spread_float", "swap_mode", "swap_long", "swap_short", "swap_rollover3days",
        "currency_base", "currency_profit", "currency_margin", "start_time",
        "expiration_time", "session_deals", "session_buy_orders", "session_sell_orders",
        "session_volume", "session_turnover", "session_interest", "time", "time_msc",
    ]
    return {key: symbol.get(key) for key in fields if key in symbol}


def normalize_market_times(value: Any) -> Any:
    if isinstance(value, list):
        return [normalize_market_times(item) for item in value]
    if not isinstance(value, dict):
        return value
    output = dict(value)
    if isinstance(output.get("time"), (int, float)):
        output["time_utc"] = iso_utc(datetime.fromtimestamp(output["time"], timezone.utc))
    if isinstance(output.get("time_msc"), (int, float)):
        output["time_msc_utc"] = iso_utc(
            datetime.fromtimestamp(output["time_msc"] / 1000.0, timezone.utc)
        )
    return {key: normalize_market_times(item) for key, item in output.items()}


def bar_gap_stats(rows: list[dict[str, Any]], interval_seconds: int) -> dict[str, Any]:
    epochs = [int(row["time"]) for row in rows if isinstance(row.get("time"), (int, float))]
    duplicates = len(epochs) - len(set(epochs))
    non_monotonic = sum(1 for left, right in zip(epochs, epochs[1:]) if right <= left)
    gaps = []
    for left, right in zip(epochs, epochs[1:]):
        delta = right - left
        if delta > interval_seconds:
            gaps.append(
                {
                    "from_utc": iso_utc(datetime.fromtimestamp(left, timezone.utc)),
                    "to_utc": iso_utc(datetime.fromtimestamp(right, timezone.utc)),
                    "delta_seconds": delta,
                    "missing_intervals_upper_bound": max(0, delta // interval_seconds - 1),
                }
            )
    return {
        "row_count": len(rows),
        "duplicate_timestamps": duplicates,
        "non_monotonic_transitions": non_monotonic,
        "gap_count": len(gaps),
        "first_20_gaps": gaps[:20],
        "note": "Weekend/market-closure gaps are counted; this is an integrity observation, not a session calendar.",
    }


def safe_call(api: Any, label: str, call, errors: list[dict[str, Any]]) -> Any:
    try:
        result = call()
        if result is None:
            errors.append({"operation": label, "error": record_to_plain(api.last_error())})
        return result
    except Exception as exc:
        errors.append({"operation": label, "error": f"{type(exc).__name__}: {exc}"})
        return None


def select_gold_symbol(symbols: list[dict[str, Any]], requested: str | None) -> tuple[str | None, str]:
    names = [str(item.get("name", "")) for item in symbols]
    if requested:
        return (requested, "operator_selected") if requested in names else (None, "requested_symbol_not_found")
    visible = [str(item.get("name")) for item in symbols if item.get("visible")]
    if len(visible) == 1:
        return visible[0], "single_visible_gold_candidate"
    if len(names) == 1:
        return names[0], "single_gold_candidate"
    return None, "ambiguous_gold_candidates_use_symbol_parameter"


def calculation_vectors(api: Any, symbol: str, info: Mapping[str, Any], tick: Mapping[str, Any], errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tick_size = float(info.get("trade_tick_size") or info.get("point") or 0.0)
    volume_min = float(info.get("volume_min") or 0.0)
    volume_step = float(info.get("volume_step") or volume_min or 0.0)
    volume_max = float(info.get("volume_max") or volume_min or 0.0)
    if tick_size <= 0 or volume_min <= 0:
        errors.append({"operation": "calculation_vectors", "error": "non-positive tick size or minimum volume"})
        return []
    volumes = sorted({volume_min, min(volume_max, volume_min + volume_step)})
    bid = float(tick.get("bid") or 0.0)
    ask = float(tick.get("ask") or 0.0)
    if bid <= 0 or ask <= 0:
        errors.append({"operation": "calculation_vectors", "error": "non-positive bid or ask"})
        return []
    vectors = []
    for direction, open_price, sign in (("BUY", ask, -1.0), ("SELL", bid, 1.0)):
        for volume in volumes:
            margin = safe_call(
                api,
                f"order_calc_margin:{direction}:{volume}",
                lambda d=direction, v=volume, p=open_price: api.order_calc_margin(d, symbol, v, p),
                errors,
            )
            for distance_ticks in (10, 100):
                close_price = open_price + sign * distance_ticks * tick_size
                profit = safe_call(
                    api,
                    f"order_calc_profit:{direction}:{volume}:{distance_ticks}",
                    lambda d=direction, v=volume, p=open_price, c=close_price: api.order_calc_profit(d, symbol, v, p, c),
                    errors,
                )
                vectors.append(
                    {
                        "direction": direction,
                        "volume": volume,
                        "open_price": open_price,
                        "close_price": close_price,
                        "distance_ticks": distance_ticks,
                        "calculated_profit_account_currency": record_to_plain(profit),
                        "calculated_margin_account_currency": record_to_plain(margin),
                    }
                )
    return vectors


def write_json(output_dir: Path, filename: str, value: Any) -> None:
    target = output_dir / filename
    if target.exists():
        raise CollectionError(f"Refusing to overwrite existing output: {target}")
    target.write_bytes(canonical_bytes(value))


def write_evidence_manifest(output_dir: Path) -> dict[str, Any]:
    files = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name not in {"MANIFEST.json", "MANIFEST.sha256"}:
            files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "1.0",
        "collector_version": COLLECTOR_VERSION,
        "policy_version": POLICY_VERSION,
        "created_utc": iso_utc(utc_now()),
        "files": files,
    }
    write_json(output_dir, "MANIFEST.json", manifest)
    (output_dir / "MANIFEST.sha256").write_text(
        f"{sha256_file(output_dir / 'MANIFEST.json')}  MANIFEST.json\n", encoding="ascii"
    )
    return manifest


def collect_evidence(api: Any, output_dir: Path, requested_symbol: str | None, bars_count: int, ticks_count: int, history_days: int, package_verification: dict[str, Any]) -> dict[str, Any]:
    output_dir.mkdir(parents=False, exist_ok=False)
    redactor = Redactor()
    errors: list[dict[str, Any]] = []
    started = utc_now()
    initialized = False
    guard_before = None
    guard_after = None
    try:
        initialized = bool(api.initialize())
        if not initialized:
            raise CollectionError(f"MT5 initialize failed: {api.last_error()}")

        terminal_before = named_record(api.terminal_info(), "terminal_info", api)
        guard_before = terminal_before.get("tradeapi_disabled") is True
        if not guard_before:
            raise CollectionError(
                "ABORTED SAFELY: enable 'Disable automated trading via external Python API' in MT5 Options, then rerun"
            )
        if terminal_before.get("connected") is not True:
            raise CollectionError("MT5 terminal is not connected")

        account_raw = named_record(api.account_info(), "account_info", api)
        all_symbols_raw = safe_call(api, "symbols_get", api.symbols_get, errors) or []
        all_symbols = [record_to_plain(item) for item in all_symbols_raw]
        gold_symbols = [
            compact_symbol(item)
            for item in all_symbols
            if isinstance(item, dict)
            and ("XAU" in str(item.get("name", "")).upper() or "GOLD" in str(item.get("name", "")).upper())
        ]
        selected_symbol, selection_reason = select_gold_symbol(gold_symbols, requested_symbol)

        selected_info = None
        tick = None
        bars = {}
        tick_history = []
        calculations = []
        if selected_symbol:
            selected_raw = safe_call(
                api, "symbol_info", lambda: api.symbol_info(selected_symbol), errors
            )
            if selected_raw is not None:
                selected_info = compact_symbol(record_to_plain(selected_raw))
            tick_raw = safe_call(
                api, "symbol_info_tick", lambda: api.symbol_info_tick(selected_symbol), errors
            )
            if tick_raw is not None:
                tick = normalize_market_times(record_to_plain(tick_raw))
            for timeframe, interval in TIMEFRAMES.items():
                rows_raw = safe_call(
                    api,
                    f"copy_rates_from_pos:{timeframe}",
                    lambda tf=timeframe: api.copy_rates_from_pos(selected_symbol, tf, 0, bars_count),
                    errors,
                )
                rows = record_to_plain(rows_raw) if rows_raw is not None else []
                if not isinstance(rows, list):
                    rows = []
                bars[timeframe] = {
                    "statistics": bar_gap_stats(rows, interval),
                    "rows": normalize_market_times(rows),
                }
            ticks_raw = safe_call(
                api,
                "copy_ticks_from",
                lambda: api.copy_ticks_from(selected_symbol, utc_now() - timedelta(hours=1), ticks_count),
                errors,
            )
            ticks_plain = record_to_plain(ticks_raw) if ticks_raw is not None else []
            tick_history = normalize_market_times(ticks_plain if isinstance(ticks_plain, list) else [])
            if selected_info and tick:
                calculations = calculation_vectors(api, selected_symbol, selected_info, tick, errors)

        history_from = utc_now() - timedelta(days=history_days)
        history_to = utc_now()
        exposure = {
            "open_orders": record_to_plain(safe_call(api, "orders_get", api.orders_get, errors) or []),
            "open_positions": record_to_plain(safe_call(api, "positions_get", api.positions_get, errors) or []),
            "history_from_utc": iso_utc(history_from),
            "history_to_utc": iso_utc(history_to),
            "history_orders": record_to_plain(
                safe_call(api, "history_orders_get", lambda: api.history_orders_get(history_from, history_to), errors) or []
            ),
            "history_deals": record_to_plain(
                safe_call(api, "history_deals_get", lambda: api.history_deals_get(history_from, history_to), errors) or []
            ),
        }

        terminal_after = named_record(api.terminal_info(), "terminal_info final", api)
        guard_after = terminal_after.get("tradeapi_disabled") is True
        if not guard_after:
            raise CollectionError("INVALID RUN: MT5 external-Python trading protection changed during capture")

        account_fingerprint = redactor.pseudonym(
            "|".join(
                str(account_raw.get(key, ""))
                for key in ("login", "server", "company", "currency", "margin_mode", "trade_mode")
            ),
            "account_fingerprint",
        )
        permissions = {
            "terminal_trade_allowed": terminal_before.get("trade_allowed"),
            "terminal_external_python_trading_disabled_before": guard_before,
            "terminal_external_python_trading_disabled_after": guard_after,
            "account_trade_allowed": account_raw.get("trade_allowed"),
            "account_trade_expert": account_raw.get("trade_expert"),
            "account_trade_mode": account_raw.get("trade_mode"),
            "selected_symbol_trade_mode": selected_info.get("trade_mode") if selected_info else None,
            "interpretation": "Runtime technical evidence only. It is not contractual or jurisdictional authorization.",
        }
        run_summary = {
            "schema_version": "1.0",
            "collector_version": COLLECTOR_VERSION,
            "policy_version": POLICY_VERSION,
            "started_utc": iso_utc(started),
            "completed_utc": iso_utc(utc_now()),
            "status": "PASS" if not errors and selected_symbol else "PARTIAL",
            "read_only_guard": "PASS",
            "account_fingerprint": account_fingerprint,
            "selected_symbol": selected_symbol,
            "symbol_selection_reason": selection_reason,
            "errors": errors,
            "gate_0_status": "INCOMPLETE",
            "manual_findings": [
                "MANUAL_DOCUMENTARY_VERIFICATION_REQUIRED: Exness contracting entity, residence/jurisdiction, client/account classification, current agreement, and automated-trading restrictions are not discoverable from MT5 alone.",
                "TRADING_SESSION_SCHEDULE_UNAVAILABLE: the Python API capture does not expose the authoritative weekly symbol trading-session table; obtain it from account-specific contract specifications or a separately verified non-trading export.",
            ],
        }
        environment = {
            "captured_utc": iso_utc(utc_now()),
            "os": platform.platform(),
            "windows_release": platform.release(),
            "windows_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "python_architecture_bits": struct.calcsize("P") * 8,
            "executable": scrub_path(sys.executable),
            "mt5_package": record_to_plain(api.package_metadata()),
            "mt5_terminal_version": record_to_plain(api.version()),
            "collection_parameters": {
                "requested_symbol": requested_symbol,
                "bars_count_per_timeframe": bars_count,
                "ticks_count_max": ticks_count,
                "history_days": history_days,
                "timeframes": list(TIMEFRAMES),
            },
        }
        terminal_evidence = {
            "before": redactor.clean(terminal_before, "terminal"),
            "after": redactor.clean(terminal_after, "terminal"),
        }
        account_evidence = redactor.clean(account_raw, "account")
        account_evidence["account_fingerprint"] = account_fingerprint
        account_evidence["permissions_summary"] = permissions
        symbol_evidence = {
            "candidate_count": len(gold_symbols),
            "candidates": redactor.clean(gold_symbols, "symbols"),
            "selected_symbol": selected_symbol,
            "selection_reason": selection_reason,
            "selected_info": redactor.clean(selected_info, "selected_symbol") if selected_info else None,
            "tick": redactor.clean(tick, "tick") if tick else None,
        }
        redaction = {
            "credentials_collected": False,
            "identifier_scheme": "Per-run HMAC-SHA-256 pseudonyms; secret key discarded and not included in evidence.",
            "stable_scope": "Stable only within this evidence run. Cross-run comparison requires manual broker/account review without exposing identifiers.",
            "removed_fields": sorted(REMOVE_KEYS) + ["account.name"],
            "pseudonymized_identifier_fields": sorted(SENSITIVE_ID_KEYS),
            "path_policy": "User-profile path component replaced with <REDACTED_USER>.",
        }
        provenance = {
            "source": "Connected MetaTrader 5 terminal and its configured Exness demo server",
            "receipt_host_utc": iso_utc(utc_now()),
            "package_verification": package_verification,
            "terminal_enforced_external_python_trading_block": True,
            "network_upload_performed": False,
            "limitations": [
                "Hashes establish file integrity, not truth or completeness of broker responses.",
                "MT5 data does not establish Exness legal entity, residence eligibility, or contractual permission.",
                "No order preflight, submission, modification, cancellation, close, subscription, or symbol-selection operation was called.",
            ],
        }

        write_json(output_dir, "RUN_SUMMARY.json", run_summary)
        write_json(output_dir, "ENVIRONMENT.json", environment)
        write_json(output_dir, "TERMINAL.json", terminal_evidence)
        write_json(output_dir, "ACCOUNT.json", account_evidence)
        write_json(output_dir, "AUTOMATION_PERMISSIONS.json", permissions)
        write_json(output_dir, "SYMBOLS.json", symbol_evidence)
        write_json(output_dir, "BARS.json", redactor.clean(bars, "bars"))
        write_json(output_dir, "TICKS.json", redactor.clean(tick_history, "ticks"))
        write_json(output_dir, "EXPOSURE.json", redactor.clean(exposure, "exposure"))
        write_json(output_dir, "CALCULATION_VECTORS.json", redactor.clean(calculations, "calculations"))
        write_json(output_dir, "REDACTION.json", redaction)
        write_json(output_dir, "PROVENANCE.json", provenance)
        manifest = write_evidence_manifest(output_dir)
        return {"summary": run_summary, "manifest": manifest}
    except Exception:
        if output_dir.exists() and not any(output_dir.iterdir()):
            output_dir.rmdir()
        raise
    finally:
        if initialized:
            api.shutdown()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only Phase 0 MT5 evidence collector")
    parser.add_argument("--output-root", type=Path, default=Path("evidence-output"))
    parser.add_argument("--symbol", help="Exact account-specific gold symbol, e.g. XAUUSDm")
    parser.add_argument("--bars-count", type=int, default=512, choices=range(100, 5001), metavar="100..5000")
    parser.add_argument("--ticks-count", type=int, default=2000, choices=range(100, 10001), metavar="100..10000")
    parser.add_argument("--history-days", type=int, default=7, choices=range(1, 31), metavar="1..30")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base = Path(__file__).resolve().parent
    package_verification = verify_package_manifest(base)
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    output_dir = output_root / f"xauusd-phase0-evidence-{timestamp}-{secrets.token_hex(4)}"
    try:
        result = collect_evidence(
            api=ReadOnlyMT5,
            output_dir=output_dir,
            requested_symbol=args.symbol,
            bars_count=args.bars_count,
            ticks_count=args.ticks_count,
            history_days=args.history_days,
            package_verification=package_verification,
        )
    except CollectionError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Collector failed safely: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    print(json.dumps({"output_directory": str(output_dir), "status": result["summary"]["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
