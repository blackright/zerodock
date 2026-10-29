# Tasks: FEAT-002 Hot-Reloading & Dynamic Module Cache Invalidation

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [interface contract](contracts/reload-contract.md), and [quickstart.md](quickstart.md).
**Created**: 2026-10-29
**Status**: Phases 1-5 are approved. Phase 6 closeout completed T041/T042/T044/T046: documentation/benchmarks, repository-wide quality, >90% touched-core statement coverage and live/runtime-status validation. Final Windows/Python 3.14 suite: 194 passed. Subsequent isolated Python 3.12 suite: 192 passed/2 performance failures. The amended <60MB baseline memory gate passes. T043/T045/T047/T048 remain open; Phase 6 is NOT complete. See verification/phase-06-closeout.md. No other limit or runtime default was changed.
**Tests**: Required explicitly by the specification and constitution. Write regression tests first, obtain red evidence for new behavior, then implement and obtain green evidence when execution is authorized. Existing passing compatibility tests need not be made artificially red.
**Organization**: Setup -> shared foundations -> US1 (P1) -> US2 (P2) -> US3 (P3) -> cross-cutting acceptance.

## Format and Path Conventions

Each actionable task uses an unchecked checkbox, sequential ID, optional `[P]`, a story label only within story phases, and exact repository-relative file paths. `[P]` means eligible to run beside other explicitly identified disjoint-file tasks once prerequisites are satisfied, not authorization to spawn agents or execute work now. Paths under `verification/` are future evidence artifacts, not fabricated results. Reuse equivalent existing tests rather than create duplicate test infrastructure.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm scope and preserve a measurable baseline without changing unrelated work.

- [x] T001 Recheck applicable repository instructions, current implementation, existing test coverage, and user edits; record reuse/replace/preserve decisions and actual branch in specs/003-handler-hot-reload/verification/implementation-audit.md using src/zerodock/engine/loader.py, src/zerodock/config/parser.py, src/zerodock/gateway/app.py, and src/zerodock/cli.py as audit targets.
- [x] T002 Inventory available Python/dev/coverage and RSS measurement tools without installing packages; record test commands, supported runtime/platform checks, local workload file count/bytes, and approval-dependent validation steps in specs/003-handler-hot-reload/verification/validation-plan.md.
- [x] T003 After execution authorization, capture unmodified loader tests, existing startup/ASGI benchmarks, lifespan-inclusive startup, isolated dispatch, process readiness, and current idle RSS baselines in specs/003-handler-hot-reload/verification/baseline.md using tests/unit/test_loader.py and tests/integration/test_performance_benchmarks.py; report unmet budgets without changing thresholds.

**Checkpoint**: Existing implementation and baseline are understood. Missing tools, permission boundaries, and pre-existing failures are reported rather than bypassed.

**Review outcome (2026-10-29)**: User approved the Phase 1 reports and measurements. Current branch was not rechecked under the user's no-Git rule; that limitation is documented in the approved audit. Approval acknowledges the recorded memory/startup findings, not a waiver of runtime budgets or permission to fix them. Phase 2 remains unauthorized.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared identity, targeted invalidation, coordination, and isolated test support before story implementation.

- [x] T004 Add temporary handler/config factories, deterministic scan barriers, and test-owned module/resource cleanup fixtures in tests/conftest.py after inspecting and reusing any existing fixture infrastructure; never modify real repository handlers.
- [x] T005 Write foundational identity, same-basename isolation, idempotent invalidation, foreign-module protection, ownership-safe cleanup, and active-lease/watcher-owner registry lifetime tests in tests/unit/test_loader.py; record red evidence for new APIs when authorized.
- [x] T006 Extract one canonical resolved-path module identity helper and implement invalidate_handler_cache(module_name: str) -> None in src/zerodock/engine/loader.py, preserving the existing hash algorithm and making absent/foreign module invalidation a no-op without touching dependencies or bytecode files.
- [x] T007 Implement process-wide per-module reentrant coordination leases, watcher ownership counts, safe registry-entry retirement, and coordinated loader/invalidation access in src/zerodock/engine/loader.py; pin holders/waiters before waiting and never hold the registry guard while acquiring a module lock or a module lock across handler invocation/awaits.
- [x] T008 Run authorized foundational tests in tests/unit/test_loader.py and verify default successful loading still executes per call; record red/green evidence and cleanup/isolation results in specs/003-handler-hot-reload/verification/foundations.md.

**Checkpoint**: Shared identities and coordination are safe for direct loader calls and multiple applications. No persistent module/callable cache or mandatory dependency has been introduced.

**Review outcome (2026-10-29)**: User approved the verified Phase 2 work. Focused tests passed 30/30; changed-file lint, formatting, typing, and cleanup checks passed. T004-T008 are complete. Phase 3 remains unauthorized; existing Phase 1 budget findings are not waived.

## Phase 3: User Story 1 - See Saved Handler Changes Without Restarting (P1, MVP)

**Goal**: Opt into in-process reload and reliably serve fresh configured source after detection/invalidation.
**Independent Test**: Start a reload-enabled gateway, receive A, save B, await confirmed invalidation, and receive B on the next request; repeat with same-length/same-timestamp edits and sync/async handlers. A separately authorized live-server check must verify unchanged PID/port.

### Tests First

- [x] T009 [P] [US1] Add reload-enabled loader tests for stale bytecode with restored size/timestamps, Python source encodings/BOM, future-import compilation, source filename/traceback fidelity, multiple entrypoints, and fresh module execution on every call in tests/unit/test_loader.py.
- [x] T010 [P] [US1] Add deterministic observer tests for SHA-256 content detection, canonical-path deduplication, unchanged scans, duplicate observations, latest-version convergence, unrelated-file exclusion, and at most one outstanding off-loop scan in tests/unit/test_watcher.py.
- [x] T011 [P] [US1] Add CLI/library contract tests for dev --reload parsing, default-false forwarding through server/app/loader, keyword-only compatibility, and absence of Uvicorn restart mode in tests/unit/test_cli.py using mocked server invocation.
- [x] T012 [P] [US1] Add HTTP integration tests explicitly entering app.router.lifespan_context(app) for sync/async A-to-B refresh after scan acknowledgement, same-metadata bytecode freshness, shared-file entrypoints, and isolated same-basename handlers in tests/integration/test_hot_reload.py.

### Implementation

- [x] T013 [US1] Add keyword-only reload=False to load_handler() in src/zerodock/engine/loader.py; in reload mode compile fresh source bytes with the resolved filename and dont_inherit=True into an importlib-created module, preserving metadata and the original non-reload execution path without retaining source/code/callable caches.
- [x] T014 [US1] Implement exact-target observation state and bounded off-loop source fingerprint scans in src/zerodock/engine/watcher.py with a 100ms interval between scans, one outstanding scan, status/digest storage only, and no source execution or module mutation inside scan workers.
- [x] T015 [US1] Implement readable-revision comparison, duplicate coalescing, coordinated targeted invalidation through the shared loader helper, and appropriate enablement/invalidation logging without source/request contents in src/zerodock/engine/watcher.py.
- [x] T016 [US1] Add keyword-only reload=False and app-owned async lifespan integration in src/zerodock/gateway/app.py; capture baseline plus immediate reconciliation before startup readiness, register target ownership, start/stop/drain observation, and forward reload mode to request-time loading without import-time tasks.
- [x] T017 [US1] Add backward-compatible keyword-only reload=False forwarding in src/zerodock/gateway/server.py; continue passing the app object to uvicorn.run() without enabling Uvicorn reload or creating a restart worker.
- [x] T018 [US1] Add dev --reload and default-false forwarding in src/zerodock/cli.py while preserving implicit no-subcommand startup and existing options; do not add a top-level --reload option or new YAML fields.
- [x] T019 [US1] Execute authorized US1 loader/watcher/CLI/HTTP tests and a bounded real-clock detection test in tests/integration/test_hot_reload.py; record raw timing, workload/environment, <=500ms results, and red/green evidence in specs/003-handler-hot-reload/verification/us1.md.
- [x] T020 [US1] Perform the separately approved disposable live-server A-to-B check from specs/003-handler-hot-reload/quickstart.md and verify identical PID/port before and after save; record the actual observations in specs/003-handler-hot-reload/verification/us1-live-server.md without modifying repository handlers.

**Checkpoint**: US1 is a demonstrable development MVP, not final feature acceptance. Recovery, hardened lifecycle compatibility, and cross-cutting budgets remain required before completion.

**Review outcome (2026-10-29)**: User approved Phase 3 after receiving the playground instructions. T009-T020 are complete. Automated evidence records 64 passing tests, passing changed-file quality/cleanup checks, 109-112ms detection in the disclosed workload, and live sync/async refresh with unchanged PID/port. No additional manual observations are inferred from approval. Phase 4 remains unauthorized; existing budget findings are not waived.

## Phase 4: User Story 2 - Recover From Saves and Errors (P2)

**Goal**: Atomic saves, invalid code, and runtime file disappearance recover without stale fallback or gateway restart.
**Independent Test**: Introduce a syntax error, observe the existing error response while another route works, fix source, await invalidation, and observe recovery; repeat deletion/recreation and atomic replacement.

### Tests First

- [x] T021 [P] [US2] Extend tests/unit/test_loader.py with syntax/import failure, missing/non-callable entrypoint, missing/unreadable source, no-stale-fallback, identity-guarded failed cleanup, valid-source recovery, and deterministic thread-barrier load/invalidate races for both loading modes where applicable.
- [x] T022 [P] [US2] Extend tests/unit/test_watcher.py with atomic rename-over, deletion/recreation, readable/missing/unreadable transitions, repeated-error suppression, rapid partial writes, bounded retry, and fatal observer setup/unexpected termination tests.
- [x] T023 [P] [US2] Extend tests/integration/test_hot_reload.py with structured-error compatibility, unaffected-route availability, corrected-save recovery, atomic replacement, runtime deletion/recreation, and event-gated in-flight old-callable completion followed by fresh requests.

### Implementation

- [x] T024 [US2] Make load-attempt failure and entrypoint-validation cleanup ownership-safe in src/zerodock/engine/loader.py, removing only that attempt's registered module and preserving HandlerLoadError behavior rather than restoring a last-known-good callable.
- [x] T025 [US2] Implement missing/unreadable revision transitions and retryable recreation/atomic-replacement observation in src/zerodock/engine/watcher.py while retaining targets and suppressing repeated identical invalidations/errors.
- [x] T026 [US2] Handle fatal observer initialization, partial-startup cleanup, bounded recoverable retries, and unexpected observer-task termination logging in src/zerodock/engine/watcher.py without tight loops, source logging, or silently disabling observation.
- [x] T027 [US2] Complete startup failure propagation and runtime error integration in src/zerodock/gateway/app.py using existing gateway error helpers without altering response envelopes, route registration, or timeout behavior.
- [x] T028 [US2] Execute the authorized concurrent load/invalidate and failed-load-versus-new-registration tests authored in T021 in tests/unit/test_loader.py; verify per-target isolation and that locks are not held during handler invocation, recording results in specs/003-handler-hot-reload/verification/us2.md.
- [x] T029 [US2] Execute authorized US2 unit/integration scenarios in tests/unit/test_loader.py, tests/unit/test_watcher.py, and tests/integration/test_hot_reload.py; record red/green, failure-format, recovery, and concurrency evidence in specs/003-handler-hot-reload/verification/us2.md.
- [x] T030 [US2] Review the implemented recovery behavior against the failure contract in specs/003-handler-hot-reload/contracts/reload-contract.md and record requirement-by-requirement results for FR-004, FR-007, FR-009, FR-014, and FR-015 in specs/003-handler-hot-reload/verification/us2.md without weakening approved guarantees.

**Checkpoint**: Failure and recovery journeys pass independently of the clean-shutdown acceptance scenario. Existing successful US1 behavior remains passing.

**Review outcome (2026-10-29)**: User approved the verified Phase 4 work. T021-T030 are complete. Evidence records 103 passing focused tests and passing changed-file quality/cleanup checks. Existing application error/startup integration was reused without edits. Phase 5 remains unauthorized; broader shutdown hardening and existing budget findings remain open. No additional manual observations are inferred from approval.

## Phase 5: User Story 3 - Preserve Existing Behavior and Clean Shutdown (P3)

**Goal**: No observer when disabled, unchanged startup validation/path semantics, and leak-free app-owned observation across shutdown/cancellation and shared targets.
**Independent Test**: Compare default/reload-enabled execution, reject an initially missing file, use an external config directory, repeat lifespan entry/exit, and shut down one of two apps sharing a handler while the survivor still reloads.

### Tests First

- [x] T031 [P] [US3] Extend tests/unit/test_cli.py with legacy positional/programmatic calls, implicit no-subcommand startup, existing CLI options, disabled-mode forwarding, and rejection of unsupported top-level --reload.
- [x] T032 [P] [US3] Extend tests/unit/test_watcher.py with worker-gated cancellation, interval wakeup, partial initialization, repeated startup/shutdown, retained worker draining, no late invalidation after ownership release, and no shared-executor shutdown.
- [x] T033 [P] [US3] Extend tests/integration/test_hot_reload.py with zero observers on import/app construction or disabled lifespan, external config-relative target resolution, initially missing-file rejection, per-request global-state compatibility in both modes, repeated lifespan cleanup, and two-app shared-target survival including distinct event loops.

### Implementation

- [x] T034 [US3] Harden cooperative stop, retained/shielded pending scan draining, cancellation propagation, resource cleanup, and repeated lifespan entry in src/zerodock/engine/watcher.py; document rather than hide indefinite hung-filesystem limitations.
- [x] T035 [US3] Complete disabled-mode and partial-startup/finally cleanup paths in src/zerodock/gateway/app.py without creating observer tasks at import or changing existing configuration-parser startup validation and relative-path rules.
- [x] T036 [US3] Finalize watcher-owner registration release and active-lease retirement in src/zerodock/engine/loader.py so one app cannot evict another app's module or lock, direct callers remain safe, and process-wide coordination is not tied to a single event loop.
- [x] T037 [US3] Reconcile CLI/server default-false and keyword-only compatibility in src/zerodock/cli.py and src/zerodock/gateway/server.py against tests/unit/test_cli.py; preserve existing invocation options without adding dependencies or schema fields.
- [x] T038 [US3] Verify module side effects execute per request in both modes and no invocation-global migration/cache was introduced using tests/unit/test_loader.py and tests/integration/test_hot_reload.py; include direct-loader behavior after watcher shutdown.
- [x] T039 [US3] Execute authorized US3 and all prior focused regression tests, including controlled worker cancellation and distinct-loop shared ownership; record task/file-handle cleanup and compatibility evidence in specs/003-handler-hot-reload/verification/us3.md.
- [x] T040 [US3] Verify native source breakpoints/tracebacks and existing sync/async arity, event/context, timeout, and response behavior remain compatible using tests/unit/test_loader.py and existing tests/integration/test_gateway_dispatch.py and tests/integration/test_error_handling.py; record automated and separately approved debugger observations in specs/003-handler-hot-reload/verification/us3.md.

**Checkpoint**: All three journeys are supported; no app-owned observer work remains after shutdown and default-mode semantics are unchanged.

**Review outcome (2026-10-29)**: User approved the verified Phase 5 work. T031-T040 are complete. Evidence records 140 passing focused tests plus five distinct existing integration tests, with passing changed-file lint, formatting, typing, and cleanup checks. Existing coordination and CLI/server behavior were reused; lifecycle cleanup and debugger source freshness were hardened. No additional manual observations are inferred from approval. Phase 6 remains unauthorized; existing budget findings are not waived.

## Phase 6: Polish and Cross-Cutting Acceptance

**Purpose**: Prove the complete feature, preserve project budgets, and document only verified behavior.

- [x] T041 [P] Update README.md with zerodock dev --reload, disabled default, 100ms internal polling/<=500ms documented workload target, post-invalidation freshness, recovery, handler-only scope, helper limitations, native debugging, and no extra installation requirement.
- [x] T042 [P] Extend tests/integration/test_performance_benchmarks.py with clearly separated reload-on/off lifespan-inclusive startup, isolated dispatch, idle current RSS, changed-file request, and real-clock detection measurements while preserving existing <100ms config/app and <30ms best-of-three ASGI definitions; use available approved platform measurement methods and disclose unsupported methods rather than substitute peak RSS.
- [ ] T043 Run authorized focused and full pytest suites, including existing packaging and diagnostics coverage, against tests/unit and tests/integration; record actual commands, results, pre-existing failures, and red/green references in specs/003-handler-hot-reload/verification/regression.md without repairing unrelated failures.
- [x] T044 Run authorized existing Ruff/mypy checks for src/zerodock and tests, and available approved coverage tooling for touched loader/watcher logic; record results and the >90% core coverage target in specs/003-handler-hot-reload/verification/quality.md without adding tooling or changing unrelated code without approval.
- [ ] T045 Execute the approved baseline-versus-modified measurement protocol from specs/003-handler-hot-reload/verification/validation-plan.md and tests/integration/test_performance_benchmarks.py, applying the current memory amendment in specs/003-handler-hot-reload/memory-budget-amendment.md; record all raw samples, source/config bytes, route/watched-file counts, runtime/platform, readiness boundaries, <100ms engine boot, <5ms dispatch, <60MB baseline actual listening-server current RSS and <=500ms detection results in specs/003-handler-hot-reload/verification/performance.md. Report <50MB separately as an optimization target, preserve old failures, use three fresh processes per reload mode with every sample passing, and stop acceptance for remaining budget violations.
- [x] T046 Validate the complete disposable quickstart, native debugging, PID/port stability, shutdown, and relevant supported Python/platform checks from specs/003-handler-hot-reload/quickstart.md only when approved; record passed, failed, and untested environments explicitly in specs/003-handler-hot-reload/verification/quickstart.md without installing tools or claiming unrun platform coverage.
- [ ] T047 Review all FR-001 through FR-016, SC-001 through SC-007, acceptance scenarios, six approved improvements, interface contracts, and non-goals against actual evidence; record the final compliance matrix and constitution review in specs/003-handler-hot-reload/verification/acceptance.md, leaving incomplete gates open rather than waiving them.
- [ ] T048 Reconcile verified usage and validation commands in specs/003-handler-hot-reload/quickstart.md and completion evidence in specs/003-handler-hot-reload/checklists/requirements.md; report remaining Git-ignore behavior, user-edited files, limitations, and approval needs without changing ignore rules, creating branches, or committing.

## Dependencies and Execution Order

### Phase Graph

```text
Setup T001 -> T002 -> T003
  -> Foundations T004 -> T005 -> T006 -> T007 -> T008
  -> US1 tests T009/T010/T011/T012
     -> T013 -> T014 -> T015 -> T016 -> T017 -> T018 -> T019 -> T020
  -> US2 tests T021/T022/T023
     -> T024 -> T025 -> T026 -> T027 -> T028 -> T029 -> T030
  -> US3 tests T031/T032/T033
     -> T034 -> T035 -> T036 -> T037 -> T038 -> T039 -> T040
  -> Polish T041/T042 -> T043 -> T044 -> T045 -> T046 -> T047 -> T048
```

The arrows describe a safe conservative execution order, not additional permission. US1 requires foundations; US2 and US3 extend the same loader/watcher/app files and therefore follow US1. US3 follows US2 to avoid conflicting lifecycle/recovery modifications. Each story has its own independently runnable acceptance journey once prerequisites exist; stories are not falsely advertised as independently implementable from an empty foundation.

### Explicit Task Dependencies

- T003 baseline precedes all source/test changes; establish it only with authorized execution.
- T005 depends on fixtures T004; T006/T007 must satisfy those tests before foundation acceptance T008.
- Each story's test group depends on the previous checkpoint and must precede implementation of that behavior. Capture red evidence for new behavior before its fix.
- T016 provides the basic lifespan needed by the US1 MVP; T026/T027 add recovery and T034/T035 harden cancellation. US3 does not postpone all lifecycle ownership until after MVP.
- T021 authors recovery and race regressions before implementation; T028 verifies them after the changes. Any race correction stays within T024/T007 scope and requires rerunning the affected regressions.
- T038 is a compatibility verification task; if it reveals a mismatch, stop and make only an approved in-scope correction before T039.
- T041 and T042 are disjoint after story checkpoints; T043 requires both to finish. T045 compares with T003, not a newly invented baseline.
- T047 requires the actual evidence from T019/T020/T029/T039/T040/T043-T046. Tests alone do not establish runtime budgets, PID/port stability, or native IDE behavior.

## Parallel Opportunities and Examples

Parallel work is limited to file-disjoint groups after their prerequisite checkpoint. Do not concurrently edit the same test or source file across stories, and do not interpret these examples as authorization to spawn agents.

### User Story 1

After T008: T009 (`tests/unit/test_loader.py`), T010 (`tests/unit/test_watcher.py`), T011 (`tests/unit/test_cli.py`), and T012 (`tests/integration/test_hot_reload.py`) can be authored in parallel using T004 fixtures. Implementation T013-T018 remains ordered because shared APIs must exist first.

### User Story 2

After T020: T021 loader errors, T022 observer transitions, and T023 HTTP recovery can be authored in parallel in their distinct files. Do not overlap them with unfinished US1 test edits. T024-T028 are ordered shared-component work.

### User Story 3

After T030: T031 CLI compatibility, T032 worker cancellation, and T033 lifecycle integration tests can be authored in parallel. Changes to shared fixtures must be completed first or coordinated serially; T034-T038 remain ordered.

### Cross-Cutting

After T040: T041 README documentation and T042 performance test authoring can proceed together. Measurements execute only after those tasks and their execution approvals, not while code is changing.

## Implementation Strategy

### MVP First

After separate authorization, complete Setup and Foundations, then US1 through T020. Demonstrate a saved A-to-B response with confirmed invalidation and unchanged PID/port. Stop for review before expanding into subsequent story implementation if required by the user's approval scope. MVP is not final constitutional acceptance or permission to skip recovery/cleanup.

### Incremental Delivery

Add US2 failure/recovery behavior and rerun US1; then add US3 compatibility/cancellation/shared-app coverage and rerun prior journeys. Finish the full cross-cutting evidence matrix before claiming feature completion. Follow test-first development within every increment.

### Scope and Approval Guardrails

Reuse path resolution, module naming, error helpers, invocation contracts, and existing test fixtures. Preserve startup missing-file rejection and per-request execution in both modes. Replace only unsafe module-failure retention and extend loading for reload freshness. Never implement persistent callable caching, imported-helper reload, dynamic configuration/routes, process-restart mode, or mandatory watcher dependencies. Stop and ask before expanding scope, installing tooling, altering Git-ignore rules, committing, or fixing unrelated failures.

## Coverage Summary

| Requirement / outcome | Tasks |
| --- | --- |
| FR-001 opt-in and compatibility | T011, T017, T018, T031, T037 |
| FR-002 in-process continuity | T016, T017, T020, T046 |
| FR-003 exact deduplicated targets | T006, T010, T014, T033 |
| FR-004 content/atomic/deletion detection | T009, T010, T022, T025 |
| FR-005 fresh source | T009, T012, T013, T019 |
| FR-006 safe invalidation | T005, T006, T007, T015 |
| FR-007 cleanup/recovery | T021, T023, T024, T029 |
| FR-008 per-request execution | T008, T009, T013, T033, T038 |
| FR-009 coordination | T007, T023, T028, T036 |
| FR-010 invocation/debugging | T009, T012, T040, T046 |
| FR-011 lifecycle | T016, T032, T033, T034, T035, T039 |
| FR-012 startup validation | T033, T035 |
| FR-013 logging/privacy | T015, T022, T026, T047 |
| FR-014 observer failure visibility | T022, T026, T027, T032 |
| FR-015 coalescing | T010, T015, T022, T025 |
| FR-016 documentation | T041, T046, T048 |
| SC-001 freshness/no restart | T019, T020, T046 |
| SC-002 detection target | T019, T042, T045 |
| SC-003 recovery/isolation | T023, T028, T029 |
| SC-004 no observer leaks | T032, T033, T039 |
| SC-005 benchmark regression | T003, T042, T045 |
| SC-006 constitutional budgets | T003, T042, T045, T047 |
| SC-007 offline tests/core coverage | T004, T043, T044 |

## Task Generation Review

Originally generated 48 unchecked tasks: Setup 3; Foundations 5; US1 12; US2 10; US3 10; Polish 8. All tasks have unique sequential IDs and exact file paths. Story phases use story labels; shared phases do not. Parallel markers identify disjoint-file authoring opportunities only. After approved Phases 1-5 and the user's Phase 6 closeout authorization, T001-T040 plus T041/T042/T044/T046 are checked complete (44 total). T043/T045/T047/T048 remain unchecked; no final phase completion is claimed. Hook configuration must be checked again before subsequent workflow execution.
