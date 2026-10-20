# D0-R2 immutable VPS pre-attach failure — Python runtime candidate discovery (2026-10-20)

## GitHub and original owner approval

Reconciled on receipt: production `main ccaa8338aecee8bd3afbc358644410dff6c512e5`; owner-approved D0-R2 draft PR19 exact HEAD `ccee77501f74de7f59c457945a42609adf4bc6e5`, base PR18 exact `3ff100189349ada29331730af99459fecc4ea821`, PR13 approved design `847829378956670e8936bf46c82e685de41145fd`. All remain draft and unmerged; PCR3 and all prior failed evidence unchanged. No actor in this GitHub-only review accessed VPS, MetaTrader5 or placed/changed any broker order. The owner explicitly approved **ONE** R2 source-discovery attempt using registration SHA256 `13c1ece5068a18b04512776a7387615c51c7075bd9df850d7e4415f6cd773c61` and frozen bootstrap `91d493b5af205fcf964ee1d051d9bd0f505d17ea0fad9f1d0ca3e59678e31087`.

## Actual reported VPS stdout (owner supplied, not independently attested)

- `VERIFIED_PR19_HEAD=ccee77501f74de7f59c457945a42609adf4bc6e5`
- `VERIFIED_BOOTSTRAP_SHA256=91d493b5af205fcf964ee1d051d9bd0f505d17ea0fad9f1d0ca3e59678e31087`
- `D0_R2_EXISTING_TERMINAL_PID=6216` at delivery wrapper preflight; terminal executable path **not printed**; no final PID/path verification occurred.
- R2 bootstrap proof SHA256s (in chronological printed order):
  1. `d959a80482deea23b14e4c7be5ab9f2d02116d5ff2a26e3eb467bbf79229ad19` — new distinct R2 stage reserved.
  2. `994def2e106407cfa4853a8ef764603226274aa4855990dac87ad1fa59a52be2` — exact PR19 ref and four functional staged files source-byte pins passed.
  3. `d4a3304354649fd295805760a2668374ae8b10163bedb605beb49aad597a6d21` — R2 failure marker emitted by catch path.
- `VERIFIED_GITHUB_HEAD=ccee77501f74de7f59c457945a42609adf4bc6e5`; no `PYTHON_EXISTING=` or `TERMINAL_EXISTING=` or private D0 raw/journal SHA after that.
- Failure class `RuntimeException`; `NO_EXISTING_PYTHON312_WITH_MT5_PREATTACH_FAIL` from `v12-d0-r2-attended-bootstrap.ps1:130` before obtaining an existing-terminal exe/PID inside that reviewed bootstrap and **before calling the reviewed D0 wrapper**.
- R2 stage retained: `C:\Users\Administrator\AppData\Local\XAUUSD-v12-D0-R2-IsolatedStage\13c1ece5068a18b04512776a7387615c51c7075bd9df850d7e4415f6cd773c61`
- R2 bootstrap delivery retained: `C:\Users\Administrator\AppData\Local\XAUUSD-v12-D0-R2-BootstrapDelivery\13c1ece5068a18b04512776a7387615c51c7075bd9df850d7e4415f6cd773c61`
- Private output path was merely printed, **not verified as created**: `C:\Users\Administrator\AppData\Local\XAUUSD-v12-D0-PrivateEvidence\13c1ece5068a18b04512776a7387615c51c7075bd9df850d7e4415f6cd773c61`.

## Root-cause analysis, provenance and limitations

The bootstrap only inspected these candidate Python executable paths: active PowerShell CWD `.venv\Scripts\python.exe`, `%USERPROFILE%\Desktop\xauusd-autonomous-trading-agent\.venv\Scripts\python.exe`, `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`, `C:\Python312\python.exe`, and **only the first** PATH `python.exe`. It required Python version 3.12 and `importlib.util.find_spec('MetaTrader5')`; its probe `-B -c` imports `sys,importlib.util`, **not** the trading/broker module. There is no proof that Python 3.12 is unavailable globally, that MT5 is uninstalled, or that any VPS setting is incorrect: another active Python venv, alternate installation path, installation-specific package, or only Python 3.11 could exist. Do not silently substitute or install software or enable Python trading.

**Disposition = SECOND DISTINCT PREATTACH FAIL_CLOSED; R2 AUTHORIZATION CONSUMED.** R1 earlier failed from reserved PowerShell `$Host` after staging, separately immutable. R2 source verification had progressed further to Python discovery, but the reviewed D0 wrapper, `MetaTrader5.initialize()`, `terminal_info`, `account_info`, `positions_get`, `orders_get`, `symbol_info`, `symbol_info_tick`, Exness fingerprint/zero exposure/disabled trading checks **were never reached in the reported flow**. Thus NO D0 broker source data admitted. A terminal process PID was read at the initial wrapper but no broker connection or MT5 attachment is evidenced. No order API or trade action observed.

Preserve R1 and R2 stages, proof files, script files, owner output and raw Windows paths unchanged; never retry the same R1/R2 registrations or erase/relabel earlier failed attempts. A third prospective D0 registration and a **fresh exact-head owner approval** would be required for any new MT5-attaching action; one cannot silently reuse the past approvals.

## Smallest remaining step: no-execution read-only Python environment survey

Prepare (separately on a new draft GitHub-only branch) `demo_adapter/scripts/v12-d0-r2-python-environment-readonly-survey.ps1`: it only reads current and common installation paths, read-only Python registry entries, PATH executable locations, and existing process paths. It **does not launch Python, import MetaTrader5, attach or initialize MT5, run the D0 collector, create/write/delete files, fetch Git, install software, alter Task Scheduler/PCR3, or enable trading.** This observation is separate from D0 and does not use R1/R2 registration or owner approval; it can identify path candidates to prospectively correct the next owner-gated D0 design. The script may show Python paths without proving runtime importability, installed wheel compatibility or exact MT5 permissions. A later *separately authorized* narrow importlib-only check might be appropriate if on-disk inventory remains inconclusive.

**Next owner action:** ask for running a pure read-only Python-environment file/path survey if desired; do NOT ask for D0-R3 broker attachment or four-hour capture until that evidence is reviewed and a new exact prospective protocol is frozen/tested. No order APIs, demo/live trading, MT5/PCR3/scheduler changes, or PR merges.
