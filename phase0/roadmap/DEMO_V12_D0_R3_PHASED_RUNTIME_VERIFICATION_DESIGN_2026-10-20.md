# D0-R3 prospective isolated recovery — design and approval gates, 2026-10-20

**STATUS: REGISTRATION PREPARED / NO PHASE APPROVED / NO VPS RUN / NO D0 BROKER ATTACH.** This is a prospective engineering design, not a live authorization. New draft PR is stacked directly on PR20 `f255f59b401310a5acf2b3b0fc6169ac5635acc9`. No PR merge or shared runtime change.

## Observed reason for new preparation

The approved PR20 static survey on 2026-10-20 at 14:22:43Z reported existing **system** `C:\Program Files\Python312\python.exe` (not a venv) with `MetaTrader5` package dir and dist-info seen on disk. One existing terminal64: PID **6216**, exact EXE `C:\Program Files\MetaTrader 5\terminal64.exe`. See `phase0/roadmap/DEMO_V12_D0_R2_STATIC_VPS_SURVEY_OWNER_REPORTED_2026-10-20.md` for original selected console lines and epistemic limits. This literal system executable was NOT in R2's limited candidate set. It remains a candidate, not proof Python 3.12 actually runs or imports MetaTrader5.

R1 frozen SHA `ab1c266290f3c38f5b8e08bd44b0b06645c0e496839b7c9fa47fd4581f9d0534`, FAIL_CLOSED at reserved PS `$Host`; R2 frozen SHA `13c1ece5068a18b04512776a7387615c51c7075bd9df850d7e4415f6cd773c61`, FAIL_CLOSED at narrow runtime locator. Both authorization budgets consumed; both original registrations, scripts, private stages, and owner logs unchanged; NEVER retry them.

## Prospective registration and code

- R3 registration: `phase0/roadmap/DEMO_V12_D0_R3_PROSPECTIVE_NONEXECUTABLE_REGISTRATION_2026-10-20.json`, *new source bytes with their own SHA pinned in PR metadata after commit*, distinct from both R1 and R2. Status `DESIGN_ONLY__NOT_AUTHORIZED_NOT_EXECUTED__NO_ACTIVATION`, one-attempt-per-R3-broker-registration if later used, no R3 attempt created/consumed.
- Phase verifier: `demo_adapter/scripts/v12-d0-r3-phased-runtime-verifier.ps1`, SHA pinned only after final GitHub source validation. It contains no MT5 initialization or broker read path, order API, Git, installation or task changes.
- No D0-R3 MT5-inventory/attach launcher is provided in this PR. A future separate, uniquely approved and reviewed attachment package may reuse only vetted, source-identical existing read-only wrapper/host/journal **if separately authorized**; it must not reuse R1/R2 stage or registrations.
- Local stdout is owner-reported and not cryptographically attested, so future approval must verify exact branch HEAD and source SHA, and the owner must return whole terminal transcript for each phase before the next owner request.

## Four **separate** owner gates

| Gate | Purpose | Proposed operation | Pass evidence | Authorization |
|---|---|---|---|---|
| **A VERSION_ONLY** | Establish the exact pinned candidate *really runs Python 3.12* | One attended `C:\Program Files\Python312\python.exe -B -I -c` running only `sys,os`; verify version and executable identity; no MT5 import | Version 3.12 + exact `sys.executable`, clean exit | **NEXT ONLY APPROVAL** separately request after CI. Not approved by GitHub preparation. |
| **B IMPORT_ONLY** | Establish exact interpreter can import MetaTrader5 and read distribution version | Independent attended `-B -I -c` using `import MetaTrader5 as mt5` and metadata version; no MT5 API calls | Import exit zero and nonempty package version, exact interpreter/version | Requires **completed A PASS** plus new explicit owner B approval; import could trigger module-specific side effects, not assumed perfectly inert |
| **C TERMINAL_ONLY** | Re-evaluate exact running terminal process | PowerShell `Get-Process terminal64`; require count = 1, PID = 6216, exact EXE | Exact contemporaneous PID/path/count (if PID changed: FAIL_CLOSED, new design) | Requires **completed B PASS** plus separate explicit owner C approval |
| **D FUTURE D0-R3 MT5 ATTACH** | One supervised read-only broker metadata inventory, **not** four-hour admission | Separately engineered isolated source delivery, source/authentication/zero-exposure checks, `initialize(existing)` only if separately approved | Future private raw/journal and source bounds; no order APIs | **No approval and no launcher exists now**. Must recheck all previous facts and obtain separate exact HEAD+registration+code SHA owner approval; `initialize()` can activate/spawn terminal even with checks |

Gate A/B/C use the same PS5.1 `-Phase` argument but **no automatic chaining**. A run must be approved by the owner for that **one gate only**, and its exact `OwnerApprovalCode` is a defense-in-depth software guard, **not proof of authorization**. The `-ShellOnlyTest` branch is intentionally safe for GitHub Actions: it never invokes Python, MetaTrader5, Git, broker or windows system mutations. The independent mandatory owner boundary remains outside the code.

## Fail-closed technical details

- Explicit literal Python path: `C:\Program Files\Python312\python.exe`, **not** PATH/first Python selection or heuristic fallback. Missing executable, wrong `sys.executable` or version, missing/incompatible MT5 import, missing/unexpected terminal singleton/PID/path, or non-zero process exit => hard failure; **no fallback to another runtime**, no auto-retry.
- Interpreter version-only uses `-B -I`. Import-only uses same, reads `MetaTrader5.__version__` if provided and standard package distribution metadata, but never calls any MT5 function. Python process launch and package import require explicit separate owner approvals, even if isolated to commands above; `-B` suppresses Python bytecode writes but cannot guarantee third-party import has zero side effects. Do not claim import provides broker authorization.
- Terminal identity verified from OS process at its phase, point in time; D must reverify before/after attach and ensure external-Python trading is DISABLED and exposures flat. PID continuity is a conservative protocol constraint rather than proof of untouched MT5.
- Any phase failure must be preserved as a new prospective phase-specific failed observation and no phase may be misreported PASS. A/B/C do not consume R3 D0 broker-attachment attempt budget; if D is eventually approved its new private journal exclusive-create and one attempt limit apply.
- D0 one-snapshot broker inventory **never counts** toward v1.2 240-minute evidence; no date-specific Exness/event source/Guard session admission, price/cash-risk calibration, activation or trading grant. Risk Policy A adapter quarantine remains before order APIs. E1 human-only and P1 human-gated controls unchanged.
- No scripts touch shared VPS worktree, PCR3, Gate0, SignalProof/VowSig/TradingTop/Windows tasks, broker settings or orders. No VPS access has occurred during this GitHub-only PR work.

## Required future verification and stop

Offline tests must check distinct immutable registration, exact explicit path, token gating, no broker/mutation calls and native **Windows PS5.1 parser + ShellOnlyTest**; Linux static tests skip Windows-only shell execution. A successful CI build is **not** Python/MT5 runtime evidence from VPS.

**Next owner request should be ONLY Gate A VERSION_ONLY** following CI, with source SHA and exact PR HEAD, an attended single-paste read-only version report (will execute pinned Python) and full stdout. It is NOT included in the current owner approval and must not be pre-executed.
