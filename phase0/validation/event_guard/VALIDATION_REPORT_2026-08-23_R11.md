# Official-source Event Guard validation report R11

**Date:** 2026-08-23 UTC  
**Result:** PASS — private evidence accepted; DOL TLS correction requires one rerun  
**Trading authorization:** none

The R16 VPS execution ran from commit
`974d5c86363390bf6fbe971131b72136dc6d7fe0` and passed 42/42 offline tests.
The append-only private acquisition manifest contains 35 records. Independent
recomputation verifies 35/35 record digests and links and 27/27 conditional-GET
cache identities. The chain ends at
`5df4661c4826e3d95b3f5fefa816fc98f72d3661ff96654087f751e609721beb`.
The private manifest, normalized report and console transcript SHA-256 values
are respectively `c1bf69c5c349507abee9899e0f5a66801eaee24a3aea1eb0ae5e052503777bef`,
`43b3522f06d2c01a91e2d7b5ee847b4d6524469aa4c9da2d0ec4cb21538f106e`
and `5f627ae7d564389377b7abe20d63e06fb37a948564a6fd2068604e0f22d3861e`.
No private bytes are published.

BLS, BEA, Fed and Census conditional acquisitions and normalization remain
healthy; every previously accepted BLS/BEA/Fed taxonomy is covered and
reconciliation passes without conflicts. DOL failed before any HTTP response
because the default Python/OpenSSL verifier could not construct the official
server's certificate chain. No DOL record or body was admitted and the overall
result correctly remained `FAIL_CLOSED`.

R11 changes only TLS path construction. It pins `truststore==0.10.4` by the
published wheel SHA-256 and uses its native Windows CryptoAPI context, which can
retrieve a missing intermediate and perform native revocation checking.
`PROTOCOL_TLS_CLIENT`, hostname verification and TLS 1.2 or later remain
mandatory. There is no unverified context, `CERT_NONE`, hostname-disable or HTTP
fallback. Missing dependencies and every remaining trust failure fail closed.

The Event Guard suite now passes 43/43; all nine controlled offline suite groups
pass 151/151. One private VPS rerun must prove the DOL HTTP/body/schema/horizon
path. No paid provider is recommended or activated. External Python trading
stays disabled.
