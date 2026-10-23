# Incident — corrected comprehensive Exness DEMO read-only collector failed closed (2026-10-23)


## 2026-10-23 follow-up — owner PRIVATE file inventory received and original hash independently reproduced

**Exact operator inventory for the original corrected run** under private `%LOCALAPPDATA%\\XAUUSD-BrokerEvidence\\capture-20261023T122721Z-5a5a5665d8b64f6591c30bd7f46a77bd`:

| Private artifact basename | Exists | Bytes |
|---|---|---:|
| `failure.json` | YES | 185 |
| `past_four_hour_broker_ticks.jsonl` | YES | 0 |
| `static_evidence.json` | NO | — |
| `prospective_run_registration.json` | NO | — |
| `prospective_quote_samples.jsonl` | NO | — |
| `prospective_broker_ticks.jsonl` | NO | — |
| `complete_evidence.json` | NO | — |
| `shareable_summary.json` | NO | — |

The operator supplied `failure.json` SHA-256 **`83292117FAA298CB527459D02CA23C91558F166238AECE98CC2AC5E6F3BCA728`**. Independently reconstructed the **exact 185-byte UTF-8 JSON plus terminal LF** from the pinned collector's constant serialized failure object; independently computed SHA-256 is **identical**. This *proves* the persisted failure contains only the console's six generic fields, not a hidden exception reason; the user need not reveal raw `failure.json`.

**New causal localization, source-order grounded:** `mt5.initialize()` returned success and the unique private capture directory and historical-tick output handle were created. Otherwise this pinned `run()` could not have reached the zero-byte `past_four_hour_broker_ticks.jsonl` file. The caller entered the `collect_static` path and raised `DemoSafetyError` before writing any valid historical tick row and before completing/sealing `static_evidence.json`. This does **not** establish that identity, flat exposure, quote/spec, broker math, history or bars passed; any of those, or the first tick/empty tick read, could reject. No prospective registration or five-second sample was started. Empty tick file means **no preserved historical tick**, not proof `copy_ticks_range()` was necessarily called.

**Result:** `STATIC_COLLECTION_FAIL_CLOSED_AFTER_MT5_INITIALIZE__EXACT_GUARD_UNKNOWN`. Do not claim the original capture reached or completed four hours or that Exness rejected an order; all order APIs remain reported 0.

### One prospective source-specific diagnostic, NO four-hour rerun

Since the existing failure file and tick file cannot identify the guard, one *optional attended STATIC-ONLY replay* against the same read-only MT5 source is prepared on PR40:
`phase0/ops/pr40_existing_failure_static_stage_only_20261023.ps1`. It is pinned to exact prior corrected collector/test source `723e276ca32f80e6b705c8dd087a4325609c59e5`, exports its Git archive without VPS checkout, runs isolated preflight, then calls **the same collector without `--prospective-four-hours`**. One prompt for explicit operator consent; no timer-based four-hour observation, order check/send, terminal login/permission/scheduler change. The diagnostic uses fixed enum-like `failure_stage` and exact fixed `safe_guard_code` allowlists: no raw exception string, account/login/history/ticket leaks. It stores new evidence in a unique private local directory and emits only sanitized outcomes/hashes. New source/tests exercise known reasons and unknown/redacted private strings. It remains **prepared only**, no operator run performed; source CI approval must be checked before owner action.

A static replay examines *current* MT5 safety state; even if it identifies a guard now, **do not retroactively assert the same transient reason was responsible for the earlier captured failure** without evidence. A fully successful static replay is still not a qualified v1.1 cost source, no completed prospective window, and no broker-order admission. No blanket repeated diagnostics; inspect the single result before further action.


**Evidence status:** `FAIL_CLOSED_NO_ORDER`. This is the **second, corrected launcher attempt**, distinct from [the immutable earlier missing-import incident](MT5_SINGLE_CAPTURE_IMPORT_FAILURE_2026-10-23.md). Its internal safety reason is **UNKNOWN** from the available transcript. Do not reinterpret a successful import preflight as completed MT5, account, monetary or four-hour evidence.

## Owner-provided sanitized console proof

- Windows ForexVPS executed an approved exact GitHub checkout-free `git show` of the canonical PowerShell launcher from PR40 source `a68063d22fa28c04f9c1f505dd3821af15a5e814`, with verified PR branch ancestry. The launcher fetched but did not check out the VPS worktree.
- `PINNED_LOCAL_IMPORT_PREFLIGHT_PASS_NO_MT5` — **PASS**, fixes the first attempt's `ModuleNotFoundError`.
- `READONLY_SOURCE_PIN=10425e6180ef660226e298ef06a0fa423334332e` — exact corrected Python source.
- `REAL_EXNESS_PRO_MT5_DEMO_ACCOUNT__READ_ONLY` and `ONE_FOUR_HOUR_RUN__5_SECOND_SAMPLES__NO_ORDERS` are **launcher banners**, **NOT actual broker/DEMO/four-hour acceptance evidence**.
- `PRIVATE_LOCAL_EVIDENCE_DIR=` was printed with a unique private path under `%LOCALAPPDATA%\\XAUUSD-BrokerEvidence\\capture-*`. **Printing the planned path does not prove directory creation**.
- Collector returned exactly `{"error_type":"DemoSafetyError","no_retry_without_source_review":true,"order_check_calls":0,"order_send_calls":0,"output_location":"PRIVATE_LOCAL_ONLY","status":"FAIL_CLOSED_NO_ORDER"}`, followed by PowerShell `COMPREHENSIVE_MT5_CAPTURE_FAIL_CLOSED__NO_ORDER`.
- There was **no** `SANITIZED_SUMMARY_SHA256`, `READONLY_EVIDENCE_DONE_NOT_ORDER_ADMISSION` or shareable completion JSON in the console. The supplied transcript does not state an end timestamp or prove whether any partial private files exist.

## Admitted/unknown disposition

| Gate | Disposition |
| --- | --- |
| Git source ancestry, canonical launcher, Python isolated import path | **PASS** |
| Actual MT5 initialize, connected terminal, DEMO fingerprint, external Python trading disabled | **UNKNOWN FROM OUTPUT** |
| Global zero exposure, dynamic symbol contract and quote freshness | **UNKNOWN FROM OUTPUT** |
| `order_calc_profit` and `order_calc_margin` for BUY/SELL 0.01 lot | **UNKNOWN FROM OUTPUT** |
| Deal/fee/swap history, seven timeframe bars and past four-hour ticks | **UNKNOWN FROM OUTPUT** |
| Prospective registration/5s quote samples and 2,880-slot four-hour completion | **NOT PROVEN; NO ADMISSIBLE CAPTURE** |
| Complete shareable summary and its SHA256 | **NOT PRESENT IN CONSOLE; NO VERIFIED COMPLETION** |
| `order_check` / `order_send` | **REPORTED 0**, also excluded by audited read-only surface |
| Policy A numeric all-cost calibration, official Event Guard, first real broker DEMO order | **NOT ADMITTED** |

## Demonstrated software observability defect, same PR40 correction

At the exact run-time source pin `10425e6180ef660226e298ef06a0fa423334332e`, the collector catches `Exception` and intentionally redacts `str(exc)`, **but also discards the failing stage**, outputting only `DemoSafetyError`. Its original `failure.json`, if created, repeats the same generic failure metadata and therefore cannot reveal the exact guard. `static_evidence.json` is written only once **all** static reads complete; an early static failure can leave only an empty/partial historic tick file. The genuine cause is **not yet recoverable from the sanitized console**. We must not invent a broker connection or assume a particular source deficiency.

PR40 follow-on **diagnostic-only, fail-closed source change** adds fixed enum-like stage labels from module import → initialization → individual static checks → prospective sampling → seal, plus booleans for private static evidence and prospective registration presence. No raw exception string, private login, order/deal IDs, or direct MT5 trade API is exposed. Two adversarial regression tests exercise early account rejection and a late failure after static/private registration, including privacy and no-order assertions. The previously invoked source remains an immutable prior SHA; **the PowerShell launcher still pins the previous reviewed collector and is NOT authorized for a repeat**. Future pin changes require reviewed CI and an identified source-specific reason.

## Existing evidence handling and next single owner action

Only inspect **already preserved** local files, without invoking MT5, Python broker APIs or a fresh four-hour attempt. Safe names of interest inside the original private capture directory are `failure.json`, `static_evidence.json`, `prospective_run_registration.json`, `prospective_quote_samples.jsonl`, `past_four_hour_broker_ticks.jsonl`, `prospective_broker_ticks.jsonl`, `complete_evidence.json`, and `shareable_summary.json`. Report only their existence/size, *optional sample-row count*, and hashes, **not raw ticks or broker history**. If nothing was written or no stage metadata exists, the actual guard remains indeterminate and requires a separately reviewed targeted source-specific diagnostic correction before any new broker action. A bare rerun cannot be justified by this evidence.

**No trading permission:** retain S2 `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED`, incomplete Gate0 and accepted `GOVERNANCE.md` rule 7; no real Exness DEMO order, activation, merge, setting change, LIVE trading or other source admission was established.
