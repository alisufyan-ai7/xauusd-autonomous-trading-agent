# 2026-10-21 XAUUSD v1.1 owner-attended launcher — pre-marker fail-closed

**Classification:** `OCT21_V11_ATTESTATION_PRE_MARKER_FAIL_CLOSED__NO_CAPTURE`. New immutable observation, not a successful four-hour calibration.

## Provenance and scope

- Owner supplied original Windows PowerShell 5.1 screenshot of invoking `C:\Users\Administrator\Downloads\demo_v11_oct21_approved_run\demo_v11_oct21_ATTENDED_READONLY_CAPTURE.ps1` on Oct21 around 12:25 UTC, followed by read-only diagnostic stdout.
- The exact original wrapper SHA256 was reverified by owner's `Get-FileHash` result: `172c362232481766a281bf503e99519f5e4ccf1baa91124ca234054d05475960`. This matches the previously authorized wrapper; no corrected wrapper substituted.
- Console screenshot: `V11_EXACT_HASHES_PERMIT_EXISTING_TERMINAL_STAGE_VERIFIED`; prompt visibly echoed `ELIGIBLE`; immediate `V11_OWNER_DID_NOT_ATTEST_LIVE_EVENT_HOLIDAY_SHOCK_HEALTH` at line 77.
- Owner's *subsequent OS-only diagnostic*, no MT5 imports/broker calls, revealed original line 76 `$Answer = Read-Host ...`; line 77 exact case-sensitive `if ($Answer -cne 'ELIGIBLE') { throw ... }`; line 78 subsequent UTC gate; line 82 `FileMode::CreateNew` attempt marker; line 90 `& $Script ...` collector invocation.
- Diagnostic file search in owner prepared package folder and `C:\Users\Administrator\AppData\Local\XAUUSD-DEMO-V11-READONLY` returned only pre-existing `source-manifest.json` (1102 bytes; 2026-10-20T21:35:16Z). The diagnostic did not show the exact `$AttemptMarker` definition, and search was limited to those paths/names.
- The same OS-only diagnostic terminated `READ_ONLY_DIAGNOSTIC_COMPLETE`. Owner-supplied text is the basis; independent live VPS authentication/broker reconciliation **not performed** by assistant.

## Supported result and uncertainty

The operator initiated the one-time approved wrapper, but execution halted at its owner-attestation check. Because line 77 threw before lines 82/90, **that visible execution path never created its attempt marker and never invoked the collector**. No broker reads, tick observations or commission/swap capture are established by this evidence; current MT5 exposure/market-source health remain **UNKNOWN**, not presumed safe or flat.

The visible input appeared as `ELIGIBLE`, but `-cne` evaluated true. **Root cause is UNDETERMINED**: potential invisible input/extra characters, input capture issue, or unexpected validation behavior. This is *not* evidence that official source health actually failed, and *not* evidence that live source health passed. Native PowerShell AST parsing previously passed but did not behaviorally test the interactive `Read-Host` path.

## Non-negotiable continuation

- **NO retry** or wrapper modification/re-extraction under Oct21 approval; the one-time launch procedure was already invoked and Oct21 prestart window expired at 2026-10-21T12:30:00Z. Do not call an unconsumed *file marker* authority to repeat the owner-granted *single launch*.
- Preserve original wrapper/source, screenshot outside GitHub, SHA identities and failed attempt output. No broker action, PR merge, PCR3/task change, account switch or external-Python trading enable authorized.
- Owner may perform a separately requested OS-only read of the unchanged wrapper's marker path/remaining definitions and an independent interactive string-codepoint reproduction *without invoking the original wrapper or MT5*. Behavioral PS5.1 regression must accompany a prospective corrective wrapper. Only a separately preregistered later qualifying window and fresh explicit owner capture grant could authorize another read-only MT5 run.
- Cost calibration, live-input Policy A binding, DEMO-ADMIT, APC-DEMO and real-money authority remain blocked or prohibited as before.

## Durable GitHub links

- [First screenshot incident record](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/28#issuecomment-6315894310)
- [Follow-up exact SHA + source-line diagnostic](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/28#issuecomment-6315973328)
- PR #28 implementation exact previously verified head `90c3e93330edeee58a0709a41e7393f7818f4ea8`, still OPEN/DRAFT/UNMERGED at incident review; production main `2848c98940def262459fd89d5897c6f63dd6aadb`.

Documentary record only. No VPS/MT5/broker action was performed by assistant.
