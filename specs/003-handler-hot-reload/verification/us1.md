# Phase 3 / US1: Saved Handler Refresh

**Date**: 2026-10-29 (Europe/Budapest)
**Scope**: T009-T020 only.
**Status**: Implemented and verified for the Phase 3 MVP; awaiting user approval. Checkboxes remain unchecked. Phase 4 has not started.

## Approval and Codebase Alignment

The user approved Phase 3 implementation, test-first focused loader/watcher/CLI/HTTP tests, changed-file quality checks, detection measurement, disposable live-server verification, and evidence reports. `Phase-Builder-Agent.md`, actual code, task definitions, design contracts, and project configuration were inspected before changes. No applicable `AGENTS.md` or extension hook configuration was found in the inspected paths. No Git commands or Git data/configuration access occurred.

| Existing area | Reuse / preserve / extend decision |
| --- | --- |
| Phase 2 module naming, leases, owner contexts, and invalidation | Reuse; no second identity or coordination scheme |
| Module execution | Preserve per-request semantics in both modes; default mode retains importlib execution |
| Reload source loading | Extend with direct compilation of bytes using original filename and `dont_inherit=True`; do not delete bytecode or change global bytecode settings |
| Existing route dispatch, events, contexts, errors, normalization, timeouts | Preserve; only forward the reload mode to the loader |
| Application lifecycle | Extend with an async lifespan owning the optional observer; no import-time or app-construction tasks |
| Server/CLI | Preserve existing options and positional calls; add keyword-only default-false library options and `dev --reload` |
| Phase 2 temporary factories and worker gates | Reuse without editing `tests/conftest.py` |

No external watcher package, persistent callable/module cache, project-wide scan, dependency reload, YAML reload field, new HTTP endpoint, process-restart mode, or unrelated optimization was introduced.

## Implementation Written

### Loader

`src/zerodock/engine/loader.py` adds keyword-only `reload=False`. Reload-enabled calls read current source bytes and compile them into the existing importlib-created module namespace. Python source encoding, explicit future annotations, module metadata, source filename, and traceback line locations are covered by focused tests. Calls still produce new module globals/callables every time. Existing Phase 2 cleanup and coordination remain in use.

### Polling

`src/zerodock/engine/watcher.py` adds an app-owned `HandlerWatcher`. It canonicalizes/deduplicates exact configured paths and hashes source contents even if metadata is unchanged. Reads stream in 64KiB chunks off-loop; stored revisions contain status/digest/error category, not source histories. An instance-local async lock serializes scans. Its background loop waits 100ms between completed scans and schedules at most one scan at a time.

Readable revision changes invoke the shared targeted invalidation API, coalescing unchanged observations and multiple saves before a scan. Startup records a baseline and immediately reconciles again before readiness. Basic lifecycle stop wakes interval waiting, drains owned work, and releases Phase 2 owner registrations. The implementation also represents missing/unreadable states; their full invalidation/error-recovery acceptance coverage belongs to Phase 4, not this MVP claim.

Logs inherit the existing Uvicorn error-logger hierarchy through `uvicorn.error.zerodock.reload`. Info logs report enablement/count and invalidation identities; debug logs list target paths. Normal unchanged scans emit no reload messages. Tests confirm handler source text does not appear in change logs.

### Application, Server, and CLI

`src/zerodock/gateway/app.py` owns observation inside FastAPI lifespan and forwards reload mode per request. Disabled mode creates no observer. `src/zerodock/gateway/server.py` forwards the option into app creation, not Uvicorn restart reload. `src/zerodock/cli.py` adds `zerodock dev --reload`, with existing implicit startup remaining disabled by default.

The new API defaults are keyword-only as specified. Uvicorn continues receiving the app object with existing host/port/log-level options and no `reload=True` setting.

## Test-First Evidence

Existing project venv: Python 3.14.6 on Windows 11, pytest 9.1.1. No package installation or upgrade occurred. Explicit sandbox escalation was used for the existing Python launcher, as in prior phases.

### Red Run

After writing tests and before any production reload implementation:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit/test_loader.py tests/unit/test_watcher.py tests/unit/test_cli.py tests/integration/test_hot_reload.py -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-03-red-temp -q --tb=line
```

Exit code 1: **25 failed, 31 passed, 7 errors in 1.74s**. Expected failures showed missing reload arguments/options, missing forwarding, and the absent watcher module. One new negative positional-argument test already passed because the pre-existing two-argument API rejected a third argument; it is not claimed as a red case. All Phase 2 tests remained passing.

### Green Runs

First implementation run: **63 passed in 1.64s**, with automatic invalidation observed at **112.2849ms**. A subsequent traceback-location test increased the suite to 64 cases. Initial import/layout findings were fixed only in touched files.

Final focused run used the same four test paths with a fresh `phase-03-final-temp` base, explicit `-s`, and in-process cleanup snapshot assertions: **64 passed in 1.69s**, exit code 0. Automatic invalidation was **108.9986ms**.

| Category | Cases | Coverage |
| --- | ---: | --- |
| Loader | 40 | Phase 2 regressions plus stale bytecode, source encodings/BOM, future flags, compile inputs, metadata/tracebacks, entrypoints, per-request execution, keyword-only mode |
| Watcher | 7 | Canonical deduplication, fingerprints, same-metadata detection, duplicate coalescing, latest save, unrelated-file exclusion, serialized off-loop workers, startup reconciliation, interval validation |
| CLI/server contracts | 10 | Opt-in/default parsing and forwarding, implicit default startup, app versus Uvicorn mode, keyword-only library interfaces |
| Lifespan/HTTP | 7 | Sync/async refresh, same-timestamp bytecode, shared entrypoints and different-file isolation, default-mode forwarding, automatic detection |

Correctness tests use explicit scan acknowledgements and event gates. `asyncio.sleep(0)` is used only to yield scheduling in the concurrency test, not as a guessed elapsed-time wait. The automatic-detection case intentionally uses the real background loop and real monotonic clock, not a manual scan.

## Detection Measurement Boundary

Workload: one configured temporary handler, **61 source bytes**, normal local NTFS filesystem, current project dependencies, 100ms polling interval, no concurrent handler load. Timing starts immediately after the completed source write and ends after the coordinated invalidation call returns and sets a test event. The following HTTP request then returns B.

```text
first green run: 112.2849ms
final green run: 108.9986ms
```

Both samples meet the <=500ms target for this disclosed workload. Two samples are not an unlimited-workload, percentile, network-filesystem, or stalled-event-loop guarantee. Handler top-level execution remains synchronous as before; blocking user code can delay observation. No watcher-wide performance compliance or memory improvement is claimed.

## Changed-File Quality Checks

Ruff lint and format checks and mypy targeted these nine files:

```text
src/zerodock/engine/loader.py
src/zerodock/engine/watcher.py
src/zerodock/gateway/app.py
src/zerodock/gateway/server.py
src/zerodock/cli.py
tests/unit/test_loader.py
tests/unit/test_watcher.py
tests/unit/test_cli.py
tests/integration/test_hot_reload.py
```

Commands used the existing venv with `-B -m ruff check --no-cache`, `-B -m ruff format --check --no-cache`, and `-B -m mypy --follow-imports=silent --cache-dir=specs/003-handler-hot-reload/verification/phase-03-mypy-cache` followed by those file paths.

Final results: **all lint checks passed**, **9 files already formatted**, **no mypy issues in 9 source files**. The initial lint run reported three import-order and eight long-line findings; the initial format check requested layout changes in six files. Those were corrected with focused patches. No unrelated source files were reformatted.

## Resource and Compatibility Checks

The final test process captured snapshots before and after pytest:

```text
Handler module snapshot restored: True
Coordination snapshot restored: True
Ownership snapshot restored: True
New live threads after test cleanup: []
Python 3.10 syntax parsing: PASS (not a runtime test)
```

These checks establish cleanup for the Phase 3 tested paths. They do not replace Phase 5's planned cancellation/failure/partial-startup/shared-app hardening tests. Source-filename and traceback checks are automated; no interactive IDE visual-debugging session is claimed.

The original real handler/configuration, parser, and existing performance-test file were not edited. Source writes were limited to the five feature source files; test changes were limited to the four files above. Two disposable live-server fixture files were added under this verification directory. All generated test files/caches remain under fresh phase-specific verification paths; no recursive deletion was performed.

## Phase Task Review

| Task | Verified result | Status |
| --- | --- | --- |
| T009 | Freshness, encoding, metadata, traceback, per-request and entrypoint regressions pass | Awaiting approval |
| T010 | Deterministic exact-path polling and worker-serialization tests pass | Awaiting approval |
| T011 | CLI/server/library contracts pass | Awaiting approval |
| T012 | Actual lifespan and HTTP refresh/isolation tests pass | Awaiting approval |
| T013 | Fresh bytes compile in reload mode; old execution path remains default | Awaiting approval |
| T014 | Deduplicated, bounded off-loop content scanning added | Awaiting approval |
| T015 | Readable revision invalidation/coalescing and scoped logging added | Awaiting approval |
| T016 | Basic app-owned baseline/reconciliation/start/stop integration added | Awaiting approval |
| T017 | Server forwards app option without Uvicorn restart reload | Awaiting approval |
| T018 | Default-disabled `dev --reload` implemented | Awaiting approval |
| T019 | 64 focused tests and two disclosed detection samples pass | Awaiting approval |
| T020 | Real sync/async A-to-B responses preserve PID and port; server stopped | Awaiting approval; see live report |

## Remaining Scope and Budget Findings

Phase 4 error/recovery/atomic-save scenarios, Phase 5 cancellation/shared-app compatibility hardening, and Phase 6 full regressions/documentation/performance/coverage acceptance remain unstarted. No full suite, existing benchmark rerun, coverage installation, whole-feature memory assessment, or other-platform runtime execution occurred in this phase. The Phase 1 >50MB memory finding and full-process readiness figures are not resolved or waived by passing these MVP tests.

## User Playground Test

1. Open PowerShell in `C:\dev\python\zerodock` and run:

```powershell
$env:PYTHONPATH = "$PWD\src"
& '.\.venv\Scripts\python.exe' -B -m zerodock.cli dev --reload --config specs/003-handler-hot-reload/verification/phase-03-live/serverless-local.yaml --port 8088
```

2. In another terminal, request `http://127.0.0.1:8088/sync` and `/async`. Both initially report version B because the saved disposable fixture reflects the completed automated run.
3. Edit only `specs/003-handler-hot-reload/verification/phase-03-live/handler.py`, changing both version values from B to C. After an invalidation log, request both routes again. Expect version C and the same PID. Stop your server with Ctrl+C.

If port 8088 is occupied, select another free port and use it consistently. Do not edit the project's real handler. Alternatively, rerun the focused four test files and expect 64 passed. Record any problem in `Troubleshoot.md` and report it. Phase 3 completion awaits user approval; no later phase is authorized by this report.

## Official Documentation Checked

- [Python compile](https://docs.python.org/3.14/library/functions.html#compile): source bytes, filename and compilation flags.
- [Async thread offloading and shielding](https://docs.python.org/3.14/library/asyncio-task.html): background filesystem work and waiting for owned work.
- [Async events and locks](https://docs.python.org/3.14/library/asyncio-sync.html): instance-local scheduling coordination.
- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/): paired startup/shutdown ownership.
- [HTTPX ASGI lifecycle](https://www.python-httpx.org/advanced/transports/#asgi-startup-and-shutdown): explicit lifespan entry in tests.
- [Argparse actions](https://docs.python.org/3.14/library/argparse.html#action): default-disabled boolean CLI flag.
- [Uvicorn programmatic deployment](https://uvicorn.dev/deployment/#running-programmatically): preserve app-object startup without process restart reload.
