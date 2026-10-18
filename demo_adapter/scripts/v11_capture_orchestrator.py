"""Inert/injected v1.1 read-only 4h capture orchestrator; no MT5 import.

OFFLINE REHEARSAL ONLY. A future explicit owner approval and independently
reviewed, source-hash-pinned Windows host binding are mandatory before
connecting a real MT5 terminal. This code never creates that binding.

All 4h slots are checked; a late or stale sample aborts instead of interpolating.
Runs through a *supplied* read-only port and *supplied* clock/sleep controller.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from scripts.v11_quote_coverage import (
    QuoteCoverageResult,
    QuoteSample,
    evaluate_quote_coverage,
)
from scripts.v11_readonly_collector import (
    CaptureSafetyError,
    ReadOnlyMT5Port,
    WindowContract,
    _identity_and_zero,
    _market,
)


@dataclass(frozen=True)
class CaptureEvidence:
    status: str
    observed_poll_count: int
    observed_tick_count: int
    polls_sha256: str
    ticks_sha256: str
    coverage: QuoteCoverageResult
    polls: tuple[QuoteSample, ...]
    ticks: tuple[QuoteSample, ...]


def _sha(samples: tuple[QuoteSample, ...]) -> str:
    payload = json.dumps([asdict(x) for x in samples],
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _utc_millis(t: datetime) -> int:
    if t.tzinfo is None or t.utcoffset() != timedelta(0):
        raise CaptureSafetyError("clock not UTC or unbounded")
    return int(t.astimezone(UTC).timestamp() * 1000)


def _quote_from_tick(tick: Any, *, stamp_ms: int) -> QuoteSample:
    try:
        # The eventual MT5 adapter must expose str(float) with provenance,
        # plus a raw tick-capture manifest. These strings alone are NOT proof
        # of instrument precision, exchange fills or account-specific USD.
        t = int(tick["time_msc"])
        bid = str(tick["bid"])
        ask = str(tick["ask"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CaptureSafetyError("invalid timestamped bid/ask tick") from exc
    if t < 1 or stamp_ms < 1:
        raise CaptureSafetyError("missing UTC tick timestamp")
    # Poll observations use observer UTC slot time and never impersonate a
    # broker tick time. Freshness of actual broker time must also pass.
    if stamp_ms - t < 0 or stamp_ms - t > 2000:
        raise CaptureSafetyError("stale/future broker tick")
    return QuoteSample(stamp_ms, bid, ask)


def rehearse_orchestrator(
    port: ReadOnlyMT5Port,
    contract: WindowContract,
    *,
    now_utc: Callable[[], datetime],
    sleep_seconds: Callable[[float], None],
    copy_ticks_all_flags: int,
) -> CaptureEvidence:
    """Deterministic injected-clock 4h data method; no real port provider here.

    Never call on a real port without independent owner approval. This
    routine is NOT a Windows executable, automatic scheduler or cost admission.
    """
    if copy_ticks_all_flags <= 0:
        raise CaptureSafetyError("explicit COPY_TICKS_ALL flags required")
    before = _identity_and_zero(port, contract.expected_identity_sha256)
    if before["external_python_trading"] != "DISABLED":
        raise CaptureSafetyError("trading disabled invariant")
    start = _utc_millis(contract.start_utc)
    end = _utc_millis(contract.end_utc)
    if end - start != 4 * 60 * 60 * 1000:
        raise CaptureSafetyError("capture window is not exact 4h")
    if _utc_millis(now_utc()) > start:
        raise CaptureSafetyError("cannot start after prospectively registered start")

    polls: list[QuoteSample] = []
    for i in range(2880):
        slot_ms = start + i * 5000
        current_ms = _utc_millis(now_utc())
        if current_ms < slot_ms:
            sleep_seconds((slot_ms - current_ms) / 1000)
        observed_ms = _utc_millis(now_utc())
        if observed_ms < slot_ms or observed_ms > slot_ms + 1000:
            raise CaptureSafetyError("missed nominal five-second polling slot")
        # Do not silently replace unknown broker trading disablement or
        # network disconnection with a positive preflight assumption.
        terminal = port.terminal_info()
        if (terminal is None or not isinstance(terminal, dict)
                or terminal.get("tradeapi_disabled") is not True
                or terminal.get("connected") is not True):
            raise CaptureSafetyError("terminal unexpectedly disconnected/tradable")
        tick = port.symbol_info_tick("XAUUSD")
        if tick is None:
            raise CaptureSafetyError("missing symbol tick")
        if hasattr(tick, "_asdict"):
            tick = tick._asdict()
        if not isinstance(tick, dict):
            raise CaptureSafetyError("unrecognized broker tick type")
        polls.append(_quote_from_tick(tick, stamp_ms=observed_ms))

    now_at_end = _utc_millis(now_utc())
    if now_at_end < end:
        sleep_seconds((end - now_at_end) / 1000)
    if _utc_millis(now_utc()) > end + 1000:
        raise CaptureSafetyError("post-window deadline missed")
    # Pre/post zero-exposure and unchanged symbol snapshot are required.
    _identity_and_zero(port, contract.expected_identity_sha256)
    _market(port)

    all_ticks: list[QuoteSample] = []
    for ten_min in range(24):
        chunk_start = contract.start_utc + timedelta(minutes=10 * ten_min)
        chunk_end = chunk_start + timedelta(minutes=10)
        observed = port.copy_ticks_range(
            "XAUUSD", chunk_start, chunk_end, copy_ticks_all_flags
        )
        if observed is None:
            raise CaptureSafetyError("missing true broker tick range")
        for entry in observed:
            try:
                stamp = int(entry["time_msc"])
                # Same-ms duplicates stay in the source and cause the
                # conservative coverage validator to reject ambiguity.
                bid = str(entry["bid"])
                ask = str(entry["ask"])
            except (TypeError, KeyError, ValueError) as exc:
                raise CaptureSafetyError("invalid raw broker tick") from exc
            if not start <= stamp < end:
                # end-inclusive MT5 range boundaries cannot be silently
                # rewritten or attributed to the next adjacent segment.
                raise CaptureSafetyError("tick at an unsupported chunk boundary")
            all_ticks.append(QuoteSample(stamp, bid, ask))
    _identity_and_zero(port, contract.expected_identity_sha256)

    coverage = evaluate_quote_coverage(
        contract.start_utc, contract.end_utc, polls, all_ticks
    )
    result_polls = tuple(polls)
    result_ticks = tuple(all_ticks)
    return CaptureEvidence(
        status="READ_ONLY_QUOTE_CAPTURE_NOT_COST_CALIBRATION",
        observed_poll_count=len(result_polls),
        observed_tick_count=len(result_ticks),
        polls_sha256=_sha(result_polls),
        ticks_sha256=_sha(result_ticks),
        coverage=coverage,
        polls=result_polls,
        ticks=result_ticks,
    )
