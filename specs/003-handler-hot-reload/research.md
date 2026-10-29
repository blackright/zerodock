# Research: Handler Hot Reload

**Date**: 2026-10-29
**Scope**: Phase 0 design research only. No tests or benchmarks executed.

## 1. Existing Behavior and Reuse

**Decision**: Preserve module execution per request, existing module identities, configuration-relative paths, and gateway error formatting. Extract shared identity logic rather than build a second naming scheme.

**Rationale**: `engine/loader.py` currently creates and executes a module on every call, and `gateway/app.py` calls it per request. There is no persistent callable cache. The parser already resolves relative paths and rejects initially missing handlers. Existing errors and invocation contracts need no redesign.

**Alternatives considered**: Persistent module caching would change globals and top-level side effects; rejected by user decision. Removing `sys.modules` alone does not guarantee fresh bytecode execution.

## 2. Fresh Source Execution

**Decision**: In reload mode, read source bytes on each load, create the module through the existing importlib spec mechanism, compile bytes with the original resolved filename and `dont_inherit=True`, then execute in the module namespace. Validate the selected entrypoint before returning. Keep the original importlib execution path when reload is disabled.

**Rationale**: Compiling source directly avoids reliance on timestamp-based `.pyc` freshness. Bytes preserve Python's source-encoding handling. The resolved filename retains traceback and breakpoint locations. Importlib-created metadata remains available. This is a proposed design to validate, not a claim of debugger equivalence already tested. See [Python 3.10 compile](https://docs.python.org/3.10/library/functions.html#compile) and [module creation](https://docs.python.org/3.10/library/importlib.html#importlib.util.module_from_spec).

**Alternatives considered**: Deleting `.pyc` files introduces filesystem mutations and permission/race issues; changing global bytecode settings affects unrelated code. `importlib.reload()` reuses module dictionaries, has reference/thread-safety caveats, and is not a replacement for current execution semantics. See [reload caveats](https://docs.python.org/3.10/library/importlib.html#importlib.reload).

**Verification**: Same-length edits with restored timestamps and existing bytecode; encoding cookies/BOM; future-import behavior; tracebacks and debugger source filenames; failed import/entrypoint cleanup. No transitive helper reload is implied.

## 3. Exact-Path Content Polling

**Decision**: Default to 100ms between completed scans, one outstanding scan per observer, reading each deduplicated target and hashing contents with SHA-256. Metadata is diagnostic only and must not gate content reads. A scan returns fingerprints or missing/unreadable states; it never executes user modules. Run scan I/O through bounded standard-library thread offloading.

**Rationale**: Exact-path content reads detect same-size/same-timestamp changes and naturally revisit replaced or recreated files. Keeping only digests/status bounds retained history. The 100ms interval leaves nominal headroom for the 500ms target but does not guarantee it under arbitrary load. [Python documents thread offloading](https://docs.python.org/3.10/library/asyncio-task.html#asyncio.to_thread) for blocking I/O.

**Alternatives considered**: Metadata-only polling misses edits; recursive watchers broaden scope; optional `watchfiles` adds dependency/platform surface and was not selected by the user. Do not add mandatory stability/debounce delays: partial-write requests may fail, and subsequent scans must recover.

**Verification**: Identical scans do not invalidate twice. A changed digest or availability transition invalidates once per observer transition; continued missing/unreadable status does not spam logs. Distinct app observers may each invalidate the same module safely.

## 4. Coordination and Registry Lifetime

**Decision**: All loader and invalidator operations use a process-wide per-module reentrant lock lease. A short registry guard obtains a strong entry reference and increments an active-user count before releasing the guard. Active holders/waiters pin the same entry; watcher ownership also pins it. Remove an entry only when both counts are zero. Never wait on the per-module lock while holding the registry guard.

**Rationale**: An application-local lock cannot coordinate two app instances or direct loader callers sharing `sys.modules`. Leases prevent removal/recreation races; reentrancy accommodates nested same-thread activity. Hold the per-module lock during module creation, top-level execution, entrypoint validation, and invalidation, not handler invocation or an await. Cleanup removes a registry module only when its object identity matches the failing load.

**Alternatives considered**: A permanent lock dictionary grows with historical paths; app-local locks leave races; a global execution lock serializes unrelated files. No design can protect callers that directly import or mutate loader-owned `sys.modules` entries outside ZeroDock; those operations are unsupported.

**Boundary**: Top-level handler code already runs synchronously in the gateway thread. Preserve that behavior rather than moving execution into worker threads. Watcher scan workers do not mutate module state; invalidation occurs through the coordinated loader API after scan completion. Arbitrary blocking imports can delay observation, outside the stated normal scheduling target.

## 5. Application Lifespan and Shutdown

**Decision**: Use an asynchronous lifespan context. Capture an initial baseline, perform an immediate comparison scan, and start observation before yielding startup readiness. Fatal observer setup failures abort startup; per-file missing/unreadable transitions after initial config validation are recoverable. On exit, signal stop, wake interval waiting, await the current scan and observer, and release watcher ownership.

**Rationale**: FastAPI recommends lifespan for paired startup/shutdown ownership. No tasks start during import or app construction. Cancelling an await around worker I/O is not proof that the underlying work ended: retain the worker future/task, protect it from premature cancellation, and drain it during shutdown. Do not shut down the shared event-loop executor. See [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/) and [asyncio shielding](https://docs.python.org/3.10/library/asyncio-task.html#shielding-from-cancellation).

**Alternatives considered**: Untracked fire-and-forget tasks and cancel-only shutdown can leak work. Dedicated watcher subprocesses violate the approved architecture. Filesystem operations that hang indefinitely cannot be forcibly interrupted safely with this design; arbitrary stalled/remote filesystems are outside the normal-local-filesystem target and this limit must be documented.

## 6. HTTP Testing and Performance Evidence

**Decision**: Explicitly enter application lifespan in async HTTPX tests; use controllable scan completion events for correctness and a separate bounded real-clock measurement for detection. Use an existing dependency's lifespan context rather than adding a new mandatory package.

**Rationale**: HTTPX does not trigger ASGI startup/shutdown automatically. Existing ASGI benchmark construction therefore cannot prove watcher startup or cleanup. See [HTTPX ASGI lifecycle](https://www.python-httpx.org/advanced/transports/#asgi-startup-and-shutdown).

**Alternatives considered**: Arbitrary sleeps are flaky; mocked clocks alone do not prove the 500ms target. In-process requests do not prove unchanged server PID/port. A separately approved real-server validation will cover that.

**Delegated repository review**: A read-only research agent independently confirmed import-time app construction, existing HTTPX tests without lifespan entry, synchronous execution on the event loop, and process-wide module ownership. Incorporate explicit `app.router.lifespan_context(app)` tests, partial-startup cleanup, and worker-gated cancellation tests that verify shutdown waits before releasing ownership. Exercise two apps on distinct event loops; process-wide coordination must not use an event-loop-bound `asyncio.Lock`. Stay compatible with Python 3.10 rather than requiring `TaskGroup`.

**Measurement decision**: Preserve current config-plus-app <100ms and best-of-three ASGI <30ms checks. Separately record process readiness, lifespan-inclusive startup, isolated dispatch, changed-file request cost, detection, and actual current RSS for both modes. Peak process memory is not idle RSS; report collection method/platform explicitly. Use representative tiny handlers and disclose file count/bytes, environment, repetitions, and raw results. Do not quietly substitute benchmark definitions or waive constitutional budgets.

## Resolution Summary

No scope clarification remains. The 100ms interval and coordination mechanisms are implementation design values to verify, not new user-facing options. Runtime measurements, platform checks, and red/green test evidence are deferred until implementation is authorized. All six approved improvements map to these decisions; none expands into helper reload, persistent caching, configuration reload, or production worker orchestration.
