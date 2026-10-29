# Phase 5 / US3: Compatibility and Clean Shutdown

**Date**: 2026-10-29 (Europe/Budapest)
**Scope**: T031-T040 only.
**Status**: Implemented, verified, and approved by the user on 2026-10-29. T031-T040 are checked complete. Phase 6 has not started and is not authorized. Approval does not imply additional manual test observations or waive existing budget findings.

## Approval and Codebase Review

The user approved test-first Phase 5 lifecycle/compatibility work, fixes to confirmed gaps, focused regressions and existing dispatch/error checks, changed-file quality checks, a controlled debugger check, and this report. The governing phase rules, task definitions, actual loader/watcher/app/CLI/server paths, fixtures, and existing tests were inspected. No applicable `AGENTS.md` or extension hook configuration was found in the inspected paths.

| Existing area | Reuse, replace, or preserve decision |
| --- | --- |
| Content polling, fingerprints, exact target paths, interval and revision transitions | Reuse unchanged |
| Loader module identities, reentrant leases, weak ownership metadata and owner counts | Preserve; new two-app/distinct-loop tests verify the existing implementation |
| CLI/server signatures, defaults and option forwarding | Preserve without source edits; legacy positional calls and unsupported top-level reload behavior verified |
| Per-request module execution and global initialization | Preserve in both modes, including direct loader calls after watcher shutdown |
| Worker drain helper | Reuse its shielded completion behavior; put whole cleanup behind a retained shutdown task |
| Startup/shutdown coordination | Replace racing lifecycle paths with serialized lifecycle operations and stop checks during initialization |
| Lifespan exception handling | Extend to preserve the primary application error/cancellation if cleanup also fails |
| Source filenames and debugger support | Preserve source filenames; fix confirmed stale debugger source after same-metadata saves with targeted line-cache eviction |

No Git operations or Git data/configuration access occurred. No dependencies, CLI options, config fields, routes, cloud adapters, release changes, or unrelated optimizations were added. Existing performance-budget findings were not waived or repaired.

## Files Changed

- `src/zerodock/engine/watcher.py`: per-instance lifecycle serialization, tracked shared shutdown task, startup stop checks, cleanup that drains external scans even after observer failure, and one-time failure reporting.
- `src/zerodock/gateway/app.py`: preserve the primary exception/cancellation while recording a secondary cleanup failure.
- `src/zerodock/engine/loader.py`: clear only the reload-enabled handler's exact and normalized debugger source-cache keys before executing its new source.
- `tests/unit/test_cli.py`: legacy positional calls, existing option values, default forwarding, and top-level flag rejection.
- `tests/unit/test_loader.py`: controlled native pdb checks, fresh listed source after same-metadata edits, and targeted cache-isolation coverage.
- `tests/unit/test_watcher.py`: cancellation/worker gates, open-file drain checks, overlapping lifecycle calls, terminal observer errors, shared executor preservation, and repeated cleanup.
- `tests/integration/test_hot_reload.py`: disabled/import-time behavior, external config paths, startup validation, module globals, repeat lifespans, same/different-loop shared apps, primary error preservation, event/context/response contracts, and async timeout cancellation.
- `specs/003-handler-hot-reload/verification/us3.md`: this evidence and user walkthrough.

CLI/server source, configuration parsing, shared fixtures, real handlers, and existing integration test files were inspected/reused rather than changed unnecessarily.

## Confirmed Failures Before Fixes

After writing tests and before changing production code:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit/test_loader.py tests/unit/test_watcher.py tests/unit/test_cli.py tests/integration/test_hot_reload.py -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-05-red-temp -q --tb=short
```

Exit code 1: **8 failed, 130 passed in 113.65s**. The confirmed gaps were:

1. Cancelling shutdown could release module ownership while an external scan still held an open file.
2. A stop request during startup could be followed by a late observer creation.
3. Overlapping starts could register duplicate owners and observer tasks.
4. An already reported terminal observer exception or cancellation could escape through ordinary cleanup and skip draining an external scan.
5. A cleanup exception could replace the original application error or cancellation.

The first red run was noticeably slower than earlier runs. These suite timings are observations, not controlled application performance measurements or proof of a speed improvement after fixes.

Existing behavior worth preserving already passed: default CLI/programmatic compatibility, unchanged per-request globals, external configuration resolution, initial missing-file validation, shared handler ownership across apps and event loops, basic pending-read cancellation, event/context/response behavior, async timeout mapping, and native breakpoints.

## Lifecycle Fixes and Evidence

`HandlerWatcher` now serializes lifecycle work with an instance-local async lock. A stop request sets the stop event immediately; initialization checks that event before committing startup. Concurrent starts cannot create a second registration. A pending stop prevents a new start from clearing the stop request prematurely.

Public `stop()` calls share a retained shutdown task. A caller cancelling its own wait does not cancel that cleanup task. Cleanup waits for the observer, then the scan lock, before closing owner contexts. Cancellation is propagated to the caller only after draining completes. Terminal observer errors remain visible in logs but do not cancel the caller's ordinary cleanup or bypass pending file reads.

Startup failures use protected cleanup while retaining lifecycle ownership. Application lifespan handling keeps an original application error/cancellation primary if another error occurs during cleanup; the secondary error is logged. Ordinary requested stop is not reported as an unexpected observer failure. Terminal failures are reported once.

### Worker and File-Handle Checks

Event-gated workers held real temporary source files open. Tests established that:

- Repeated cancellation of a stop caller leaves cleanup pending and owner registration intact until the read is released.
- A cancelled scan or cancelled initial scan retains its worker and open file until completion, then propagates cancellation.
- A failed observer does not bypass draining a different outstanding scan.
- No late invalidation occurs after stop while a gated scan completes.
- Once stop completes, gated handles are closed and owner/lease state is released.
- A long polling interval is awakened by stop rather than delaying shutdown for that interval.
- The shared default executor is not shut down; another `asyncio.to_thread()` operation succeeds after stopping the watcher.
- Repeated and concurrent stop calls complete without duplicate owner release.

The executor-shutdown spy is scoped inside its test body and restored before pytest closes its event loop. No test replaces event-loop cleanup permanently.

### Filesystem Limit

Python cannot forcibly interrupt an already-running filesystem call in an offloaded thread. Stop deliberately drains it rather than declaring cleanup finished early. Shutdown can therefore wait indefinitely on a hung filesystem; there is no claimed hard shutdown deadline. This limitation is stated in the watcher stop docstring. Tests use controlled release events with failure timeouts rather than pretending thread cancellation kills I/O.

## Debugger Discovery and Fix (T040)

A separate same-size/same-timestamp debugger test found an additional gap: the updated handler executed B correctly, but pdb's `list` command could still show the old `return 'A'` source line. Its red run was **1 failed, 58 deselected in 2.85s** before the source-cache fix.

The reload-enabled loader now removes only that file's exact and `os.path.normcase()` source-cache keys before executing freshly compiled code. Both spellings matter for Windows debugger canonicalization. Default loading does not clear the cache, unrelated files are not touched, and no global cache clear or dependency eviction is introduced.

This uses the filename-keyed `linecache.cache` implementation mapping, whose shape and metadata-only validation were checked against official CPython 3.10 and 3.14 source. It is not presented as a new public linecache API or proof of every Python implementation's compatibility. Runtime verification here is on the installed CPython 3.14.6; the broader supported-version matrix remains Phase 6.

Controlled pdb runs used actual temporary handlers containing `breakpoint()`, a scoped breakpoint hook, `readrc=False`, and in-memory command input/output, with no visible window or external service. They verified:

- Both default and reload-enabled handlers stop at their original source path.
- `p event['name']` displays `phase5-debug`, and `continue` returns the expected handler result.
- After a same-metadata A-to-B save and invalidation, the function returns B and `list` shows `return 'B'`, not stale A.
- Existing traceback filename/line checks remain passing.
- Unrelated source-cache entries remain unchanged, and default-mode source-cache behavior is preserved.

The targeted debugger/traceback green run passed **4 cases in 0.56s**; a later cache-isolation case is included in the final focused run. No interactive IDE session or user-reported manual debugger result is claimed.

## Compatibility and Shared-Application Evidence

- Importing the gateway and constructing apps start no observers. Disabled lifespan never constructs one.
- Config paths outside the working directory retain the existing config-relative handler resolution.
- Configuration loading still rejects initially missing handler files in both modes.
- Top-level module side effects happen on each request; handler globals are recreated per request in both modes. Direct loading after shutdown remains usable.
- Repeated app lifespans release the old observer and create a fresh one when enabled.
- Two apps sharing a handler have two owner registrations. Stopping one leaves the other's registration and module intact; the survivor reloads saved source.
- Two apps running on distinct event loops in separate threads share the same per-module coordination safely. The first can shut down while the second still refreshes and serves the handler.
- Existing CLI options and legacy positional server calls retain their values. Top-level `zerodock --reload` remains unsupported; opt-in stays on `dev`.
- Sync/async HTTP handlers retain methods, query/body data, invocation context, status codes, and headers in both modes.
- Async timeout tests verify the configured timeout argument, actual coroutine cancellation, and the existing HTTP 504 response. A scoped wrapper shortens only the test handler's deadline to 5ms; these are controlled correctness tests, not measurements of the configured one-second wall-clock deadline. No new synchronous timeout guarantee is claimed.

## Final Focused Regression Results

After the lifecycle fixes, the targeted shutdown/error-preservation group passed **10 tests, 56 deselected in 4.43s**.

Final focused suite: **140 passed in 16.72s**, exit code 0:

| File | Cases |
| --- | ---: |
| `tests/unit/test_loader.py` | 60 |
| `tests/unit/test_watcher.py` | 31 |
| `tests/unit/test_cli.py` | 14 |
| `tests/integration/test_hot_reload.py` | 35 |

The final run used an inline evidence plugin, a fresh `phase-05-final-temp` base, and snapshots before/after pytest. It reported:

```text
Handler module snapshot restored: True
Coordination snapshot restored: True
Ownership snapshot restored: True
New live threads after cleanup: []
Trace function restored: True
Breakpoint hook restored: True
Python 3.10 syntax parsing: PASS (not a runtime test)
```

The retained small-workload automatic detection case measured **133.8441ms** for one 61-byte handler. This does not replace Phase 6 performance acceptance. The slowest reported test call was 0.30s; the total 16.72s is suite time, not handler or startup latency.

### Existing Dispatch and Error Tests

The original `tests/integration/test_gateway_dispatch.py` and `tests/integration/test_error_handling.py` were run unchanged. All five existing cases passed. That final command also reran the executor-preservation test after a test-only formatting correction: **6 passed in 2.58s**. The repeated executor case is already part of the 140, so this is **145 distinct passing tests**, not 146.

These checks cover existing GET/POST behavior, root configuration dispatch, structured handler errors, and gateway survival after a handler crash. No full repository suite or unrelated benchmarks were run.

## Changed-File Quality Checks

Final Ruff lint, Ruff format checking, and mypy targeted only these seven changed Python files:

```text
src/zerodock/engine/loader.py
src/zerodock/engine/watcher.py
src/zerodock/gateway/app.py
tests/unit/test_loader.py
tests/unit/test_watcher.py
tests/unit/test_cli.py
tests/integration/test_hot_reload.py
```

Final results: **all lint checks passed**, **7 files already formatted**, and **no mypy issues in 7 source files**. Commands used the existing venv with `-B -m ruff check --no-cache`, `-B -m ruff format --check --no-cache`, and `-B -m mypy --follow-imports=silent --cache-dir=specs/003-handler-hot-reload/verification/phase-05-mypy-cache`, followed by the listed files.

Initial formatting/long-line findings were corrected only in touched test files. Python 3.10 syntax parsing was performed on the changed files using the available Python 3.14 interpreter; it is not a Python 3.10 runtime result. Explicit sandbox escalation was used for the existing venv launcher rather than bypassing restrictions.

## Task Review Status

| Task | Actual result | Review state |
| --- | --- | --- |
| T031 | Legacy CLI/server calls, defaults, existing options and unsupported flag tests pass | Approved |
| T032 | Worker-gated cancellation, startup/stop races, closed handles, interval wakeup, repeated stop and executor preservation tests pass | Approved |
| T033 | Disabled/import-time behavior, paths/validation, globals, repeated lifespans and shared apps/loops verified | Approved |
| T034 | Retained protected cleanup and serialized lifecycle implemented; hung-filesystem limit documented | Approved |
| T035 | Lifespan preserves primary errors/cancellation while recording secondary cleanup errors | Approved |
| T036 | Existing lease/owner retirement reused and verified across app shutdown and distinct loops; no unnecessary registry rewrite | Approved |
| T037 | Existing CLI/server implementation reused unchanged and proven compatible | Approved |
| T038 | Per-request side effects/globals and post-shutdown direct loading pass in both modes | Approved |
| T039 | Focused regressions, worker/file-handle assertions and module/thread cleanup evidence recorded | Approved |
| T040 | Controlled pdb/source/traceback checks, event/context/response/async-timeout tests and original dispatch/error tests pass | Approved |

## User Playground Test

### Automated Check

1. Open PowerShell in `C:\dev\python\zerodock`.
2. Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit/test_loader.py tests/unit/test_watcher.py tests/unit/test_cli.py tests/integration/test_hot_reload.py -p no:cacheprovider -q
```

3. Expect **140 passed**. Do not reuse a saved fixed `--basetemp` directory; omitting it lets pytest choose a fresh location.

### Manual Stop and Restart

1. Start the existing disposable gateway, preserving any previous edits to its handler:

```powershell
$env:PYTHONPATH = "$PWD\src"
& '.\.venv\Scripts\python.exe' -B -m zerodock.cli dev --reload --config specs/003-handler-hot-reload/verification/phase-03-live/serverless-local.yaml --port 8088
```

2. Open `http://127.0.0.1:8088/sync` and `/async`; expect valid responses for the fixture's current version.
3. Press Ctrl+C in the server terminal and wait for shutdown to finish. Run the same command again. Expect the same port to be available without an address-in-use error. A new PID after this deliberate stop/restart is normal.

### Optional Manual Debugger Check

Temporarily add `breakpoint()` inside the disposable `sync_handler`, save, and request `/sync`. The browser waits while the terminal shows `(Pdb)`. Type `p event`, then `continue`. Expect the request to finish. Remove your temporary breakpoint and save afterward; stop the server with Ctrl+C only after leaving the debugger. This manual check is offered for user review and is not claimed as already performed.

Record any issue in `Troubleshoot.md` and report it. Approval of Phase 5 permits its task checkmarks only; Phase 6 still requires separate authorization.

## Remaining Limits and Unstarted Work

No full-suite run, coverage installation, release/package change, README reconciliation, performance-budget optimization, or broader platform matrix was undertaken. Coverage tooling remains uninstalled, and the Phase 1 memory/startup findings remain unresolved and unwaived. Only the available Windows/CPython 3.14.6 runtime was exercised. GUI IDE debugging and user manual tests are not assumed from automated results.

No live HTTP server was launched by the agent in Phase 5. HTTP tests used actual application lifespan and in-process ASGI requests; the separately approved pdb check ran under controlled command input. All test-owned worker/loop threads were joined or drained. Generated pytest files and mypy cache remain under fresh phase-specific verification paths; no recursive deletion was performed.

## Official References Checked

- [Python cancellation and shielding](https://docs.python.org/3.14/library/asyncio-task.html#shielding-from-cancellation) and [Python 3.10 shielding](https://docs.python.org/3.10/library/asyncio-task.html#asyncio.shield): protecting owned work while propagating caller cancellation.
- [Asyncio thread/loop boundaries](https://docs.python.org/3.14/library/asyncio-dev.html#concurrency-and-multithreading): keep watcher synchronization instance/loop-local and shared module coordination thread-safe.
- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/): paired startup/shutdown and failure propagation.
- [Python pdb](https://docs.python.org/3.14/library/pdb.html#pdb.Pdb): controlled breakpoint interaction and source inspection.
- [Linecache documentation](https://docs.python.org/3.14/library/linecache.html), [CPython 3.14 implementation](https://raw.githubusercontent.com/python/cpython/3.14/Lib/linecache.py), and [CPython 3.10 implementation](https://raw.githubusercontent.com/python/cpython/3.10/Lib/linecache.py): cached source lines and size/mtime validation explain why same-metadata source needs targeted eviction.
