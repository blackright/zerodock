# Phase 2 Foundations: Implementation and Verification

**Date**: 2026-10-29 (Europe/Budapest)
**Scope**: T004-T008 only.
**Status**: Implemented and checked; awaiting user review. Task checkboxes remain unchecked. Phase 3 has not started.

## Authorization and Existing-Code Audit

The user approved the proposed Phase 2 loader changes, isolated test helpers, focused loader tests, changed-file quality checks, and this report. `Phase-Builder-Agent.md`, the phase tasks, actual loader/test code, design contracts, research, and constitution were read before implementation. No applicable `AGENTS.md` was found in the inspected paths. The requirements-quality checklist was already satisfied; no review markers were changed. No implementation extension hooks are configured.

| Area | Decision and actual result |
| --- | --- |
| Existing resolved-path SHA-256 identity | Reused unchanged; exposed through one `handler_module_name()` helper |
| Importlib spec/module creation and execution | Preserved; still runs on every load, not a persistent callable/module cache |
| Handler signatures and sync/async invocation | Preserved; `invoke_handler()` is unchanged |
| Existing error messages and exception chaining | Preserved; failed initialization/entrypoint validation now removes only its own registration |
| Registry eviction | Added targeted `invalidate_handler_cache()`; missing/foreign registrations are ignored |
| Per-handler coordination | Added leases and owner counts; no global execution lock and no lock held during handler invocation |
| Fixture support | No existing conftest infrastructure existed; added isolated factories, cleanup, and event gates |

No watcher, reload flag, reload-specific source execution, app lifespan integration, dependency change, configuration change, or unrelated optimization is added. Invalidation alone still does not guarantee bytecode freshness; that belongs to a later phase.

## Files Written

- `src/zerodock/engine/loader.py`: identity helper, targeted invalidation, weak ownership metadata, process-wide per-module leases/owner registration, and failed-load cleanup.
- `tests/conftest.py`: temporary handler/config factories, test-owned module cleanup, and bounded event-based worker gates.
- `tests/unit/test_loader.py`: preserve the original six behaviors, route their temporary files through cleanup helpers, and add foundational isolation/ownership/concurrency regressions.
- `specs/003-handler-hot-reload/verification/foundations.md`: this evidence and review guide.

Disposable pytest fixture directories and a mypy cache were generated under the feature's verification directory. No source bytecode or pytest cache was deliberately generated: Python used `-B`, `PYTHONDONTWRITEBYTECODE=1`, and pytest used `-p no:cacheprovider`. Each run used a different `--basetemp` path rather than deleting an existing test directory.

## Coordination and Cleanup Design

`_ModuleState` owns a reentrant lock plus active-lease and watcher-owner counts. A short registry lock protects acquisition/counting and weak module-ownership metadata. A holder or waiter increments its lease count before waiting on the per-module lock. Registry state is retired only with no active leases and no observer owners.

`watch_handler_cache()` is a synchronous ownership context for future observers, not a file watcher or background task. Two owners share the same state. Closing one does not evict a module or remove coordination needed by the other owner or a waiting loader. It does not use an event-loop-bound lock.

Loaded module objects are recorded weakly for ownership checks, not retained as a second persistent module cache or reused for execution. Invalidation checks the actual registered object's identity rather than trusting a namespace prefix. Cleanup after failure checks the failing load's expected module object and preserves a newer/replacement object. Already returned callables remain usable after invalidation.

The per-module lock spans initialization and entrypoint validation, not user handler invocation or an await. Thread-gated tests show same-target invalidation waits for initialization while another target can load independently and an already-running callable can finish normally.

## Test-First Evidence

Existing interpreter: project venv Python 3.14.6 on Windows 11, pytest 9.1.1. No packages were installed or upgraded. The launcher required the same explicit sandbox escalation as Phase 1; no restriction was bypassed.

### Red: Before Loader Implementation

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit/test_loader.py -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-02-red-temp -q --tb=short
```

Exit code 1: **21 failed, 9 passed in 0.81s**. Failures were expected missing `handler_module_name`, `invalidate_handler_cache`, and coordination APIs. The passing cases included the existing six invocation/error behaviors plus compatibility/factory tests. No production loader changes existed at the red run.

Some cleanup tests initially stopped at the missing identity helper, so this red result is not claimed as separate execution evidence for every deeper cleanup assertion. All those assertions executed in green runs.

### Green: After Loader Implementation

First implementation run: **30 passed in 0.35s**. Ruff then found one import-order issue; it was corrected. The first formatting check requested layout changes in the three touched files; these were applied locally without formatting unrelated files. Mypy found no issues.

Final focused command:

```powershell
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit/test_loader.py -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-02-final-temp -q --tb=short --durations=5
```

Exit code 0: **30 passed in 0.33s**. No sleep-based correctness assertions are used. Event waits and future results have five-second failure bounds; normal execution completed well below those bounds.

### In-Process Cleanup Verification

A final focused run invoked pytest in a process that captured registry snapshots before and after execution, using `phase-02-cleanup-temp`. **30 passed in 0.27s**. All three post-run comparisons passed:

```text
Handler module snapshot restored: True
Coordination state snapshot restored: True
Ownership snapshot restored: True
```

The three changed Python files also parsed with the Python 3.10 syntax grammar. This is a syntax check on Python 3.14, not a claim that Python 3.10 runtime tests were executed.

## Focused Quality Checks

```powershell
& '.\.venv\Scripts\python.exe' -B -m ruff check --no-cache src/zerodock/engine/loader.py tests/conftest.py tests/unit/test_loader.py
& '.\.venv\Scripts\python.exe' -B -m ruff format --check --no-cache src/zerodock/engine/loader.py tests/conftest.py tests/unit/test_loader.py
& '.\.venv\Scripts\python.exe' -B -m mypy --follow-imports=silent --cache-dir=specs/003-handler-hot-reload/verification/phase-02-mypy-cache src/zerodock/engine/loader.py tests/conftest.py tests/unit/test_loader.py
```

Final results: Ruff **all checks passed**; formatting **3 files already formatted**; mypy **no issues found in 3 source files**. Imported dependencies were not treated as unrelated source-check targets. No full-suite, integration, benchmark, coverage, package installation, or live-server execution was performed in Phase 2.

## Phase Task Verification

| Task | Implementation | Verification | Review state |
| --- | --- | --- | --- |
| T004 | Temporary factories, targeted cleanup, event gate fixtures | Factories tested; concurrency tests use the gate; complete run restores module metadata | Awaiting user approval |
| T005 | Identity/isolation/invalidation/cleanup/lease/owner tests | 30 loader cases pass, including original six behaviors | Awaiting user approval |
| T006 | Shared identity helper and ownership-aware idempotent invalidation | Algorithm, relative paths, absent/foreign/replaced modules, and retained callables tested | Awaiting user approval |
| T007 | Process-wide reentrant leases and owner counts | Nested access, exceptional exit, pinned waiter after owner shutdown, independent targets, initialization exclusion, and invocation unlock tested | Awaiting user approval |
| T008 | Focused red/green and compatibility checks recorded | Red 21/9; final green 30/30; cleanup/type/lint/format checks pass | Awaiting user approval |

## Unchanged Scope and Remaining Limits

Seven hashes still match the Phase 1 snapshot: configuration parser, gateway app, server, CLI, existing performance test, YAML configuration, and real sample handler. No Git commands or Git configuration/data access occurred. Existing user workflow/spec drafting files were not edited.

The Phase 1 idle-memory finding and full-process-startup numbers remain unresolved and were not remeasured or waived. Missing coverage tooling was not installed. Linux/macOS and Python 3.10-3.13 runtime behavior remain untested. No claims of complete hot reload, <=500ms detection, lifecycle cleanup, or whole-feature performance compliance are made.

## Playground Test for User Review

1. Open a PowerShell terminal at `C:\dev\python\zerodock`.
2. Run the command below. Omitting a fixed base directory lets pytest choose a temporary location rather than clear one of the saved measurement directories.
3. Expect `30 passed`. There is no new UI, reload CLI flag, or watcher to try yet.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit/test_loader.py -p no:cacheprovider -q
```

If anything fails, record the error in `Troubleshoot.md` and report it. Review this phase before approving task completion. Approval of Phase 2 does not authorize Phase 3.

## Official References Checked Before Implementation

- [Python reentrant locks](https://docs.python.org/3.14/library/threading.html#rlock-objects): ownership and nested acquisitions.
- [Context manager cleanup](https://docs.python.org/3.14/library/contextlib.html#contextlib.contextmanager): release resources with `try/finally`.
- [Importlib module creation](https://docs.python.org/3.14/library/importlib.html#importlib.util.module_from_spec): preserve the existing dynamic module approach.
- [Pytest fixture finalization](https://docs.pytest.org/en/stable/how-to/fixtures.html#teardown-cleanup-aka-fixture-finalization): cleanup registered fixture resources.
- [Thread events](https://docs.python.org/3.14/library/threading.html#event-objects): deterministic synchronization instead of arbitrary sleeps.
