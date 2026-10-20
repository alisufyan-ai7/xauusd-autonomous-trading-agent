# APC-DEMO-CANARY isolated execution-OFF VPS staging handoff (2026-10-20)

**Authority:** Owner approved exactly ONE attended **EXECUTION-OFF STAGING ONLY** step after the owner-run read-only Exness MT5 DEMO preflight PASS. This does NOT authorize broker attachment, order_check, order_send, demo/live orders, trade enablement, MT5 config/scheduler/PCR3/Gate0 mutations, shared worktree edits or PR merge.

## Immutable upstream artifact

- Production `main` `ccaa8338aecee8bd3afbc358644410dff6c512e5` unchanged; consolidated draft PR23 `e32f6dda35b2f29f2f5c0d762d0d26846bc5f384` unchanged/open/draft/unmerged.
- PR23 sealed CI [39454146632](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39454146632), GitHub Actions artifact ID `12278134974`, one outer GitHub ZIP (91,005 bytes) containing one inner `apc-demo-canary-e32f6dda35b2f29f2f5c0d762d0d26846bc5f384.zip`.
- Inner ZIP SHA256: `61535b668da13605d62a00517bc76cc6b4b918eab1db769b001e64b1bfa241a5`.
- Manifest SHA256: `03886c4afd8a2716f7c5d2d59aaa6fe535d4d5af0c97745da681c46839d4eed3`.
- Five exact verified manifest components: demo wheel `699b3a47c42bb57c875dfa1342a01546d68cd253de31a7af74d146c85d130980`, production risk wheel `2000b2ae1af7a0a252bb25d11ab19381c728310f6b3fe5b2b35b8b179abe89aa`, Python read-only preflight `484348e154e3072192b9a4b1fa8031b457355e6c46035bc1696ee22afcfabfc6`, PS5.1 read-only wrapper `11db0ba0877f29ddf62ff0b626dc060d80393176f79d97f7e8dca32f20154519`, attended operator `002f4ad5d3ed372026172b99a2dcfd6ca293196a2b9dfb0f1b6c7f2b503a776f`.
- Transport ZIP saved from original GitHub artifact and separately SHA verified locally. The transport hash is not used as an authority; the **inner ZIP + manifest/component bytes** are the fixed authority.

## Staging helper source

- `phase0/ops/apc-demo-canary-execution-off-stage.ps1` SHA256 `0400e2a339e90efb43125c65b27872cf8779b6630abb79c22ec917ab26272408`.
- Embedded Python source SHA256 `5d48dae4ea75e2a2268a8f8e5d15be156a23c47f5faf9cf7b826f754939e745a`.
- Reads owner-downloaded GitHub outer artifact from the supplied `-Artifact` path, rejects unexpected paths, size, inner SHA, manifest SHA, any of five component mismatches, all duplicates/traversal/symlinks, non-purelib wheel or reused staging root **before** writing.
- Creates ONLY new `%LOCALAPPDATA%\\XAUUSD-APC-DEMO-CANARY` under the attended Windows account; applies inheritable ACL limited to current SID, SYSTEM and Administrators using `icacls`. Unpacks pure Python wheels to isolated `site` path without `pip`, global Python install or system PATH modification; re-reads SHA from stored files.
- Creates and reopens `control.sqlite3` with `KILLED` default (no activation), and `canary.sqlite3` `UNUSED` via audited modules. Does not import `MetaTrader5`, start MT5, run broker APIs, create schedules, perform orders, change external Python trading configuration or run the canary operator. Writes `staging_evidence.json` to the isolated directory.
- The operator will require a future separately approved launcher that injects the isolated `site` path when the owner explicitly authorizes a bounded canary; the staging step does **not** produce a runnable CLI or broker permission.
- PowerShell wrapper validates its embedded Python source SHA before launching pinned `C:\Program Files\Python312\python.exe -B -I -`. Reports original terminal singleton/PID/path before and after (read-only), but does not attach to MT5. Refuses an existing stage directory, no auto-delete/retry.

## Offline preparation evidence and limitations

- Downloaded **actual** GitHub Actions artifact into isolated assistant container; validated one outer entry, six inner entries, SHA256 for inner and all five components.
- Performed local Python 3.13 **offline rehearsal** with the actual GitHub archive into a fresh disposable directory. It passed purelib wheel extraction (70 wheel files), re-hashing staged files, SQLite `KILLED` and `UNUSED` persistence, absence of MetaTrader5 imports, and rejection of an immediate second stage. This is **NOT** a Windows PowerShell 5.1/ACL live test. Those Windows-specific steps remain subject to the ONE attended owner execution.
- No VPS staging is claimed complete until owner sends full stdout including `APC_STAGE_SUCCESS_EXECUTION_OFF_NO_TRADING` and `APC_STAGE_VERIFIED__KILLED__UNUSED__MT5_UNTOUCHED`; any exception/missing marker is FAIL_CLOSED. Never silently retry, remove partial directory, re-enable trading or change PR23 artifact.
- Old R1/R2/A1 FAIL_CLOSED and A2 unexecuted, historical PRs #8–#22 remain immutable.

**Next only after owner stage PASS:** review current Exness DEMO account/exposure/quote, broker risk calculations and exact strategy side/protective stop, then seek separately bounded APC-DEMO-CANARY approval for at most one `0.01` lot XAUUSD demo position and one attended closure, mandatory risk and full KILLED after. Real-money stays off.
