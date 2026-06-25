# Provenance

## Clean-room creation
This repository was created **clean-room**. It does **not** inherit:
- any legacy git history,
- any old tags or release artifacts,
- any source-code projection of the internal development platform,
- any secrets, keys, vault data, TLS private keys, logs, or runtime artifacts.

## Why
The mathdoc library was extracted from the internal HestiaOS development
toolchain to serve as an independent, reusable Markdown + LaTeX → PDF pipeline.
A clean repository boundary ensures no platform internals are leaked.

## Status
`developer-preview`. No production-readiness, compliance, or security guarantees
are asserted by this repository.

## Repository visibility
Initial repository visibility: **private**. Public release requires explicit
security and publication review.
