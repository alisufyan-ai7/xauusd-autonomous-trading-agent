# R34 one-command closure-wrapper validation

## Result

- Focused G0-07/G0-09 controls: PASS, 50/50 tests across 7 groups
- New regressions beyond R33: 19
- Aggregate controlled registry: PASS, 357/357 across 25 groups
- Python compilation: PASS for all new/changed Python modules
- Gate 0 matrix: unchanged at 6 PASS / 8 PENDING
- G0-07: wrapper-ready, not executed
- G0-09: secure sender package ready, not configured and not executed
- External Python trading: disabled

## Bounded implementation

The G0-07 wrapper accepts only the frozen R31 prefix. It pins `main`, checks
zero exposure and the disabled barrier, uses a bounded adapter watchdog, polls
fresh recovery, gracefully restarts the single MT5 terminal, resumes after the
single Windows restart under the same interactive user, verifies every prefix,
and directly reconciles the immutable pre/post exposure chain before sealing a
publication-safe result.

The G0-09 setup uses masked prompts, redirected standard input, Windows DPAPI
CurrentUser and an owner-only ACL. Non-delivery preflight verifies Gmail
SMTP/IMAP and the dedicated label plus Telegram bot identity, empty webhook and
an exact nonce-bound private-chat update. The runtime sends only one sanitized
A1 canary body concurrently to the two pinned paths, distinguishes provider
acceptance from end-to-end acknowledgement, preserves private receipt hashes,
and applies the frozen 0/5/10/15-minute oracle.

No restart, disconnect, canary, email, Telegram message, broker mutation,
provider action, OpenAI call or trade occurred during R34 engineering.
