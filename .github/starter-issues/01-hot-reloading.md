# FEAT-002: Handler Hot Reload — Delivery Handoff

**Status**: Functional behavior is implemented in the current checkout.
This card is not confirmation of a published release or closed GitHub issue.

## Delivered behavior

- Opt-in `zerodock dev --reload`; default startup remains reload disabled.
- Exact configured-handler content observation without process or port replacement.
- Fresh source after invalidation, including same-size/same-timestamp edits.
- Atomic-save, invalid-source and deletion/recreation recovery.
- Native sync/async execution, debugging and owned lifecycle cleanup.

Imported helpers and configuration changes are outside the automatic reload scope.
Per-request module execution is preserved in both modes; invalidation alone is not
the entire freshness mechanism.

## Remaining work

Cross-runtime startup/dispatch acceptance is tracked by the local
[performance remediation specification](../../specs/004-performance-remediation/spec.md).
A maintainer must create/verify the actual follow-up GitHub issue and link it before
closing the original issue as functional delivery. Do not reopen this card as an
unimplemented watcher task or describe all original Phase 6 gates as passed.

See [the handoff record](../../specs/003-handler-hot-reload/issue-handoff.md),
[reload guidance](../../docs/hot-reload.md), and
[validation results](../../docs/performance.md).
