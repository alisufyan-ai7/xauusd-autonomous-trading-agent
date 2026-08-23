# A1 private alert-delivery evidence

This package prepares a random canary and an empty evidence template. It has no
email, Telegram, network, broker or credential capability and sends nothing.
The output path must be outside the repository.

Later, an operator-approved delivery drill must send the same canary through
email and Telegram push, preserve hashed transport receipts, and record the
designated acknowledgement within 15 minutes. The offline verifier rejects a
missing path, mismatched canary, duplicate channel, invalid chronology, late
delivery or late acknowledgement. It also requires a SHA-256-bound record from
the append-only local audit chain; off-host delivery alone cannot satisfy A1.
It never restores risk authority.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\run_prepare_private_canary.ps1 `
  -Output C:\Gate0Private\AlertCanary-YYYYMMDD
```

Do not enter recipient addresses, Telegram identifiers, credentials or names
in repository files. Do not run a delivery drill until separately authorized.
External Python trading remains disabled throughout.
