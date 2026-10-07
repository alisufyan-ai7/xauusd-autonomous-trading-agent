# Operational Policy Selection — Partial Gate 0 Freeze

**Decision:** D-0074  
**Status:** V1/M1/E1/P1/A1 accepted for specification and testing  
**Authorization:** no demo/live trading; external Python trading disabled

## Accepted controls

### V1 — volume cap

`strategy_volume_cap = min(0.01 lot, account_validated_cap)`.

The candidate volume must be on the current broker minimum/step grid, rounded
down, and must pass every cash-risk, margin, stop, cost and stress rule. If
0.01 lot is invalid or exceeds any limit, reject; the cap never creates an
entitlement to trade.

### E1 — emergency handling

Unexpected, conflicting, unknown, unprotected or policy-breaching exposure
blocks new risk, preserves evidence, triggers a critical alert and continues
read-only reconciliation. The system emits no cancel, modify or close request.
Only a human may decide a broker action after verifying identity and state.
Automatic closure of unknown exposure is prohibited.

### P1 — pause and resumption

No risk or safety pause clears automatically. After the trigger-specific hold,
complete reconciliation, required diagnostics, alert acknowledgement and fresh
preflight must all pass before a designated human creates a new authorization
epoch. Old proposals/intents remain expired and cannot be revived.

### A1 — alerts

All alerts enter the append-only local audit log. Critical alerts additionally
use `EMAIL` and `TELEGRAM_PUSH`, repeat every 5 minutes until acknowledged, and
require acknowledgement within 15 minutes during an execution window. Warnings
require acknowledgement within 4 hours; informational events enter a daily
digest. The sanitized acknowledgement role is
`OWNER_DESIGNATED_ACKNOWLEDGER`; personal routing data stays outside source
control. Channel failure must never restore or increase risk authority.

## M1 — margin reserve and stress

M1 is accepted under D-0075. Its deterministic rule is:

1. Projected margin level must be at least `1000%` and projected free margin
   must be at least `90%` of projected equity, under both current and stressed
   calculations.
2. The stressed calculation applies `2.0x` incremental margin and reduces
   projected equity by the frozen adverse spread, slippage, gap and cost stress.

The broker calculation and current verified account/symbol fingerprint remain
mandatory. Missing, stale, non-finite or ambiguous inputs produce `UNKNOWN` and
reject new risk. M1 is subordinate to every other Risk Governor limit;
satisfying it alone never authorizes a proposal or trade.

## Claim limit

This partial freeze authorizes only specification and deterministic testing. It
does not authorize implementation of broker calls, demo/live execution,
automatic emergency action, resumption, or enabling external Python trading.
