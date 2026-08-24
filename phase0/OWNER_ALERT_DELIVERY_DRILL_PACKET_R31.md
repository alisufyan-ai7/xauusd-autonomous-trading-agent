# G0-09 email + Telegram delivery drill — R31 action packet

Authority: owner-approved 2026-08-24
Scope: one sanitized A1 canary, email primary and Telegram secondary
Trading: prohibited; external Python trading remains disabled

Execution requires the exact verified primary email recipient and exact
Telegram recipient/chat. Do not put either identifier or any credential in the
repository.

## Prepare

Use a fresh private directory:

~~~powershell
git pull --ff-only
git rev-parse HEAD
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\phase0\validation\alert_evidence\run_prepare_private_canary.ps1 -Output C:\Gate0Private\Alert-R31-DELIVERY
~~~

Copy only the generated canary_sha256 into this message:

Subject: Gate 0 A1 canary test — no trading authority

Body:

> TEST/CANARY ONLY. No trading or broker action is authorized.
> Canary SHA-256: [canary_sha256]
> Please acknowledge by returning the same SHA-256.

Do not include credentials, names beyond what the configured channel already
shows, account numbers, broker state, private evidence, attachments or links.

## Deliver and acknowledge

Let T0 be created_utc in PRIVATE_CANARY.json.

1. At minute 0, send the exact same message through primary email and secondary
   Telegram push.
2. Save each transport/recipient delivery receipt inside
   C:\Gate0Private\Alert-R31-DELIVERY; record actual UTC send and receipt
   timestamps.
3. If the owner-designated acknowledgement has not arrived, repeat on both
   channels at minutes 5, 10 and 15. Stop repeating immediately after a valid
   acknowledgement.
4. The acknowledgement must return the same canary SHA-256 and arrive no later
   than T0 + 15 minutes. Save its evidence inside the same private directory.
5. No message may trigger a trade, broker action or restoration of risk
   authority.

After each channel attempt, record its receipt:

~~~powershell
py -3.12 .\phase0\validation\alert_evidence\private_delivery_evidence.py --output C:\Gate0Private\Alert-R31-DELIVERY record-receipt --channel EMAIL --attempt-minute 0 --sent-utc [UTC_TIMESTAMP] --received-utc [UTC_TIMESTAMP] --transport-receipt-file [PRIVATE_RECEIPT_FILE]
~~~

For Telegram use --channel TELEGRAM_PUSH. For repeats, use the exact attempt
minute 5, 10 or 15.

Record the acknowledgement:

~~~powershell
py -3.12 .\phase0\validation\alert_evidence\private_delivery_evidence.py --output C:\Gate0Private\Alert-R31-DELIVERY record-ack --acknowledged-utc [UTC_TIMESTAMP] --acknowledgement-evidence-file [PRIVATE_ACK_FILE]
~~~

Then verify:

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\phase0\validation\alert_evidence\run_verify_private_delivery.ps1 -Output C:\Gate0Private\Alert-R31-DELIVERY
~~~

Require PASS_SPEC_ONLY. Preserve only the publication-safe evidence-bundle
hash, local-audit final hash, delivery/acknowledgement timestamps and PASS
result. Any missing channel, late receipt, missing repeat, digest mismatch,
audit-chain failure or late acknowledgement fails closed.
