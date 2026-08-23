# Controlled revision/outage/holiday validation note

Scope: offline specification and testing only. No network, broker, model or
trading call is present.

Acceptance claims are deliberately narrow: the transition harness exercises
append-only revision typing, conservative moved-event locks, immediate locking
for newly discovered events, outage fail-closure, full-horizon recovery gating,
and DOL holiday replacement through the production parser. Synthetic fixtures
cannot close live update latency, actual outage recovery, or holiday-publication
observations. Those remain external evidence requirements.

Local verification on 2026-08-23: 10/10 controlled-evidence tests passed. The
unchanged parent Event Guard suite also passed 43/43 tests.
