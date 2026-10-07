# G0-09 secure sender and one-command canary — R34

Recipient identities remain private and are entered only at VPS prompts. The
repository contains no token, app password, email address, Telegram username or
numeric chat ID.

## Unavoidable one-time owner steps

1. In Telegram, open the verified `@BotFather`, run `/newbot`, create a dedicated
   bot and keep its token off chat and GitHub.
2. In the Gmail account, ensure two-step verification is enabled and create a
   dedicated app password named `XAUUSD Gate 0 Alerts`. Keep the 16-character
   value off chat and enter it without display spaces.
3. In the VPS VNC console at the repository root, run:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\phase0\validation\alert_sender\setup_private_sender.ps1
   ```

   Enter the owner-confirmed email and Telegram username, then paste the bot
   token and Gmail app password only into the masked prompts. When the wrapper
   prints `BIND`, open the new bot and send the displayed exact
   `/start <nonce>` command. Setup creates/verifies the Gmail label, pins the
   numeric private chat, encrypts both secrets with Windows DPAPI CurrentUser
   under an owner-only private ACL, and prints `CONFIGURED_NOT_SENT`. No canary
   is sent during setup.

## One-command approved canary

While available to acknowledge within 15 minutes, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\phase0\validation\alert_sender\run_dual_channel_canary.ps1
```

Reply in the bound Telegram chat with the exact `ACK <canary_sha256>` printed in
the canary, or reply to the email with that exact text. The wrapper launches the
same sanitized message on both channels, records private provider/mailbox
receipts, repeats both only at frozen minutes 5, 10 and 15 while unacknowledged,
and runs the frozen hash-chain oracle. Require `PASS_SPEC_ONLY`; it restores no
trading authority.
