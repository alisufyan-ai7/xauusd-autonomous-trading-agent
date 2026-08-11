# Phase 0 read-only MT5 evidence collector v0.1.1

This diagnostic gathers account, terminal, symbol, price/history, exposure, and broker-calculation evidence from an already-open Exness MT5 **demo** terminal. It is not production trading code. Gate 0 remains incomplete after a successful run.

## Safety boundary

- The collector accepts no account login, password, server, API key, or token.
- It contains no order submission, order preflight, modification, cancellation, close, login, symbol-selection, subscription, shell, or network operation.
- It aborts before account or market collection unless MT5 reports **Disable automated trading via external Python API** is enabled.
- Its frozen MetaTrader call surface contains only observation functions and `order_calc_profit` / `order_calc_margin`, which calculate values without submitting an order.
- A syntax-tree policy check and a fake-MT5 trap test run before every collection. Package hashes are checked before launch.

## Windows VPS instructions

1. Open the intended Exness MT5 terminal and sign in to the intended **demo** account manually. Do not put credentials in any file or command.
2. Remove or pause unrelated EAs/scripts for a consistent snapshot. In MT5, open **Tools → Options → Expert Advisors** and check **Disable automated trading via external Python API**. Leave it checked for the whole run.
3. Install 64-bit Python 3.12 if needed. In PowerShell, install the complete binary-only dependency lock using the recorded PyPI hashes. The lock explicitly includes both `MetaTrader5==5.0.6090` and its NumPy dependency, `numpy==2.5.0`:

   ```powershell
   py -3.12 -m pip install --require-hashes -r .\requirements-win-py312.txt
   ```

4. Copy this complete folder to the VPS. Open PowerShell in the folder and run:

   ```powershell
   powershell.exe -NoProfile -File .\run_collector.ps1
   ```

5. If several gold symbols are reported and the result is `PARTIAL`, rerun with the exact symbol shown in MT5 Market Watch, for example:

   ```powershell
   powershell.exe -NoProfile -File .\run_collector.ps1 -Symbol XAUUSDm
   ```

6. Return only the generated `.zip` and matching `.zip.sha256` files. Never paste or send an MT5 password, login number, identity document, home address, or unredacted account statement.

Also report, in plain text, the Exness contracting entity and account type shown in your Personal Area/current client agreement (for example, `Exness (SC) Ltd — Standard demo`). Do not send the agreement if it exposes personal data. MT5 cannot prove residency eligibility or contractual permission for automated trading, so this documentary check remains separate.

## What the hashes prove

The package manifest detects changes to the shipped collector files. The evidence manifest detects changes to captured output. The archive hash detects transfer corruption. These hashes do not prove that broker data is true, complete, legally permitted, or representative of live execution.

## Expected safe stops

The collector stops without evidence collection if package verification fails, MT5 is disconnected, or the external-Python trading block is not enabled. A `PARTIAL` result is still useful evidence and does not pass Gate 0.

## Superseded package warning

Do not use collector `v0.1.0`. Its dependency lock omitted the transitive NumPy pin/hash, so pip correctly refused installation in `--require-hashes` mode. Use only the byte-exact `v0.1.1` archive and verify its published archive SHA-256 before running it.
