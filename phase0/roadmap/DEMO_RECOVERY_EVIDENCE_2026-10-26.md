# October 26, 2026 — Owner-observed Exness DEMO recovery (sanitized)

**Classification:** owner-pasted VPS console output; sanitized public repository account of actual execution, not an independent GitHub Actions broker connection. No raw logs, secrets, actual account ID, account fingerprint or private SQLite contents were uploaded.

## Lineage and accepted scope

- **Before:** old Windows ForexVPS source `dfd193a4c9a6db00da81b806f2b160892eae30c9` was stopped; existing interactive Scheduled Task `XAUUSD Exness Pro DEMO Autonomous Trader` had been Ready and coordinator `QUARANTINED/SOURCE_OR_FEATURE_EXCEPTION` since October 25, 05:05:06 UTC. Root exception text was never preserved. The old execution recorded no broker submissions or receipts.
- **Corrective development:** [PR #41](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/41) merged as `b212715f8afad96a3af4edfdfb132681a4f74894` and allowed only three exact idle MT5 information/connection-unavailable errors to remain `NO_ORDER`; other account-identity, open-intent and known-position uncertainty cases still fail closed.
- **Attended recovery:** [PR #42](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/42) merged as `4bb27ff5ecae3d1e7dad0bd6e2354812a6a2c573` after native Windows PowerShell 5.1 AST and Windows/Linux Python offline suites passed. It was run with the exact merged Git commit under owner-attended confirmation on the **existing Windows Task Scheduler task**, with no new task, no LIVE approval and no forced order.

## Owner's successful execution evidence, 2026-10-26 UTC

| Evidence marker | Sanitized owner-observed output | Interpretation |
|---|---|---|
| Release pin | `APPROVED_SOURCE_PIN=4bb27ff5ecae3d1e7dad0bd6e2354812a6a2c573` | Exact reviewed GitHub release |
| Task and owner identity | `EXISTING_TASK_ONLY_AND_OWNER_SID_CONFIRMED` | Single same-user existing task |
| Dependency installation | Isolated Python 3.12 release, MetaTrader5 5.0.6090 and dependencies installed | New release staged; previous release left on disk |
| Dual-store recovery | `RECOVERY_CONTROL_AND_WATCHDOG_ACTIVE_BROKER_FLAT_NO_ORDER` | Both control gates active after fresh, exact DEMO flat-broker checks |
| Private backups | `RECOVERY_PRIVATE_BEFORE_STATE_BACKUP_VERIFIED` | Journals and historical incident evidence preserved locally |
| Same-task start | `EXISTING_DEMO_TASK_RESTART_REQUESTED_NO_SECOND_TASK` | Task start requested without creating another writer |
| Fresh heartbeat | `FRESH_HEALTH_UTC=2026-10-26T17:23:03.5989700Z` | Positive post-restart running `ACTIVE / NO_ORDER` |
| Initial strategy wait | `FRESH_STRATEGY_STATUS=WAIT_FOR_NEXT_COMPLETED_M15_BAR` | Valid idle-before-next-close state |
| Actual completed-M15 evaluation | `COMPLETED_M15_EVIDENCE_UTC=2026-10-26T17:30:05.1878490Z` | Observed new M15 result after restart |
| Specific strategy outcome | `TPB_DOWNTREND_STRUCTURE_NOT_CONFIRMED` | Deterministic TPB rejects setup; **NO_TRADE**, not a broker order or AI inference |
| Task after monitoring | `FINAL_TASK_STATE=Running` | Positive observation at end of attended script |
| Bar-processing status | `FRESH_M15_EVALUATION_EVIDENCED=True` | One actual completed-M15 assessment confirmed |
| Backup location | `%LOCALAPPDATA%/XAUUSD-DemoRecoveryEvidence/20261026T172126Z` | Private local vault path; never publish its contents |

The previously observed read-only DEMO broker probe at **2026-10-26 16:51 UTC** passed the pinned Exness DEMO fingerprint, showed no positions, no pending orders, no order/deal history since deployment, fresh XAUUSD tick and completed M15. The recovery procedure independently rechecked the same broker flat/identity/history/market gates **twice** before coordinator/watchdog mutation, evidenced by its successful exact guard completion.

## Outcome and limits

**RECOVERY PASS — owner-observed**: exact DEMO release updated on the same task, coordinator/watchdog rearmed, private before-state journals preserved, fresh heartbeat, one subsequent market M15 evaluation and `Running` task at the final observed point. No broker order was forced and no LIVE trading was authorized.

**Still outstanding:** subsequent 24–48h unattended uptime, first genuine technically qualifying TPB setup and OpenAI market approval, any broker order/pending receipt/fill, actual known-position management, delivered alert receipts, comprehensive future risk/fee and profitability review. The October 25 source exception was not logged precisely and remains historically **unknown**, not retrospectively proven transient. Do not restart or upgrade again merely to gather more M15 results; use read-only observation of the running task. The old quarantine evidence remains preserved in the current machine runtime record and the private recovery vault.

Canonical machine state: [CURRENT_DEMO_RUNTIME_STATUS.json](CURRENT_DEMO_RUNTIME_STATUS.json). Operational handoff: [DEMO_RUNTIME_HANDOFF_AND_NEXT_STEPS_2026-10-24.md](DEMO_RUNTIME_HANDOFF_AND_NEXT_STEPS_2026-10-24.md).
