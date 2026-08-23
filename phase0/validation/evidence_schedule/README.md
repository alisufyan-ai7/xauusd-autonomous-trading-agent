# Gate 0 official-source and session evidence schedule

This oracle creates a deterministic, read-only capture plan only; it does not
schedule or execute work.

The frozen plan provides:

- four official Event Guard reads per source per day at 00:15, 06:15, 12:15
  and 18:15 UTC so adjacent records can expose natural revisions/failures;
- dense T-24h, T-6h, T-1h, T+15m and T+2h checks around registered releases;
- daily refresh of the official Exness instrument-hours and holiday pages;
- extra T-14d/T-7d/T-24h/T-1h source checks for holiday boundaries; and
- read-only XAUUSD `BEFORE`, `INSIDE`, `AFTER` terminal observations for each
  declared close/reopen interval.

Run from this directory:

```text
python -m unittest -v test_schedule_oracle.py
```

Natural source failures may be observed, but this plan never causes an outage.
It contains no restart, disconnect, message, order, process-control or trading
task. Executing future VPS checkpoints remains separate from this offline plan;
external Python trading must remain disabled.
