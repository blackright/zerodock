# Phase 6 Bounded Dispatch Diagnostic

**Date**: 2026-10-29 (Europe/Budapest)
**Status**: Diagnostic complete; acceptance remains open. No production or acceptance-test changes.

## Approval, reuse and scope

The user approved a bounded profile to investigate measurement overhead versus actual dispatch cost, not fixes or threshold changes. Reviewed Phase-Builder-Agent.md, the actual benchmark, loader, and gateway. Reused direct ASGI scope, explicit lifespan, real source loading, and existing invocation/response contracts. Preserved per-request execution and all limits. No dependency installation, live server, Git commands/data access, or automatic optimization.

Added only a disposable diagnostic script/config/handler under phase-06-diagnostic/. The fixture is 60 bytes as written, whereas the benchmark fixture is 61 bytes; it has equivalent tiny-handler behavior but is not byte-identical. This diagnostic is not a replacement benchmark or full-suite rerun.

Command, with project PYTHONPATH=src and bytecode disabled:

```powershell
& './.venv/Scripts/python.exe' -B specs/003-handler-hot-reload/verification/phase-06-diagnostic/profile_dispatch.py
```

Exit 0. Raw records, stage timings, profiler tables and cleanup assertions: [phase-06-diagnostic-output.txt](phase-06-diagnostic-output.txt).

## Bounded method

One reload-enabled app, one configured handler, no source edits during execution. Four modes, each exactly 23 requests (3 warmups excluded, 20 retained): unwrapped; invoker timing wrapper matching the benchmark concept; loader plus invoker timing wrappers; cProfile with wrappers removed. All 92 responses were HTTP 200 with body A. No retries-until-green or concurrent agent-launched checks.

Wall times use perf_counter_ns. thread_time_ns was recorded as a diagnostic comparison. In practice thread CPU samples were quantized to 0 or 15.625ms despite nominal clock resolution reporting; they cannot separate sub-5ms scheduling delay from CPU work on this run. OS activity was not independently controlled.

| Mode | Wall range ms | Wall mean ms | Samples above 5ms |
| --- | --- | --- | --- |
| Unwrapped | 3.9049-8.7056 | 5.643265 | 10/20 |
| Invoker wrapper | 4.6728-14.2291 | 7.093115 | 16/20 |
| Loader + invoker wrappers | 3.6909-6.4142 | 4.695915 | 6/20 |
| cProfile | 5.9986-22.0566 | 8.998855 | 20/20 |

With stage wrappers: loader 3.0820-5.7113ms, mean 3.87827ms; invoker 0.0829-1.1201ms, mean 0.15481ms. The invoker-only mode showed an additional 3.8091ms outlier. Different modes execute sequentially under changing conditions, not a randomized controlled experiment: subtracting their means does not isolate wrapper overhead. cProfile timings include profiling overhead and are not acceptance measurements.

## Findings and limits

1. Unwrapped requests also exceeded 5ms. The invoker timing wrapper alone cannot explain every observed overrun. This does not prove why the earlier specific full-suite sample took 5.3948ms.
2. The loader was the largest measured stage in the stage-wrapper run. cProfile ranked load_handler at about 0.132s cumulative out of 0.179s in FastAPI application calls for 20 requests. Nested cumulative values must not be summed.
3. Path resolution is a concrete candidate: 40 Path.resolve calls for 20 loads (about 0.080s cumulative under profiling). Windows nt._getfinalpathname was the largest internal-time entry (80 internal calls, about 0.069s). File open/read and compilation also contribute.
4. Actual code confirms load_handler resolves its path, then handler_module_name resolves that already-resolved path again. This is duplicated canonicalization, not evidence that all path resolution can safely be removed or cached.
5. Per-request fresh source compilation and execution are approved behavior. Persistent module/callable caches, stale bytecode fallback, disabling polling, global cache changes, or relaxed limits are not proposed.

## Proposed next step — requires approval

Make one narrow optimization: extract a private identity formatter for an already-resolved path; keep public handler_module_name resolving caller input as before; let load_handler reuse its existing resolved path for identity hashing. Preserve the exact SHA-256/string identity algorithm, canonicalization semantics, locks, invalidation, freshness, and per-request execution. No identity cache or path cache.

Before changing production code, add regression coverage proving one canonical resolution on a load, unchanged public-helper canonicalization, and unchanged identity/loading/failure behavior. Run targeted loader/watcher/HTTP regressions and the unchanged performance checks sequentially. Report any remaining budget failures without expanding the fix. This is a candidate improvement, not a guaranteed solution or an already-authorized change.

## Cleanup and remaining gates

Both timing wrappers restored. Observer task stopped; module, coordination, and ownership snapshots restored. One shared default-executor thread (asyncio_0) existed before asyncio.run exited; that is shared infrastructure, not a surviving app-owned observer. Process exit was normal; no live server was launched. No GUI/IDE claims, coverage result, or full feature acceptance follow from this diagnostic. T041-T048 remain unchecked.

Official guidance: [Python cProfile](https://docs.python.org/3.14/library/profile.html) explicitly distinguishes profiling from benchmarking; [thread CPU clock](https://docs.python.org/3.14/library/time.html#time.thread_time_ns) measures CPU time rather than elapsed waiting. The coarse observed CPU samples limit its usefulness here.
