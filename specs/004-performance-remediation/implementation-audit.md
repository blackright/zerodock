# Existing Implementation and Performance Handoff

**Date**: 2026-10-29 (Europe/Budapest)
**Scope**: Read-only reuse/replace/preserve review for the new specification.
No remediation implementation, dependency change, Git operation or new performance
measurement was performed while creating this follow-up.

## Verified starting point

- Issue #1 handler hot reload is functionally implemented: opt-in CLI forwarding,
  exact-target content polling, fresh source compilation, targeted invalidation,
  recovery, native debugging and lifespan cleanup.
- Current source executes handler modules on every request in both modes; it is
  not a persistent callable cache. Loading and invalidation use per-target leases.
- A previously approved optimization already removed duplicate path resolution
  inside load_handler while preserving public canonical module identity behavior.
  Do not repeat that change as a new solution.
- Latest Windows/Python 3.14.6 full suite: **194 passed in 8.48s**, with startup
  max 18.3976ms and direct ASGI total max 2.9545ms in its small measured workload.
- Subsequent isolated Windows/Python 3.12.0 full suite: **192 passed, 2 failed in
  38.28s**. Reload-off direct ASGI max **36.2505ms**; reload-on warm-import startup
  max **230.2233ms** and recorded direct ASGI max **23.7090ms**. All functional
  cases passed. No concurrent agent checks were running; host contention was not
  independently measured and causality remains unknown.
- Configured repository lint, formatting and typing pass. Core statement coverage
  is loader **125/126 (99.2063%)**, watcher **166/174 (95.4023%)**, measured separately
  using the existing standard-library tracing tool (not branch coverage).
- Constitution 2.0.0 explicitly approves <60,000,000-byte actual baseline server RSS;
  <50,000,000 is an optimization target. Fresh validation had 18 passing samples,
  maximum **54,988,800 bytes**. Memory is not the current failed acceptance gate.

## Reuse / replace / preserve decisions

| Existing area | Decision |
| --- | --- |
| tests/integration/test_performance_benchmarks.py | Reuse definitions, thresholds and raw sample output; inspect measurement overhead before any revision |
| src/zerodock/engine/loader.py and watcher.py | Preserve freshness, per-request execution, coordination, bounded observation and cleanup |
| src/zerodock/gateway/app.py and server.py | Preserve routes, events, timeouts, response/error contracts and native execution |
| Existing disposable live-server harness | Reuse actual PID/current RSS, loopback binding and owned shutdown methodology; port test-only helpers into durable tests only if approved |
| Existing profiler/trace experiments | Retain as diagnostics, not performance acceptance; correct measurement limitations rather than suppress samples |
| Framework/dependency stack and runtime defaults | Preserve unless a separately approved proposal establishes benefit and compatibility |
| Original performance failures | Preserve and link; no retroactive passes from a newer favorable run |

## Known limits of earlier investigations

Unwrapped requests sometimes exceeded 5ms; a later bounded trace did not reproduce
the spike. Neither finding establishes an OS, application or scheduling root cause.
Thread CPU clocks were too coarse for sub-5ms attribution on the inspected machine.
Profiler overhead and differences between sequential modes prevent simply subtracting
means to claim a causal timing improvement.

Earlier memory review found default-app construction too small to explain the
memory gap (~17KB traced allocations per additional app in that probe). Framework
imports account for substantial retained allocations, but traced Python allocations
are not RSS and import deltas are order-dependent. Do not remove a public app or
replace the server based on those observations alone.

## Evidence and publication

Detailed historical summaries remain in ../003-handler-hot-reload/verification/,
especially phase-06-closeout.md, memory-amendment-validation.md and
runtime-comparison.md. The repository ignore policy permits reviewed Markdown
summaries but deliberately excludes generated raw logs/output files, executable
diagnostic folders, caches and temporary environments. Links in historical summaries
to raw artifacts refer to local review evidence, not promised public downloads.
Portable project-wide conclusions and exact current failures are included above.

No Git state was inspected. Whether any artifact was previously tracked must be
checked by the human before pushing; ignore rules do not remove already tracked files.

## Closure boundary

The user requested separating remediation so the maintainer can close issue #1 as
functional delivery after creating a real linked follow-up issue. This local spec
does not create that remote issue or complete the original Phase 6 performance gates.
Original T043/T045/T047/T048 remain recorded as unresolved and must not be silently
checked off. The constitution and project performance obligations remain in force.
