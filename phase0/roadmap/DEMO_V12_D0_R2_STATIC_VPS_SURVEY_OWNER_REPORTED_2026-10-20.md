# Owner-reported PR20 static VPS survey — 2026-10-20 (no Python/MT5 execution)

**Evidence classification: OWNER-SUPPLIED PowerShell stdout, not independent host attestation or broker proof.** This document was prepared on a separate draft GitHub-only successor to PR20. No direct VPS access was performed by the assistant. The survey was separately approved for **static, read-only observation only** and executed by the owner at `2026-10-20T14:22:43.0554548Z` per the printed UTC marker.

## Exact provenance

- Repo: `alisufyan-ai7/xauusd-autonomous-trading-agent`.
- Approved PR20 HEAD: `f255f59b401310a5acf2b3b0fc6169ac5635acc9`; parent PR19: `ccee77501f74de7f59c457945a42609adf4bc6e5`.
- Read-only source: `demo_adapter/scripts/v12-d0-r2-python-environment-readonly-survey.ps1`.
- SHA-256 of *original LF script bytes*, independently checked via GitHub: `e6095ec5b12a47ea86f6767008027c13e8d0e862ecec50b1a6725024f7c37605`.
- Owner stdout: `SURVEY_SHA256=e6095ec5b12a47ea86f6767008027c13e8d0e862ecec50b1a6725024f7c37605`; `SURVEY_SHA256_VERIFIED__STATIC_READ_ONLY`.
- Account/session operator label in the log: `WINDOWS_USER=trader`; CWD `C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent`. No broker login/account number recorded.
- Start and completion markers: `D0_PYTHON_LOCATION_SURVEY_START`; `D0_PYTHON_LOCATION_SURVEY_END__NO_PYTHON_OR_MT5_EXECUTED`. No reported error.
- Survey invocation: in-memory PowerShell 5.1 UTF8/LF SHA-verified ScriptBlock; no on-disk staging/files created by the survey.

## Exact owner-observed output fields

```text
SURVEY_SHA256=e6095ec5b12a47ea86f6767008027c13e8d0e862ecec50b1a6725024f7c37605
SURVEY_SHA256_VERIFIED__STATIC_READ_ONLY
D0_PYTHON_LOCATION_SURVEY_START
UTC=2026-10-20T14:22:43.0554548Z
WINDOWS_USER=trader
CWD=C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent
READ_ONLY_PYTHON_CANDIDATES
PYTHON_PATH=C:\Program Files\Python312\python.exe | VENV=False | MT5_PACKAGE_DIR=True | MT5_DIST_INFO=True
READ_ONLY_PYTHON_PROCESSES
READ_ONLY_TERMINAL_COUNT
TERMINAL_COUNT=1
TERMINAL_PID=6216 | EXE=C:\Program Files\MetaTrader 5\terminal64.exe
D0_PYTHON_LOCATION_SURVEY_END__NO_PYTHON_OR_MT5_EXECUTED
```

## Conclusions and strict limits

1. A **candidate** `C:\Program Files\Python312\python.exe` was found; it is system-level and not a venv. On-disk `MetaTrader5` package directory and its distribution `.dist-info` metadata were both present at the selected site-packages location. This does **not** establish Python version 3.12, package wheel ABI, package import success or broker runtime operation.
2. Exactly one `terminal64` process was observed, PID **6216**, EXE `C:\Program Files\MetaTrader 5\terminal64.exe`, matching R2's previously *initially* reported PID. This is a point-in-time OS observation, **not** a permanent terminal/process identity proof.
3. Read-only survey did not start new Python or terminal processes, run MT5 imports/attach, contact broker, call order APIs, or modify VPS files/config/tasks. The empty Python-process section indicates none listed by the matching process-name query; it does not prove all relevant processes globally absent.
4. R2's narrow candidate list omitted `C:\Program Files\Python312\python.exe`; the data explains why a candidate could have been missed. It **does not retroactively change R2 FAIL_CLOSED**, prove that an R2 import probe would pass, or prove there are no other environment issues.
5. R1 `ab1c266290f3c38f5b8e08bd44b0b06645c0e496839b7c9fa47fd4581f9d0534` and R2 `13c1ece5068a18b04512776a7387615c51c7075bd9df850d7e4415f6cd773c61` remain distinct consumed immutable FAIL_CLOSED attempts, with all on-VPS stages preserved. No rerun/reclassification.
6. No GitHub CI run is a broker/MT5 or VPS environment attestation. Future version/import/process verification requires separately approved attended runs, then **an independent future D0-R3 MT5 attachment approval** if ever proposed.
