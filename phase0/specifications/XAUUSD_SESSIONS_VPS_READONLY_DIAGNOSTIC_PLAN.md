# XAUUSD Sessions and VPS Reliability — Read-Only Diagnostic Plan

**Status:** Phase 0 read-only diagnostic protocol frozen; runnable artifact and account/VPS run evidence pending  
**Version:** 1.0  
**Date:** 2026-08-11  
**Hard boundary:** Keep **Disable automated trading via external Python API** enabled. No order check/send, order change/cancel, position close, login/account switching, symbol selection, market-book subscription, or other risk-changing operation is permitted.

## 1. Objectives

Establish, for the fingerprinted Pro MT5 demo target and `XAUUSD`, (a) account-specific weekly sessions and exception behavior and (b) whether the Windows VPS/MT5/Python read-only observation stack remains coherent through time, disconnection, and restart. Results are point-in-time diagnostic evidence, not permanent real-account assumptions or trading authorization.

## 2. Safety controls before any run

Any diagnostic artifact must be separately versioned, hashed, statically allow-listed, behaviorally tested against a fake MT5 module with forbidden-operation traps, packaged with complete dependency hashes, and approved for the exact run. It must:

- abort before account/symbol reads unless `tradeapi_disabled=true`, and verify the flag remains true at the end;
- contain no dynamic dispatch or forbidden imports/calls;
- use an allow-list limited to terminal/account/symbol/tick/session/rates/orders/positions/deals reads needed by the plan;
- never accept credentials or perform `login`; the operator connects the already-running intended terminal;
- redact account number, names, paths, IPs, and other secrets from review output while hashing protected originals;
- record executable/source/config/dependency hashes and the terminal/account/symbol fingerprint;
- write append-only timestamped observations locally, with no OpenAI or other external transmission.

The package verifier must reject source or bytecode containing these MT5 capabilities (including aliases/wrappers): `initialize` with credentials or account switching, `login`, `order_check`, `order_send`, `orders_get` followed by any mutation path, position close, order modify/remove, `symbol_select`, market-book add/release, or terminal-setting changes. Read-only `initialize()` without credentials may be admitted solely to attach to the already-running terminal if static/runtime tests prove that it cannot switch accounts or enable trading; otherwise the operator must initialize the terminal manually and the collector must fail.

Runtime fake-module tests must expose every allowed function and trap every other attribute access, not merely known forbidden names. Network egress must be absent or OS-blocked except MT5 terminal IPC and separately approved clock checks; the artifact itself must not contact broker websites, OpenAI, telemetry, package registries, or update services.

## 3. Session evidence protocol

### 3.1 Evidence sources

Collect and reconcile:

1. account-specific MT5 `symbol_info` properties;
2. MT5 trade-session query for each weekday and all returned session indices;
3. timestamped tick availability and freshness observations around expected open/close/break boundaries;
4. applicable broker-published XAUUSD schedule and holiday notices captured with URL/version/date/hash where obtainable.

The authoritative runtime rule is the current account-specific terminal response plus healthy fresh-tick evidence. Generic website hours are corroboration, not an override.

### 3.2 Normalization

Store raw weekday/session index and raw returned times separately from interpretation. Normalize interpreted intervals to UTC with explicit source timezone, offset, IANA zone, and DST rule. Support intervals crossing midnight, multiple intervals per weekday, zero-duration/absent sessions, weekend closure, daily maintenance breaks, and exceptional holiday schedules. Never infer sessions from VPS local time.

### 3.3 Acceptance evidence

- seven-day raw and normalized weekly table;
- observations spanning at least one expected close and reopen plus any daily break visible during the 24-hour soak;
- explicit discrepancy report between terminal session API, fresh ticks, and broker publication;
- named unresolved exception policy: a missing/contradictory schedule fails closed;
- later real account must be probed independently.

## 4. Reliability observation matrix

All tests are non-trading; analysis and execution switches remain off.

| Test | Safe action | Required observation | Pass condition |
|---|---|---|---|
| 24-hour soak | Periodic allow-listed reads | terminal/connection/build, UTC clocks, account fingerprint, symbol properties, tick age, process resource health, errors | No identity drift; gaps classified; no stale data represented as fresh; protection flag always true |
| Temporary network failure | Operator/firewall or infrastructure-approved interruption; no broker call | disconnect detection, stale lock, bounded reconnect observation | System enters unhealthy/read-only state; no fabricated continuity; recovers identity before healthy |
| Python process restart | Restart diagnostic only | durable observation continuity and gap | Startup safety checks repeat; no execution capability; gap recorded |
| MT5 restart | Operator restarts terminal with trading disabled | loss/recovery of IPC, build/fingerprint/protection | Health remains failed until complete re-probe; changed identity/build flagged |
| Windows/VPS restart | Controlled restart | service start order, UTC sync, terminal readiness | No automatic execution enabling; full fingerprint/reconciliation reads precede healthy status |
| Clock drift | Compare UTC system clock to approved time sources and broker timestamps | offset, jump, monotonic continuity | Threshold breach marks timestamps/data unhealthy; no silent correction of evidence |
| Multiple terminals | Detect processes/install/data paths without exposing them publicly | ambiguity and selected terminal identity | More than one plausible terminal fails closed until operator resolves it |
| MT5 auto-update/build change | Observe build/version across cycle | changed binary/build and compatibility state | Change invalidates prior compatibility status and requires revalidation |
| Disk/log pressure | Safe synthetic diagnostic-log pressure only if separately approved | free space, write/fsync failure behavior | Recording failure makes health fail; evidence is not silently dropped |

Network interruption and restart actions can affect availability; they require an operator-approved window and must never be performed against a real or trading-enabled account in Phase 0.

## 5. Sampling and evidence format

Frozen initial sampling: health/tick observation every 5 seconds; account/symbol fingerprint every 60 seconds; session table at start, end, reconnect, and build/account/symbol change. During the ten minutes on each side of an expected session boundary, sample health/tick every second if the fake-module/load test and terminal observation show no instability. Missed deadlines are recorded as gaps; they are never backfilled. Any future interval change is versioned and requires re-verification.

Each record uses UTC ISO-8601 plus monotonic time, sequence number, prior-record hash, test/scenario ID, process/session boot IDs, protection flag, connection/health state, redacted fingerprint, tick broker time and receipt time, clock-offset estimate, build/version, error code/class, and raw protected evidence reference/hash. Manifest distinguishes physically packaged files from protected evidence referenced only by hash.

## 6. Failure and stop rules

Immediately stop collection and mark the run invalid if the external-Python protection flag is false, account/symbol fingerprint changes unexpectedly, static/runtime verifier fails, an unapproved MT5 method is invoked, output cannot be durably recorded, or a credential appears in output. Disconnect, stale tick, schedule disagreement, multiple-terminal ambiguity, clock drift, or build change are diagnostic findings and make health fail closed; they do not justify any corrective trading action.

## 7. Package verification and acceptance contract

Before the owner is asked to run anything, a release directory must contain source, locked dependency manifest, configuration schema, allow-list, generated forbidden-call inventory, fake-MT5 tests, redaction tests, hash-chain tests, restart tests, static-verifier report, test report, operator instructions, and SHA-256 manifest. The release archive hash and every included file hash are immutable. Protected outputs are not placed in GitHub; GitHub stores only redacted reports and hashes under the evidence policy.

Minimum pre-run acceptance is all tests passing with:

1. zero reachable risk-changing or account-switching calls;
2. every non-allow-listed MT5 attribute trapped by the fake module;
3. startup and shutdown both prove the external-Python protection flag is true;
4. intentional credential/account/path/IP fixtures are redacted while protected originals hash consistently;
5. interruption at every write point yields either a valid prior record or an explicitly invalid tail, never a silently valid altered chain;
6. attach failure, terminal loss, stale tick, account/build/symbol drift, clock breach, disk failure, and multiple-terminal ambiguity all fail health closed;
7. the package performs no trading, configuration mutation, account switching, symbol selection, market-book subscription, or external analytical transmission.

The account/VPS evidence phase passes only after an operator-approved run produces: a complete 24-hour soak; a weekly session table; at least one observed relevant close/reopen or daily break (extend beyond 24 hours if needed); the approved restart/network scenarios; no safety-boundary violation; and a signed/redacted findings report with raw evidence hashes. A 24-hour run that does not cross a boundary is useful reliability evidence but does not close the session objective.

## 8. Remaining diagnostics/research

- Exact account-specific weekly sessions and holiday exception source have not yet been captured.
- Soak duration beyond the minimum 24 hours and event/weekend boundary coverage may be required after initial evidence.
- Clock source, drift warning/failure thresholds, sampling rate, reconnect timeout, and monitoring SLA require selection.
- Approved safe method for network interruption and Windows/MT5 restart on the VPS requires an operator window.
- Multiple-terminal discovery and path redaction need objective verification in the new collector.
- MT5 auto-update control/rollback and Windows patch policy need operational decisions.
- Any future real account needs a new fingerprinted probe before use.

