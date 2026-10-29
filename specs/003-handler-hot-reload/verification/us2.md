# Phase 4 / US2: Recovery From Saves and Errors

**Date**: 2026-10-29 (Europe/Budapest)
**Scope**: T021-T030 only.
**Status**: Implemented and verified; awaiting user review. Task checkboxes remain unchecked. Phase 5 has not started.

## Authorization and Existing Implementation Review

The user approved Phase 4 tests, targeted recovery fixes, earlier focused reload regressions, changed-file quality checks, and this evidence report. The governing `Phase-Builder-Agent.md`, actual source/tests, phase tasks, failure contract, and constitution were read before implementation. Official documentation was checked before using cancellation/callback and replacement behavior. No applicable scoped `AGENTS.md` or extension hooks were found in the inspected paths.

| Area | Reuse, replace, or preserve |
| --- | --- |
| Existing module identity, leases, per-request execution, and reload source compilation | Reused unchanged |
| Existing failed-import and entrypoint cleanup | Reused; new tests prove it works in both loading modes and preserves newer owned registrations |
| Missing-file failure before module creation | Extended cleanup to remove only the previous loader-owned registration captured for that attempt |
| Watcher missing/unreadable revision representation | Reused; extended transition invalidation and category-aware, non-repeating warning logs |
| Existing 100ms polling and off-loop scanning | Preserved; extracted one internal wait method so retry pacing can be tested deterministically |
| Unexpected observer completion reporting | Extended to include cancellation and an unrequested normal return, not only exceptions |
| Application startup/dispatch/error integration | Inspected and preserved without edits; integration tests verify existing failure propagation and error envelope |
| Existing fixtures and synchronization gates | Reused; no new shared fixture framework |

No Git commands, Git data/configuration access, dependency installations, new routes, CLI flags, configuration fields, background daemons, or unrelated fixes were performed. No automatic observer restart policy was added: an unexpected observer exit is explicitly logged as a failure, not silently treated as successful observation.

## Files Changed

- `src/zerodock/engine/loader.py`: capture prior owned module under the registry guard and perform identity-checked cleanup for failures before a new module is created, including a disappearing file.
- `src/zerodock/engine/watcher.py`: invalidate every changed availability/content revision, handle initially unavailable observations visibly, include bounded error categories in warnings, preserve repeat suppression, report unexpected task endings, and expose internal poll waiting for deterministic tests.
- `tests/unit/test_loader.py`: extend existing failure and race coverage across reload modes; add missing/unreadable source, corrected-source recovery, nested newer-registration ownership, and waiting-load tests.
- `tests/unit/test_watcher.py`: add atomic replacement, deletion/recreation, unreadability, category/log suppression, partial writes, startup failure/partial registration, unexpected endings, and paced retry tests.
- `tests/integration/test_hot_reload.py`: add existing-format HTTP errors and corrected-save recovery, unaffected routes, deletion/recreation, unreadability, atomic replacement, old-callable completion, and fatal startup propagation.
- `specs/003-handler-hot-reload/verification/us2.md`: this report.

`src/zerodock/gateway/app.py` required no change for T027: its existing lifespan startup failure propagation and structured request error integration passed the new tests. Existing CLI/server files and shared fixtures were not edited.

## Targeted Implementation Details

### Ownership-Safe Failure Cleanup

While holding the existing per-module lease, the loader captures the previously owned object before checking file existence. If loading fails before a new module is created, cleanup targets that captured object. If a new module exists, cleanup targets that attempt's module instead. In either case, object identity checks preserve a different/newer registration. No module dictionary or callable is reused as a last-known-good fallback.

Missing files retain the existing `HandlerLoadError` message. Import, syntax, missing-entrypoint, and non-callable errors retain their existing behavior. Previously returned callables may still finish; that is distinct from silently returning one for a failed new load.

### Availability Transitions and Retry Pacing

Changed readable, missing, and unreadable revisions now all call targeted invalidation. Missing/unreadable targets remain in the exact configured watch set; later readable contents trigger a new invalidation and normal loading. Same revision/status/category is suppressed. A changed error category is reported once as a new transition. Logs include the category name, not an underlying file-error payload that could expose source or secrets.

An initially missing/unreadable observation is invalidated and logged once during watcher setup; an unchanged reconciliation scan does not duplicate it. This does not relax configuration's initial missing-file rejection. Per-file failures occurring after configuration validation remain recoverable observations, not a fatal watcher setup error.

`_wait_for_poll()` retains the existing stop-event wait and 100ms timeout. `_run()` performs another scan only after that wait permits it. Controlled queue/event tests prove repeated recoverable errors cannot bypass the wait; a separate test verifies the production wait uses the configured 0.1s timeout. No new user-facing polling option is introduced.

### Fatal Versus Recoverable Failures

Per-file filesystem errors are represented and retried at the normal polling cadence. Unexpected infrastructure failures during baseline/reconciliation propagate out of startup and release partially registered owners. Unexpected runtime exceptions, cancellation, or return without a stop request produce error logs. Normal requested shutdown is not logged as an unexpected failure.

This phase does not claim complete cancellation/shutdown hardening. The observer's terminal exception/cancellation can still propagate when draining it during shutdown; the tests allow that existing behavior while verifying owner release. Preserving primary errors under every shutdown race and broader multi-app lifecycle acceptance remain Phase 5 work, not silently completed here.

## Test-First Evidence

Environment: existing project venv Python 3.14.6, Windows 11, pytest 9.1.1, same installed dependencies as prior phases. Tests use temporary files and monkeypatched permission errors so Windows account privileges do not make unreadability tests unreliable. No package changes occurred.

### Red Before Fixes

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit/test_loader.py tests/unit/test_watcher.py tests/unit/test_cli.py tests/integration/test_hot_reload.py -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-04-red-temp -q --tb=short
```

Exit code 1: **11 failed, 88 passed in 5.73s**. Failures demonstrated:

- Previous owned registrations remained after a source file disappeared, in both modes.
- Missing/unreadable scans did not acknowledge invalidation.
- Initially unreadable targets produced no warning.
- Error-category transitions lacked the required invalidation/reporting behavior.
- Unexpected cancellation and normal observer return were silent.
- The internal deterministic poll-wait seam did not exist.
- HTTP deletion flow could not acknowledge the required invalidation.

Passing new tests confirmed existing behavior worth preserving: most failed-load cleanup, atomic replacement, corrected syntax/import/entrypoint recovery, fatal startup propagation, owner cleanup, and in-flight callable behavior already worked.

### First Green and Strengthened Final Run

After the targeted source changes: **99 passed in 4.82s**. Quality checks then identified three long lines and formatting differences in the touched test files; these were corrected locally. Additional coverage strengthened the existing initialization/invalidation test across successful/failed imports and both loading modes and added an unreadable HTTP handler case.

Final focused run: **103 passed in 4.74s**, exit code 0. It used the same four test files, a fresh `phase-04-final-temp` base, and an inline evidence plugin for counts and cleanup snapshots. No test fixture directory was cleared or reused.

| Test file | Cases | Important verified behavior |
| --- | ---: | --- |
| `tests/unit/test_loader.py` | 56 | Both loading modes; existing invocation contracts; pre-registration/missing/read failures; new versus old object identity; nested replacement; waiting loads; successful/failed initialization versus invalidation |
| `tests/unit/test_watcher.py` | 21 | Content/availability changes; atomic saves; partial writes; repeated-error/category suppression; initial errors; partial/fatal setup; explicit terminal failure reporting; bounded retry pacing |
| `tests/unit/test_cli.py` | 10 | Prior Phase 3 default/opt-in and server forwarding contracts remain passing |
| `tests/integration/test_hot_reload.py` | 16 | Fresh HTTP responses; existing structured errors; healthy other-file routes; corrected saves; deletion/readability recovery; atomic replacement; old in-flight versus new requests; startup failure |

The slowest recorded test call was 0.17s for real automatic detection. Other reported slow calls were 0.06-0.07s. The 4.74s number is total suite time, not per-test latency.

The retained Phase 3 real-clock detection case measured **119.6916ms**, with one 61-byte handler on the local filesystem. This remains below 500ms for that disclosed small workload and is not a broad performance certification.

## Concurrency and Error-Contract Evidence

- Event-gated tests prove invalidation waits for module initialization, whether initialization succeeds or raises, in both reload modes.
- A waiting fresh load completes after an earlier load's failure and remains registered; cleanup does not remove its callable.
- A failing outer reentrant load preserves a newer successfully registered module from its nested load.
- Existing tests still prove unrelated modules can load independently and invocation does not hold the module lock.
- In the HTTP in-flight test, the old async handler remains pending while source is replaced; a new request returns `new` before the old request is released and returns `old`.
- HTTP syntax/import/missing-entrypoint/non-callable failures retain status 500 and exactly the existing keys: `error`, `exceptionType`, `message`, and `requestId`; the error remains `InternalServerError` with `HandlerLoadError` for those loading failures.
- Deleted and unreadable handlers fail rather than silently returning the old success. Another configured file continues serving `healthy`. Corrected/recreated/readable source returns a fresh response without gateway restart.

## Changed-File Quality Checks

Checked only the two changed source files and three changed test files with the existing venv:

```text
python -B -m ruff check --no-cache <five changed files>
python -B -m ruff format --check --no-cache <five changed files>
python -B -m mypy --follow-imports=silent --cache-dir=specs/003-handler-hot-reload/verification/phase-04-mypy-cache <five changed files>
```

Final results: **all lint checks passed**, **5 files already formatted**, and **no mypy issues in 5 source files**. No unrelated code was reformatted. Sandbox escalation for the project Python launcher was requested explicitly; restrictions were not bypassed.

## Resource and Compatibility Verification

Snapshots around the final in-process pytest run reported:

```text
Handler module snapshot restored: True
Coordination snapshot restored: True
Ownership snapshot restored: True
New live threads after cleanup: []
Python 3.10 syntax parsing: PASS (not a runtime test)
```

The five changed files parse using the Python 3.10 grammar on the available Python 3.14 interpreter. No Python 3.10-3.13, Linux, or macOS runtime execution is claimed. No live server was started in Phase 4; HTTP tests used actual application lifespan with in-process ASGI transport.

Temporary pytest files and the mypy cache remain under fresh feature verification paths. No Git command, recursive cleanup, dependency installation, full-suite run, coverage run, or unrelated benchmark run occurred. Phase 1 memory/startup findings remain unresolved and unwaived.

## Required Contract Review (T030)

| Requirement | Phase 4 evidence | Result within phase scope |
| --- | --- | --- |
| FR-004 content, atomic replacement, disappearance/recreation | Real temporary-file rename-over and delete/recreate tests at watcher and HTTP levels; prior same-metadata tests retained | PASS |
| FR-007 safe failed loading and recovery, no stale fallback | Both-mode cleanup and recovery; unreadable/missing failures; newer-owned identity preservation; HTTP corrected saves | PASS |
| FR-009 per-handler coordination and in-flight behavior | Controlled threaded successful/failed initialization/invalidation; waiting load ownership; old async callable finishes after new HTTP response | PASS |
| FR-014 visible fatal/recoverable observer failures | Initial scan/reconciliation/partial-owner failures propagate and release owners; per-file retry pacing; explicit runtime exception/cancel/return logs | PASS for Phase 4; full shutdown races remain Phase 5 |
| FR-015 coalescing and latest valid save | Previous duplicate/latest-save tests retained; partial-to-valid writes, status/category transition suppression, and repeated scan pacing | PASS |

## Task Review Status

| Task | Actual result | Review state |
| --- | --- | --- |
| T021 | Loader failure, recovery, identity, and race tests added/extended | Awaiting approval |
| T022 | Watcher transitions, setup/failure visibility, and retry tests added | Awaiting approval |
| T023 | HTTP error/recovery, isolation, atomic save, and in-flight tests added | Awaiting approval |
| T024 | Pre-registration missing-file cleanup fixed; existing owned-attempt cleanup preserved and verified | Awaiting approval |
| T025 | All availability transitions invalidate; recreation is observed; duplicate warnings suppressed | Awaiting approval |
| T026 | Setup cleanup preserved/verified; unexpected endings logged; polling cadence verified | Awaiting approval |
| T027 | Existing application/error integration reused without edits and proven by integration tests | Awaiting approval |
| T028 | Successful/failed init-versus-invalidate and waiting-load/new-registration scenarios pass | Awaiting approval |
| T029 | 103 focused regression/recovery cases pass; evidence recorded here | Awaiting approval |
| T030 | Required failure-contract matrix reviewed without weakening scope or budgets | Awaiting approval |

## Playground Test

### Automated Check

1. Open PowerShell in `C:\dev\python\zerodock`.
2. Run the command below; do not reuse one of the saved fixed `--basetemp` directories.
3. Expect **103 passed**. No browser or live test server is needed for this check.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit/test_loader.py tests/unit/test_watcher.py tests/unit/test_cli.py tests/integration/test_hot_reload.py -p no:cacheprovider -q
```

### Optional Manual Error/Recovery Check

Use only the existing disposable Phase 3 fixture, never `functions/hello.py`. Its current contents may include your prior manual edits; preserve them and undo only your deliberate test error.

1. Start the disposable gateway:

```powershell
$env:PYTHONPATH = "$PWD\src"
& '.\.venv\Scripts\python.exe' -B -m zerodock.cli dev --reload --config specs/003-handler-hot-reload/verification/phase-03-live/serverless-local.yaml --port 8088
```

2. Open `http://127.0.0.1:8088/sync`. Note its version and PID.
3. In `verification/phase-03-live/handler.py`, temporarily remove the colon from the `def sync_handler(event):` line and save. Refresh the route: expect the existing structured 500 error and a syntax traceback in the terminal, not an old successful response.
4. Restore the colon and save. After invalidation, refresh again: expect the original valid response and same PID, without restarting. Stop the server using Ctrl+C.

Both disposable routes share the same source file, so a file-level syntax error affects both; they are not an unaffected-route demonstration. Automated recovery tests use a separate healthy source file and prove it stays usable. If you want to try disappearance manually, rename the disposable handler temporarily rather than deleting it, then restore its original name; expect failure while absent and recovery after restoration.

Record any issue in `Troubleshoot.md` and report it. Approval of this phase permits its task checkmarks only; Phase 5 requires separate authorization.

## Official References

- [Python task cancellation and completion callbacks](https://docs.python.org/3.14/library/asyncio-task.html): distinguish cancelled tasks, exceptions, and normal results.
- [Python replacement semantics](https://docs.python.org/3.14/library/os.html#os.replace): replacement-save tests use temporary files on one filesystem.
- [Pytest monkeypatching](https://docs.pytest.org/en/stable/how-to/monkeypatch.html): deterministic permission/failure injection with scoped restoration.
- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/): preserve startup failure propagation and resource ownership.
