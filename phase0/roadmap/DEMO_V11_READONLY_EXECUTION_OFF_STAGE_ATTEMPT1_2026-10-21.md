# DEMO-ADMIT v1.1 read-only source — owner-reported VPS staging PASS

**Date recorded:** 2026-10-21. **Immutable classification:** `DEMO_V11_READONLY_STAGE_ATTEMPT1_PASS_EXECUTION_OFF_NO_CAPTURE`.

The operator supplied the complete Windows PowerShell 5.1 output following explicit approval for **ONE** attended execution-OFF stage. The operation completed with no error and all expected source hashes/disabled-state markers. This is **owner-reported console evidence**, NOT an independently authenticated inspection of the VPS disk. Approval has been consumed; **no repeated stage operation, deletion, overwrite, or reset is authorized**.

**Authoritative full exact output:** [PR28 stage PASS evidence](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/28#issuecomment-6302062782).

## Precisely observed artifacts

| Field | Value |
|---|---|
| PR28 exact sealed HEAD | `90c3e93330edeee58a0709a41e7393f7818f4ea8` |
| Production main unchanged | `2848c98940def262459fd89d5897c6f63dd6aadb` |
| Source-only Actions artifact ID | `12300205161` |
| Outer artifact SHA256 | `10115fb5bd412a1df2ec4a80cac7d4e563f3276df3fe29ab2e1dde42b7d3c264` |
| Inner sealed ZIP SHA256 | `987982e0a4585fe4c1283c5557d953162a1d0fcb0f4a62b0253b7488af13a938` |
| Inner manifest SHA256 | `b0abedcf7fd86dd93ee2ea959f279453bbf80f19d96de619a385f8799edf5b7f` |
| Owner-run stage-helper SHA256 | `eb0b241dcac4f53d77dc00b5306c31edfb480867184aedad66da5225276d5cca` |
| Number of checked components | `5`; owner output `V11_ALL_FIVE_COMPONENT_HASHES_VERIFIED` |
| Isolated VPS stage root | `C:\Users\Administrator\AppData\Local\XAUUSD-DEMO-V11-READONLY` |
| Stage result | `V11_EXECUTION_OFF_STAGED_NO_CAPTURE` |
| Stage marker | `EXECUTION_OFF__NO_CAPTURE_AUTHORIZED`, marker text `NO_CAPTURE_NO_BROKER_ACTIONS_NO_REAL_MONEY` |
| MT5 imported | `false` |
| Broker actions | `0` |
| Capture authorized | `false` |
| Final wrapper marker | `V11_EXECUTION_OFF_STAGE_VERIFIED__NO_MT5_NO_CAPTURE_NO_TRADING` |

The final native source CI remained green: demo-admit run `39499813422` Windows 66 PASS / Linux 65 PASS + 1 native Windows skip; records `39499813467` PASS; sealed source `39499813418` PASS. Historical intermediate Windows syntax FAIL `39496459205` remains immutable and distinct; final corrected staging evidence does **not** erase that history. The separate prior S2 demo canary failure/success stages, PCR3, Gate0 and main are untouched.

## Next separately authorized phase: PREPARE run registration before VPS capture

The run-record template `phase0/roadmap/DEMO_LIFECYCLE_V1_1_CAPTURE_WINDOW_TEMPLATE_2026-10-18.json` at immutable PR28 HEAD is **NOT** a run authorization. Do NOT change its `TEMPLATE_NOT_RUN_REGISTRATION` state in place, re-stage the package, or send a capture command before separate prospective owner approval. The actual future run should use a **new separate run-specific registration** with:
- exact qualifying contiguous 4-hour London/New York liquid-market UTC start/end, evidenced from current Exness XAUUSD schedule, verified DST, holiday/reopening exclusions, Event Guard health and major event UTC blackouts; independent source hashes committed **before** beginning capture;
- run-specific registered true-tick 1/5/30s match tolerance in integer milliseconds (0–1000; **not yet selected**), immutable matching algorithm and review/allowlist hashes; account-specific commission/swap USD provenance, no missing-as-zero;
- original sealed script/component hashes, GitHub source head, exact existing MT5 PID and path, admitted Exness DEMO account fingerprint `9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91`, zero positions and orders, external-Python trading disabled;
- new single-run ID/approval ID, read-only scope, separately explicit owner permission including acknowledgment that `mt5.initialize()` can have terminal side effects, precise local private `capture-YYYYMMDDTHHMMSSZ` destination, one capture attempt only, no automatic restart or retry; registration SHA256 and code/static allowlist SHA-256.

**Never invent those evidence fields from an absent live VPS observation or stale official broker schedule.** If a suitable 4-hour UTC period cannot be verified prospectively, **BLOCK**, not retrospective registration. The proof may be formed and audited owner-independently on GitHub first, but the owner must authorize any new MT5 attach/read-only broker/capture operation.

**Even after a 4-hour raw capture:** numerical `DEMO_LIFECYCLE_ONLY` costs are only candidates until independently verified, USD Policy A and historical period-risk ledger bound, one execution-disabled successor staged and DEMO-ADMIT PASS/FAIL separately adjudicated. No APC-DEMO trade authority and no real-money permission.
