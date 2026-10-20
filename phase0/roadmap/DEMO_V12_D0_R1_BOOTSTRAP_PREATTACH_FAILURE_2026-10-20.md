# D0 bootstrap failure — immutable incident D0-P0 (20 Oct 2026)

**Outcome: PRE-ATTACH FAIL_CLOSED.** No successful D0 diagnostic evidence; no qualifying v1.2 observation; no trading permissions.

## Reconciliation and owner authorization

Production `main ccaa8338aecee8bd3afbc358644410dff6c512e5` and approved draft PR18 HEAD `3ff100189349ada29331730af99459fecc4ea821` were independently rechecked after the VPS output; approved PR13 and sealed PCR3 are unchanged. Owner approved **one attended D0** for prospective registration SHA256 `ab1c266290f3c38f5b8e08bd44b0b06645c0e496839b7c9fa47fd4581f9d0534`, wrapper SHA256 `adc226a7d21ca7eb296f100ad0a6c79d9554c76ca15ca260c3c82959f0312274`, host `ea1496f715a6601f47098ee15a9d09645dc804a63ab9248fa60a4d36d3f52260`, journal `547131361b690e95c6718734b6de727e812346e92af8c1a20ced4f6dbc12ef06`. The **unreviewed supplemental inline staging bootstrap** was provided in chat, not a pinned GitHub file. Its PowerShell automatic-variable collision is an assistant-introduced error; DO NOT blame broker or user's environment.

## Real VPS stdout/error as owner-supplied (not independently authenticated broker data)

From owner-shared `Pasted text(20261020-125238).txt`:
- PowerShell prompt: `C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent`.
- First bootstrap artifact proof SHA256 `914ae74caef38bd3a3b6f08cc9d18e8eaae161457d3d2a6f572ffd529f8d887b` (claimed `ISOLATED_STAGE_RESERVED__ONE_ATTEMPT`, see actual file to verify).
- Second bootstrap artifact proof SHA256 `1dac09c21c5ed2f7112d09abe662a7531d794f0189e254bfb9d6af2488a7f9a3` (claimed `EXACT_GITHUB_HEAD_AND_FOUR_RAW_SOURCE_SHA256_PASSED`, see actual file to verify).
- `D0_FAILED_OR_NOT_STARTED=SessionStateUnauthorizedAccessException`; `Cannot overwrite variable Host because it is read-only or constant.` at inline bootstrap line **127**, assignment `$Host = Join-Path $SourceRoot 'scripts\v12_d0_readonly_inventory.py'`.
- Preserved on VPS: `%LOCALAPPDATA%\XAUUSD-v12-D0-IsolatedStage\ab1c266290f3c38f5b8e08bd44b0b06645c0e496839b7c9fa47fd4581f9d0534`. The full absolute Windows location and source checkout were printed.
- Neither `EXISTING_PYTHON_PATH` nor `EXISTING_TERMINAL_PATH`, `PRIVATE_RAW_SHA256`, `PRIVATE_JOURNAL_SHA256` nor `D0_RAW_DIAGNOSTIC_RESULT_JSON` appeared. The wrapper invocation was *after* the failing assignment. So **no Python preflight, no MT5 initialize/attach, no broker read, no D0 private directory or journal creation is demonstrated**; actual VPS disk/process state is not independently verified by this log alone.
- The exact four GitHub files were fetched/checksummed before line 127; wrapper and host have NOT been invoked. The echo message `D0_FAILED_OR_NOT_STARTED` is **bootstrap** failure, not broker/MT5 result.

**Causal defect:** PowerShell automatic variable `$Host` is case-insensitive, read-only. Using it as an ordinary variable in the long inline bootstrap caused an early runtime exception. Windows PowerShell parser accepts the syntax; native parser-only testing of the pinned wrapper did **not** test this added bootstrap. Prevent recurrence with immutable, GitHub-reviewed bootstrap source and native **actual execution** of its pre-MT5 preflight path on Windows Actions, plus AST assignment/static regression.

## Quarantine and retry policy

- Existing GitHub PR18 registration `ab1c...0534` remains historically **APPROVED_ONCE / BOOTSTRAP_PRE-ATTACH FAIL_CLOSED**. Do not edit/overwrite its preregistration, alter its original source pins, erase original stdout, delete stage, or invoke it again under the same registration.
- A new **separately prospectively versioned** D0-R2 registration/source package with a **different registration SHA** and fresh **explicit exact-head owner approval** is required before any further VPS D0 MT5 attach. Approval of the old R1 does not carry forward.
- If the owner wants zero-attach evidence review first, only inspect existing stage/proof files with read-only PowerShell commands that perform **no writes, no Git fetch, no Python/MT5 import, no D0 attempt**, and ask them to return hashes/status. This is not a second D0 attempt.
- A source digest match or a PASS on GitHub Actions does not prove broker/account/session authenticity or D0 execution. Frozen v1.2 four-hour capture remains unexecutable; no Event Guard or cost calibration admission, no external Python trading enablement, broker/order actions, scheduled-task/PCR3 edits, shared worktree changes, or PR merges are authorized.

**Status:** PRESERVE PRE-ATTACH FAILURE; prospective engineering/tests on child draft branch only. No current permission for a second D0 attempt.
