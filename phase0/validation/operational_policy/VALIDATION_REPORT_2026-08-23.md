# Operational Policy Offline Validation Report

**Recorded:** 2026-08-23 UTC  
**Decision:** D-0075  
**Result:** PASS — 15/15 tests  
**Authorization:** specification/testing only; no trading

Command executed from the repository root:

```text
python -m unittest -v phase0.validation.operational_policy.test_operational_policy
```

Verified behavior:

- V1 accepts the exact 0.01-lot boundary only when it is valid on the current
  broker grid and every other limit can still pass;
- M1 applies 1000% margin-level and 90% free-margin thresholds to current and
  stressed states, uses 2.0x incremental margin, subtracts all four required
  adverse equity stresses and rejects invalid inputs;
- an M1/V1 pass cannot override any other Risk Governor failure and is labeled
  as non-trading policy-test evidence;
- E1 emits no cancel, modify or close request and never closes unknown exposure;
- P1 requires every human/hold/reconciliation/diagnostic/ack/preflight/new-epoch
  prerequisite;
- A1 uses email plus Telegram push, five-minute critical repeats and a 15-minute
  acknowledgement boundary;
- static inspection finds no MT5, broker, network, messaging, credential or
  process-control capability.

One pre-acceptance test fixture was corrected transparently: `0.009` is valid
on the synthetic `0.005 + n*0.002` grid, so the intended off-grid fixture was
changed to `0.008`. The corrected suite passes 15/15.

This is an offline oracle, not account-specific margin evidence, message-channel
delivery evidence, an MT5 implementation, profitability evidence or trading
authorization. External Python trading remains disabled.

The existing Event Guard, setup/execution, raw-OHLC feature, VPS reliability,
Risk Governor/Analyst and replay suites were also rerun from their documented
directories. Together with this oracle, 93/93 test methods passed. An initial
root-level combined invocation produced three import-path errors in suites that
use directory-local imports; rerunning those unchanged suites from their
intended directories passed 21/21, 26/26 and 1/1 respectively.
