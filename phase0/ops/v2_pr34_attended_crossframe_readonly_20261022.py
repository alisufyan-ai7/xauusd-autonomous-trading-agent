"""Attended, source-pinned read-only Exness Pro DEMO aggregate parity diagnostic.

Does NOT verify official broker session calendar, trading or strategy P/L.
No raw candles, account IDs, secrets, login, tickets, orders or broker writes.
Never run automatically as a scheduler. The MT5 adapter fails unless the
exact admitted DEMO identity and Python trading DISABLED are confirmed.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from xauusd_agent.broker.v2_mt5_context_readonly import MT5ExtendedReadOnlyAdapter
from xauusd_agent.features.v2_chronology_audit import audit_seven_frame_chronology
from xauusd_agent.features.v2_crossframe_oracle import audit_crossframe_aggregates
from xauusd_agent.features.v2_market_context import ContextTimeframe

ADMITTED_DEMO_HASH = "9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91"
BROKER = "Exness Technologies Ltd"
SERVER = "Exness-MT5Trial15"

LIMITS = {
    ContextTimeframe.W1: 104,
    ContextTimeframe.D1: 180,
    ContextTimeframe.H4: 300,
    ContextTimeframe.H1: 500,
    ContextTimeframe.M15: 1000,
    ContextTimeframe.M5: 300,
    ContextTimeframe.M1: 300,
}


def inspect_readonly_crossframe() -> dict[str, object]:
    as_of = datetime.now(UTC)
    with MT5ExtendedReadOnlyAdapter(
        admitted_fingerprint_sha256=ADMITTED_DEMO_HASH,
        admitted_server=SERVER, admitted_company=BROKER,
    ) as adapter:
        adapter._guard_demo_identity()
        frames = adapter.read_seven_frames(as_of=as_of, limits=LIMITS)
        adapter._guard_demo_identity()
        cross = audit_crossframe_aggregates(frames=frames, as_of=as_of)
        # Full chronology cannot PASS until independently verified official
        # Exness market-hours/holiday/session source is admitted.
        full = audit_seven_frame_chronology(
            frames=frames, as_of=as_of, calendar=None
        )
        anchors = frames[ContextTimeframe.W1]
        sunday_anchor = all(
            bar.open_time.weekday() == 6
            and bar.open_time.hour == 0
            and bar.open_time.minute == 0
            for bar in anchors
        )
        gaps = {
            tf.value: sum(
                1 for a, b in zip(series, series[1:], strict=False)
                if b.open_time - a.open_time > tf.duration
            )
            for tf, series in frames.items()
        }
        complete = all(len(frames[tf]) == LIMITS[tf] for tf in ContextTimeframe)
        status = (
            "READ_ONLY_CROSSFRAME_PARITY_PASS_SESSION_UNVERIFIED"
            if cross.accepted and complete and sunday_anchor
            else "READ_ONLY_CROSSFRAME_OR_HISTORY_REJECTED"
        )
        return {
            "status": status,
            "symbol": "XAUUSD",
            "trade_mode": "DEMO",
            "broker": BROKER,
            "server": SERVER,
            "admitted_fingerprint_sha256": ADMITTED_DEMO_HASH,
            "external_python_trading_disabled": True,
            "execution_permitted": False,
            "order_api_calls": 0,
            "observed_utc": as_of.isoformat(),
            "crossframe_parity_accepted": cross.accepted,
            "crossframe_compared_parent_bars": cross.compared_parent_bars,
            "crossframe_reason_codes": list(cross.reasons),
            "w1_nominal_sunday_utc_open_observed": sunday_anchor,
            "timeframe_gap_counts_unclassified": gaps,
            "all_requested_bar_counts_available": complete,
            "official_broker_session_source_admitted": False,
            "full_chronology_admitted": full.accepted,
            "full_chronology_reason_codes": list(full.reasons),
            "broker_order_and_position_actions_authorized": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Execution-disabled XAUUSD causal parity probe")
    parser.add_argument("--confirm-readonly", action="store_true")
    args = parser.parse_args()
    if not args.confirm_readonly:
        print("NOT_EXECUTED_REQUIRE_CONFIRM_READONLY")
        return 2
    try:
        result = inspect_readonly_crossframe()
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL_CLOSED_READONLY_SOURCE",
            "error_type": type(exc).__name__,
            "order_api_calls": 0,
        }, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "READ_ONLY_CROSSFRAME_PARITY_PASS_SESSION_UNVERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
