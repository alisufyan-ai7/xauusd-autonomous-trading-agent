# Incident — 2026-10-23 first comprehensive MT5 collector attempt: isolated Python import failure

**Evidence classification:** FAILED BEFORE MT5 INITIALIZATION; NO MARKET/BROKER REQUEST; ZERO four-hour quote samples; ZERO actual DEMO/LIVE orders; no account setting changes. The owner provided a sanitized PowerShell traceback of the exact attended command. This is a *software import-path defect*, not an Exness broker or trade rejection, and it does NOT count as a completed v1.1 observation or a Gate0 pass.

## Initial failure / preservation

- Owner invoked the one source-pinned launcher on the Windows ForexVPS through GitHub PR40's approved bootstrap at `f1fb8ac3f010b3ac139eab5777e65fdbd83e4bdc`. The launcher selected original comprehensive collector Git source `150b60e8884b13d6a934c1e9ff77bd523826c75e`.
- The launcher verified repository, Python3.12 and source pin, then printed `READONLY_SOURCE_PIN` and a private LOCAL evidence **path**. The interpreter failed during `from xauusd_demo.broker_money_readonly import ...` → package `__init__.py` → `mt5_demo.py` → `risk_binding.py` → `from xauusd_agent.risk ...`: **`ModuleNotFoundError: No module named 'xauusd_agent'`**.
- The original collector's `sys.path` under `python -I` included `demo_adapter` and `demo_adapter/src`, but **omitted the Git-exported repository's core `src`**. CI previously used editable `pip install -e ".[dev]"`, concealing this error.
- The failure happened at module import, BEFORE `run()`, `MetaTrader5.initialize()`, output-directory creation or prospective sampling. The provided transcript shows `COMPREHENSIVE_MT5_CAPTURE_FAIL_CLOSED__NO_ORDER`, so **there is no successful broker capture to reuse**. Do not infer source costs or restart an unstarted four-hour campaign.

## Exact prospective correction

- Same sole PR40; no new PR. The collector now binds all three source roots to the exact exported Git tree: `<archive>/src`, `<archive>/demo_adapter` and `<archive>/demo_adapter/src`. No installed editable package can replace these module origins.
- Added `--self-check-imports` that verifies all three critical modules reside in the pinned exported paths and returns `PINNED_LOCAL_IMPORT_PREFLIGHT_PASS_NO_MT5` **without importing or initializing MetaTrader5**.
- Native tests stage the *actual repository layout* in a temporary directory and execute the collector with **`python -I -S ... --self-check-imports`**: isolated interpreter, no site/editable packages, no broker network. This exactly reproduces the failure's relevant packaging condition.
- The SAME `phase0/ops/pr40_one_comprehensive_mt5_readonly_4h_20261023.ps1` first calls `-B -I -S --self-check-imports`, and aborts before the four-hour run if imports fail. It then invokes the exact source normally only when this gate passes; it never logs in, changes MT5 toggles, checks/sends broker orders or installs a job.
- The launcher has been repinned to **tested corrected source SHA `10425e6180ef660226e298ef06a0fa423334332e`**. Source release [CI 39949092166](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39949092166) passed **342 Windows tests, 339 Ubuntu passes / 3 Ubuntu skips**, Ruff, strict MyPy 20 sources and `PASS_STATIC_STOP_PRESENT__FIRST_DEMO_ORDER_NOT_ADMITTED`. The companion Windows PowerShell static tests require the new pin and exact import preflight. Later documentation commits still require independent GitHub CI reconciliation.

## No-repetition owner next action / safety

The next owner invocation is a **single corrected attempt to START the originally intended comprehensive four-hour source collection**, not a repeat of an earlier four-hour dataset; the previous run never began sampling. Use the revised canonical script only, source-pinned at the SHA above, with the reviewed bootstrap from the latest PR40 discussion/handoff. Do not run older partial diagnostics. If preflight, account state, source freshness or session checks fail, **retain the existing private local failure artifacts and report sanitized failure**, no blind restarts. Source completeness, numeric costs and official calendar/session provenance remain independently unadmitted even if collection completes.

Project target remains actual **MT5 broker-executed Exness Pro DEMO-server orders on virtual funds**, no simulator as final proof; S2 Policy A hard stop remains, and future 0.01-lot real-money LIVE trading needs separate acceptance/owner authority. Accepted production `main` remains unmodified.
