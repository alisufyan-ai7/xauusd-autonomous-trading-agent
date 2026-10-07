# XAUUSD execution-disabled production candidate

This package is the APC-A shadow runtime. It is restricted to XAUUSD,
`SHADOW` mode, a `NULL` broker sink, and zero broker actions. It contains no
submit, modify, cancel, close, demo, or live-order capability.

The local implementation is anchored to R42. Publication, VPS operation,
external Sol transport, demo execution, and live execution each require their
separate owner approval. Gate 0 evidence remains independent and unchanged.
