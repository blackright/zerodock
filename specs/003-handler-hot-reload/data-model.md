# Runtime Data Model: Handler Hot Reload

**Date**: 2026-10-29
No database, persisted revision history, new YAML schema, or cached callable is introduced. These are proposed internal runtime entities, not implemented classes.

## Handler Target

| Field | Meaning / validation |
| --- | --- |
| resolved_path | Canonical path resolved consistently with current configuration/loader behavior |
| module_name | Existing `zerodock.handlers.mod_` plus first 12 hex characters of SHA-256 of the resolved path string |
| entrypoints/routes | Existing configuration references; many may share one target |

Deduplicate by canonical path per app. Do not add independent case-folding or path normalization that changes existing module identity. Symlink retargeting is not an additional guaranteed feature; retain existing resolution semantics.

## Observed Revision

| Field | Meaning / validation |
| --- | --- |
| status | `readable`, `missing`, or `unreadable` |
| digest | SHA-256 of source bytes only when readable |
| error_category | Bounded error classification for diagnostics, not source/error payload history |
| last_observed_at | Monotonic observation time for diagnostics/testing |

Transitions: initial scan establishes baseline; different readable digest, readable-to-missing/unreadable, or recovery-to-readable triggers invalidation. Identical digest/status does not. A repeated unreadable state may update diagnostics without repeatedly invalidating or logging each poll. Missing/unreadable targets remain in the configured watch set. Intermediate revisions may be coalesced.

## Module Coordination Entry

| Field | Meaning / validation |
| --- | --- |
| module_name | Process-wide coordination key |
| lock | Reentrant per-module synchronization primitive |
| active_leases | Number of loader/invalidator holders or waiters; never negative |
| watcher_owners | Active app observer registrations; never negative |

Registry acquisition/release uses a short registry guard. Increment leases before waiting on the module lock, and retain a strong reference. Delete coordination metadata only with zero leases and zero owners. One app shutting down must not remove another app's ownership. This entry contains no persistent handler callable or source body.

## Load Attempt

Transient fields: target, requested entrypoint, reload-mode boolean, and newly created module object. States: resolving -> loading -> validating -> callable-returned, or failed. Failed cleanup removes `sys.modules[module_name]` only if it is the attempt's own module. Successful calls still execute a fresh module on every request. Returned callables live with invocations; invalidation does not cancel or mutate them.

## Observer Lifecycle

| State | Allowed transitions and resources |
| --- | --- |
| disabled | No observer, scan task, or ownership registration |
| initializing | Register ownership, collect baseline and comparison scan; no accepted HTTP work yet |
| running | One loop and at most one offloaded scan; bounded fingerprints and stop event |
| stopping | Set stop, interrupt interval wait, drain outstanding scan/loop, unregister ownership |
| stopped | No owned pending I/O tasks, observer tasks, or open file handles |
| failed | Fatal initialization propagates; unexpected runtime termination is explicitly logged; cleanup still runs |

Per-file failures are revision states, not automatically fatal observer states. Shutdown must not dispose of the shared event loop/executor. Default executor threads themselves are shared infrastructure, not application-owned watcher resources.

## Invariants

1. Observation and loading use one target identity scheme.
2. Fingerprints never become a source/module/callable cache.
3. Module locks never span handler invocation or await points.
4. All test-owned runtime entries/resources are cleaned independently of other apps/tests.
5. No source contents or request data enter reload logs.
