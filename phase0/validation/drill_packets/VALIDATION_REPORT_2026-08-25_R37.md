# R37 G0-09 secret-safe diagnostic correction

## Result

- Authoritative parent: `85ac6cec60315d8298c04241d0504ee1e547e070`
- Focused alert controls: PASS, 24/24 across 3 groups
- Alert-sender controls: PASS, 13/13
- New regressions beyond R36: 3
- Python compilation: PASS
- Operational setup result: two fail-closed attempts before binding or sending
- Gate 0 matrix: unchanged at 6 PASS / 8 PENDING
- External Python trading: disabled

## Concrete defect corrected

R34 intentionally suppressed the Telegram exception because its request URL
contains the bot token, but it also discarded every safe cause distinction.
After a fresh token failed identically and TCP 443 was observed reachable, the
generic message could not distinguish an HTTP token rejection from TLS, DNS,
timeout, connection or proxy/network failure.

R37 emits only a bounded category and never renders exception text, token
values or the token-bearing URL. Tests cover HTTP 401, certificate failure and
Telegram API rejection, including formatted exception output. The Gmail,
Telegram-binding, DPAPI, recipient, canary, acknowledgement and frozen A1
behavior are unchanged.

No setup retry, canary, broker mutation, OpenAI call or trade occurred during
this correction.
