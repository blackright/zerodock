# Phase 6 Bounded Per-Request Outlier Diagnostic

**Date**: 2026-10-29 (Europe/Budapest)
**Status**: Diagnostic complete. Prior acceptance failures remain open; no new production changes justified by this run.

## Scope and reuse

The user approved another bounded diagnostic after the single-resolution optimization passed functional tests but left two dispatch-budget failures. Reviewed the phase rules, existing diagnostic harness and current loader. Reused its disposable 60-byte source/config, actual reload-enabled app, explicit lifespan, and direct ASGI request contract. No production or acceptance-test edits, dependency installs, Git access, policy changes or threshold changes.

Added phase-06-diagnostic/trace_outliers.py. One invocation, exactly 66 requests: 23 unwrapped then 43 stage-traced, excluding three warmups per mode from statistics. No retry loop, no repeated acceptance run, and no concurrent agent-launched checks. Raw evidence: [phase-06-outlier-trace-output.txt](phase-06-outlier-trace-output.txt). Command with project PYTHONPATH=src and bytecode disabled:

```powershell
& './.venv/Scripts/python.exe' -B specs/003-handler-hot-reload/verification/phase-06-diagnostic/trace_outliers.py
```

Exit 0; all 66 responses were HTTP 200, body A. Both modes observe garbage-collection callbacks; “unwrapped” means no stage wrappers, not completely uninstrumented execution. GC was not disabled, forced or retuned. Stage-traced mode wraps loader, invoker, response normalization, Path.resolve/exists/read_bytes, and a temporary loader-local compile binding. Timing uses perf_counter_ns; no CPU-time inference is made.

## Observations

| Mode | Retained requests | Total range ms | Mean ms | Above 5ms |
| --- | --- | --- | --- | --- |
| Unwrapped with GC observer | 20 | 0.3993-2.5717 | 0.550795 | 0 |
| Stage traced with GC observer | 40 | 0.3899-0.4783 | 0.4269275 | 0 |

| Stage (traced mode) | Range ms | Mean ms |
| --- | --- | --- |
| Resolve | 0.1074-0.1663 | 0.124915 |
| Exists | 0.0210-0.0370 | 0.0251375 |
| Read source bytes | 0.0536-0.0747 | 0.0603625 |
| Compile | 0.0375-0.0543 | 0.042570 |
| Entire loader (includes nested stages) | 0.2841-0.3577 | 0.309970 |
| Invoker | 0.0151-0.0298 | 0.0173975 |
| Normalize response | 0.0037-0.0735 | 0.006080 |

The slowest unwrapped sample (index 7, 2.5717ms) overlapped one GC callback interval measured at 0.2861ms. That does not account for the whole request or prove GC caused earlier outliers. No GC interval was recorded within traced requests. GC callback absence does not rule out all runtime/scheduler activity.

## Conclusion and limits

No >5ms spike was reproduced within this fixed run. The prior 20.1003ms off / 5.9510ms on full-suite failures remain valid recorded observations, not waived or replaced by this smaller standalone diagnostic. This fixture is 60 bytes versus 61 bytes in acceptance tests, and it does not reproduce the preceding full-suite workload or a listening server. No OS scheduler, filesystem security-scanner, or lock-contention cause was established.

Single resolution is still visible once per traced load. During this run the entire loader was sub-millisecond, so another production optimization is not supported by the available evidence. Do not disable security tooling, change priorities, cache callables/source, relax limits or rerun until green based on this result.

Wrappers and temporary compile binding were restored; GC callback list, handler registration, coordination and ownership snapshots restored; observer task stopped. Script exited normally through asyncio.run. No live server was launched. Phase 6 tasks remain unchecked.

Recommended next action, for explicit approval: stop speculative optimization and collect the remaining live-server evidence while retaining the unresolved dispatch gate. Continuing evidence collection is not feature acceptance or a budget waiver. Repository-wide quality, unavailable coverage and runtime-matrix gaps remain separate open items.

Official references used: [GC callbacks](https://docs.python.org/3.14/library/gc.html#gc.callbacks) and [performance-counter semantics](https://docs.python.org/3.14/library/time.html#time.perf_counter_ns).
