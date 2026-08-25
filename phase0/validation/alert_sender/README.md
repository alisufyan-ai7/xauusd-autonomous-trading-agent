# G0-09 private dual-channel sender

This package implements only the owner-approved R31 A1 canary. It cannot call
MT5, a broker or an order API. The private sender configuration, recipient
identities, bot token, Gmail app password, numeric Telegram chat ID, raw
receipts and acknowledgement remain outside the repository.

## One-time private setup

The owner creates a dedicated bot with Telegram BotFather, opens the new bot,
and is ready to send the exact `/start <nonce>` printed by the setup wrapper.
The owner also creates a dedicated Gmail app password after enabling two-step
verification if necessary. Neither secret is entered in chat.

From the repository root on the VPS:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\phase0\validation\alert_sender\setup_private_sender.ps1
```

Enter the owner-confirmed email address and Telegram username at the prompts,
then paste both secrets only into the masked VNC prompts. The wrapper creates
or verifies the Gmail label `XAUUSD Gate 0 Alerts`, authenticates SMTP/IMAP
without sending, verifies the Telegram bot and empty-webhook state, and pins
the numeric private chat only after the exact nonce-bound `/start` update.

The two secrets are encrypted with Windows DPAPI CurrentUser and stored under
the owner-only ACL at `C:\Gate0Private\AlertSender-R34`. They can be decrypted
only under the same Windows user profile on the same VPS. Setup prints
`CONFIGURED_NOT_SENT`; it never sends a canary.

## Approved one-command canary

Only while the owner can return the exact acknowledgement within fifteen
minutes, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\phase0\validation\alert_sender\run_dual_channel_canary.ps1
```

The wrapper first reruns the offline sender controls, then performs non-delivery
preflights. It creates one fresh private canary and launches email and Telegram
at the same frozen attempt offset. Both channels receive the identical subject,
body and digest. If no valid acknowledgement arrives, it repeats both at
minutes 5, 10 and 15, then fails closed at the fifteen-minute deadline.

The owner acknowledges by sending exactly `ACK <canary_sha256>` in the bound
Telegram private chat or by replying to an attempt email with that exact text.
Telegram Bot API acceptance is recorded only as provider acceptance, not as a
read receipt; the authenticated inbound acknowledgement is the end-to-end
receipt evidence. Raw messages, numeric IDs and transport evidence stay in the
fresh private output. PASS is `PASS_SPEC_ONLY` and restores no trading authority.
