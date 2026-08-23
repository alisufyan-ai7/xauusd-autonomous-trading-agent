# Controlled Event Guard evidence

This package replays revision, outage and holiday transitions using normalized
events plus hash-only acquisition metadata. It is compatible with summaries
derived from the private capture but neither requires nor admits raw source
bodies, account metadata, credentials or screenshots.

Run from this directory with Python 3.12:

```text
python -m unittest -v test_controlled_evidence.py
```

The oracle proves deterministic fail-closed behavior for an event added inside
its pre-lock, a moved event retaining both old and new windows, unexplained
future disappearance, a source outage despite cached events, incomplete
recovery coverage, and the DOL Thanksgiving exception using the production
parser. These are controlled conformance exercises, not observations of an
actual agency revision or outage.

External closure still requires timestamped private captures observing a real
revision/holiday update and a controlled acquisition failure/recovery. Only
sanitized hashes, transition types, timestamps, latency and PASS/FAIL summaries
may be published.
