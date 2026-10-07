# XAU/USD Phase 0 Read-Only Collector — Objective Verification Report

**Artifact:** `XAUUSD_Phase0_ReadOnly_Evidence_Collector_v0.1.1.zip`  
**Artifact SHA-256:** `3be08021c4d2c9e8206819e9e14838d5f811ac5a295422e4db501232700a1a59`  
**Verification date:** 2026-08-09 UTC  
**Verdict:** PASS for a Phase 0 read-only evidence run only  
**Gate 0:** INCOMPLETE  
**Production implementation:** Not started and not authorized

## 1. Read-only claim and enforcement layers

The artifact is accepted for the requested demo-account diagnostic because two independent barriers apply:

1. **Terminal-enforced barrier.** The collector reads only `terminal_info` after initialization and aborts before account, market, exposure, or history collection unless `tradeapi_disabled=true`. It checks the same flag again before completion. MetaQuotes states that Python scripts can perform trading operations only when **Disable automated trading via external Python API** is disabled; the collector requires that protection to be enabled.
2. **Capability-limited source.** The production adapter exposes only observation functions plus `order_calc_profit` and `order_calc_margin`. It contains no order submission, preflight, modification, cancellation, close, login, symbol-selection, order-book subscription, dynamic attribute lookup, shell/process, or network client call path.

The terminal barrier prevents external-Python trading even if a prohibited call were introduced. The source barrier ensures the verified artifact has no such call. Package-hash verification causes any modified production file to fail before collection.

## 2. Objective acceptance results

| Test | Result | Evidence |
|---|---|---|
| Python syntax/bytecode compilation | PASS | `collector.py`, adapter, verifier, and tests compiled without error. |
| AST forbidden-import/call scan | PASS | No forbidden call/import finding in production files. |
| Direct MetaTrader module isolation | PASS | `collector.py` does not import `MetaTrader5`; only the narrow adapter does. |
| Frozen MT5 attribute allow-list | PASS | Every adapter access matched the 28 recorded observation/calculation methods/constants/metadata fields; no additional MT5 attribute was found. |
| Fake-MT5 forbidden-operation traps | PASS | Traps for order submission, order preflight, login, and symbol selection were invoked zero times during a full synthetic capture. |
| Guard-off fail-safe | PASS | With `tradeapi_disabled=false`, collection raised a safe error before `account_info` was called. |
| Credential/identifier handling test | PASS | No credential input exists; synthetic account login became a per-run HMAC pseudonym, account name was removed, and the Windows user path was scrubbed. |
| Evidence integrity generation | PASS | Synthetic run generated canonical JSON and evidence manifests. |
| Complete binary dependency lock | PASS | Exact, hashed entries exist for `MetaTrader5==5.0.6090` and transitive `numpy==2.5.0`; source distributions are disabled; the runner checks installed versions. |
| Source package manifest | PASS | All seven manifested package files matched their recorded SHA-256 values. |
| Extracted ZIP re-verification | PASS | The final ZIP was extracted to a clean temporary directory; static, behavioral, and manifest checks all passed again. |

Behavioral test count: **3 passed, 0 failed**.

## 3. Frozen production call surface

The adapter accesses only:

`initialize`, `shutdown`, `last_error`, `version`, `terminal_info`, `account_info`, `symbols_get`, `symbol_info`, `symbol_info_tick`, `copy_rates_from_pos`, `copy_ticks_from`, `orders_get`, `positions_get`, `history_orders_get`, `history_deals_get`, `order_calc_profit`, and `order_calc_margin`, plus read-only timeframe/direction constants and package metadata.

The production source hashes are:

- `collector.py`: `a9c51b9b6b53c58043b04ef0f57722bc2dcf0d203100f63c3fc1c509dcbd1e26`
- `readonly_mt5.py`: `1b49f38463521ff1a6e17f2816020e0e0750c2296e6c50e5fa0551ab10e18fef`

The Windows dependencies are binary-only and pinned for 64-bit CPython 3.12: `MetaTrader5==5.0.6090` uses PyPI wheel SHA-256 `70601ae582a0d9a5b8e4d074b6f198ccf82a3172ced4c8eb4b47ad091f578a86`; `numpy==2.5.0` uses the CPython 3.12 Windows x86-64 wheel SHA-256 `6f2d6873e2940c860a309d21e25b1e69af6aaffdd80aa056b04c16380db1c4f2`.

Collector `v0.1.0` is not accepted for operator use. Its lock omitted NumPy, causing pip’s mandatory all-dependency pin/hash check to stop installation. `v0.1.1` corrects that packaging defect without expanding the production MT5 call surface.

## 4. Evidence and redaction behavior

The run records OS/Python/MT5 versions, terminal and account modes, EA/automation permission flags, gold-symbol candidates, selected-symbol contract fields, current/recent ticks, six bar timeframes and gap statistics, current exposure, seven-day order/deal history, and profit/margin calculation vectors.

It accepts no credential argument or file. Login and trading-record identifiers are HMAC-pseudonymized; account holder name, comments, credential-like fields, and Windows user-profile path components are removed. The per-run HMAC secret is discarded, so identifiers are stable only inside one evidence bundle. Output receives canonical JSON, individual file hashes, a manifest hash, and an archive hash. No upload is performed.

## 5. Limits that remain open

- The intended Windows VPS, Exness MT5 terminal, and demo account have not yet been observed. The live pre/post `tradeapi_disabled` values and broker facts remain pending.
- The PowerShell runner, remote wheel installation, and proprietary MT5 import could not be executed in this Linux verification environment; the exact archive’s Python verifier/test/package operations were executed directly and passed. The Windows install/import and terminal run are the next empirical evidence items.
- The proprietary MetaTrader5 wheel was hash-pinned but not reverse-engineered. The terminal-enforced protection flag is therefore mandatory.
- This collector cannot prove the Exness contracting entity, residency eligibility, client classification, or contractual permission for automated trading. Those require separate redacted documentary evidence.
- It cannot prove that another EA, script, manual operator, or service did not trade independently. Unrelated automation should be paused for a consistent snapshot.
- Passing this diagnostic proves neither strategy safety nor model safety, and it does not authorize any risk-changing operation.

## 6. Authoritative basis

- [MetaQuotes terminal information](https://www.mql5.com/en/docs/python_metatrader5/mt5terminalinfo_py)
- [MetaQuotes account information and EA permission flags](https://www.mql5.com/en/docs/python_metatrader5/mt5accountinfo_py)
- [MetaQuotes external Python trading protection](https://www.mql5.com/en/forum/53/page20)
- [Exness EA guidance](https://get.exness.help/hc/en-us/articles/360019530859-Using-Expert-Advisors-EA)
- [Exness account/instrument permission guidance](https://get.exness.help/hc/en-us/articles/360013352479--Trade-is-disabled-error)
- [Exness entities and regional restrictions](https://www.exness.com/regulation/)
- [MetaTrader5 package release and wheel hashes](https://pypi.org/project/MetaTrader5/)
- [NumPy 2.5.0 CPython 3.12 Windows wheel and hash](https://pypi.org/project/numpy/2.5.0/)
- [pip secure installs and all-dependency hash requirements](https://pip.pypa.io/en/stable/topics/secure-installs/)
