# Implementation Plan: FEAT-002 Handler Hot Reload

**Branch**: `main` (unchanged) | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)
**Input**: Approved specification and six-phase plan from conversation.
**Status**: Design history retained below. Implementation Phases 1-5 are approved; Phase 6 is in progress. The 2026-10-29 memory amendment is approved and aligned; final acceptance and other scope changes still require their own evidence/review.

## Summary

Add opt-in `zerodock dev --reload` using standard-library asynchronous content polling and targeted module invalidation, preserving per-request execution in both modes. Guarantee fresh source, isolate failures, own watcher resources through application lifespan, and measure overhead honestly. Do not use Uvicorn restart reload or add dependencies.

## Technical Context

**Language/Version**: Python 3.10+.
**Primary Dependencies**: Existing FastAPI, Uvicorn, Pydantic, and PyYAML; standard library for observation and coordination.
**Storage**: Existing handler source files; bounded in-memory fingerprints and coordination metadata, no database.
**Testing**: Existing pytest, pytest-asyncio, HTTPX, Ruff, and mypy toolchain. Tests are planned, not executed.
**Target Platform**: Local Windows, Linux, and macOS development; platform-specific behavior must be verified, not presumed.
**Project Type**: CLI and embedded HTTP gateway.
**Performance Goals**: Detection/invalidation target <=500ms; preserve startup <100ms, dispatch overhead <5ms, and existing best-of-three ASGI round-trip <30ms benchmark. The user-approved 2026-10-29 amendment sets baseline actual listening-server current idle RSS <60 decimal MB, with <50MB retained as an optimization target. Use the scoped workload and three-process-per-mode protocol in [memory-budget-amendment.md](memory-budget-amendment.md), not app-only/peak/private memory or an arbitrary-workload promise.
**Constraints**: No process restart, mandatory dependency additions, persistent callable cache, global bytecode setting changes, or unrelated cache deletion.
**Scale/Scope**: Exact configured handler paths, not recursive project watching. Report watched file count, total source bytes, hardware, filesystem, runtime, and scheduler conditions with timing results; no unlimited-scale guarantee.

## Constitution Check

| Principle | Design assessment | Required evidence before completion |
| --- | --- | --- |
| Featherweight and instant | Aligned by design; no added runtime dependency or daemon | Baseline/reload-on/reload-off startup, dispatch, detection, and RSS measurements |
| Native execution/debugging | Preserve host runtime, source filenames, and existing invocation contracts | Source-line debugging check and sync/async regression coverage |
| Declarative onboarding | Reuse existing configuration and path validation; add one opt-in flag | CLI forwarding, external-config-path, and startup validation tests |
| Modular architecture | Isolate observation from dispatch; share loader identity/invalidation logic | Focused changes without integration or routing redesign |
| Test-first quality | Regression tests precede loader/watcher implementation | Red/green evidence, offline deterministic tests, typing/lint and coverage results |

The memory requirement was explicitly amended under constitution 2.0.0; this is not a retroactive passing result under the former 50MB gate. No other budget exception is approved. Performance and correctness compliance still require actual measurement; artifact review is not a passing runtime gate.

## Project Structure

### Documentation (this feature)

```text
specs/003-handler-hot-reload/
  spec.md
  plan.md
  research.md
  data-model.md
  quickstart.md
  contracts/reload-contract.md
  checklists/requirements.md
```

The explicit `speckit-plan` invocation authorizes Phase 0 research and Phase 1 design artifacts. Setup now resolves `.specify/feature.json` to this feature. No tasks, implementation, branch operations, or commits are implied. The setup output's `BRANCH=003-handler-hot-reload` is its feature identifier fallback; the actual Git branch remains `main`.

### Proposed Source and Test Scope (not changed)

```text
src/zerodock/
  cli.py
  engine/loader.py
  engine/watcher.py                 proposed isolated polling module
  gateway/app.py
  gateway/server.py
tests/unit/
  test_loader.py
  test_watcher.py                   proposed polling tests
  test_cli.py                       proposed if no equivalent coverage exists
tests/integration/
  test_hot_reload.py                proposed lifecycle/HTTP coverage
  test_performance_benchmarks.py
README.md
```

**Structure Decision**: Retain the current project layout. Before editing each area, inspect scoped instructions and existing coverage again; extend equivalent existing tests rather than duplicate them.

## Existing Implementation: Reuse, Replace, Preserve

| Area | Decision |
| --- | --- |
| Loader path hash identity | Reuse exact resolved-path identity algorithm; extract a shared helper rather than compute it differently in the watcher |
| Loader module execution | Preserve per-request execution; no persistent module/callable cache |
| Reload-enabled source execution | Extend selectively to bypass stale bytecode for configured handlers, preserving module metadata, source encoding, source filename, and tracebacks |
| Failed registration | Replace unsafe failure retention with ownership-aware cleanup, including entrypoint validation failures |
| Configuration parser | Reuse resolution relative to config directory; preserve rejection of missing startup files |
| Gateway invocation/errors | Preserve event, context, signature, timeout, normalization, and structured error contracts |
| CLI/server/app | Extend with default-disabled, backward-compatible optional reload arguments |

Verified correction: `load_handler()` currently overwrites `sys.modules` and executes a module on each request. Deleting an entry alone does not establish source freshness. No existing watcher, reload flag, or invalidation API was found in the inspected paths.

## Approved Design Boundaries

### Observation

- Use asynchronous standard-library polling of deduplicated canonical configured paths. Perform filesystem reads/fingerprinting off the event loop using bounded work, without creating an independent daemon or subprocess.
- Compare content fingerprints even if file metadata is unchanged. Retain fingerprints/status rather than whole source histories. Treat missing and unreadable states explicitly.
- Use a 100ms internal default interval, with at most one active scan per observer and no accumulating work queue. This is a design value, not measured compliance with the 500ms target. Coalesce duplicate revisions and observe the latest completed save rather than promising every intermediate version.
- Establish initial fingerprints before accepting requests, with an immediate subsequent scan so startup-window edits are not absorbed unnoticed. Preserve baseline missing-file validation.
- Observe exact target paths across rename-over and deletion/recreation; do not scan unrelated trees or depend on a file handle surviving replacement.
- Log recoverable failures with bounded retries; fail startup on fatal initialization errors. Explicitly log unexpected runtime observer termination. No source/request payload logging.

### Loader Freshness and Ownership

- Add `invalidate_handler_cache(module_name: str) -> None`; absent entries are a no-op and unrelated modules are not evicted. Route watcher calls through the shared canonical module identity helper.
- In reload mode, ensure configured handler source is executed freshly without trusting stale timestamp-based bytecode. Prefer a source-reading execution path retaining importlib-created module metadata and original filename; verify Python source encoding and debugger behavior before accepting it.
- Do not globally disable bytecode or recursively delete cache directories. Preserve non-reload successful loading semantics.
- Clean up failed initialization/entrypoint validation only when the registry entry is still the module owned by that load; do not remove another load's newer registration.
- Coordinate loading and invalidation per canonical module, with process-wide coordination where multiple apps share the identity. Never hold a lock across handler execution, awaiting a handler, or the full request.
- Define watcher registration ownership and release coordination metadata when unused, without breaking direct programmatic loader callers. Avoid a monotonically growing per-app registry or competing module identity schemes.
- In-flight callables may finish; the first request after completed invalidation must load fresh source. No last-known-good fallback.

### Lifecycle and Interfaces

- Add `--reload` to the `dev` subcommand; documented syntax is `zerodock dev --reload`. Do not silently add top-level `zerodock --reload` support.
- Forward a default-false option through `run_server()` and `create_app()` without breaking existing positional callers. Preserve implicit no-subcommand startup with reload disabled.
- Own polling through FastAPI lifespan; imports and app construction must not start observer tasks. Ensure shutdown stops and awaits owned work, including any pending filesystem work, without blocking the event loop.
- Keep Uvicorn process-restart reload disabled. Each application owns its observer lifecycle; shared module coordination must remain safe when one app shuts down before another.

## Implementation Phases (Awaiting Approval to Execute)

### Phase 1 - Regression Tests

Establish baseline behavior and reproduce stale-bytecode cases with temporary files, including preserved size/timestamps. Cover identity, idempotence, failed-load state, sync/async calls, source encoding, and reload-disabled per-request execution. Clean test-owned module entries and avoid repository handler edits.

### Phase 2 - Loader Changes

Extract shared identity logic; introduce targeted invalidation, reload-aware fresh-source execution, ownership-safe failure cleanup, and per-handler coordination. Verify same-file multiple entrypoints and same-basename different-file isolation. Do not hold coordination across user execution.

### Phase 3 - Polling Service

Implement fingerprint/status transitions, exact-path deduplication, startup baseline safety, atomic replacement, deletion/recreation, coalescing, bounded retries, and shutdown. Use controllable scan steps/events and deterministic clocks rather than arbitrary long sleeps in unit tests.

### Phase 4 - Lifecycle and CLI

Integrate app-owned observation and default-false CLI/server/app forwarding. Verify disabled mode starts no observer, existing callers remain compatible, external configuration paths resolve correctly, and startup rejects initially missing handlers.

### Phase 5 - Integration Coverage

Exercise actual application lifespan and HTTP dispatch for sync/async refresh, error recovery, multiple entrypoints, unaffected routes, in-flight invocations, concurrent loads/invalidation, and multiple app instances sharing a handler. Include an approved running-server check for unchanged PID/port; in-process ASGI tests alone do not prove that boundary.

### Phase 6 - Validation and Documentation

After separate execution approval, run focused tests before regression suites, existing packaging/diagnostics coverage, Ruff, mypy, and available coverage tooling. Do not install tooling or repair unrelated failures without approval. Record baseline versus modified startup, dispatch, detection, changed-file request, and idle RSS measurements for both modes. Distinguish app creation from process readiness and handler runtime from gateway overhead. Document environment and workload, retain raw measurements, and report any budget violation rather than weakening a threshold. Update README with scope, timing, recovery, and helper-module limitations.

## Requirement Traceability

| Spec requirements | Planned verification |
| --- | --- |
| FR-001, FR-012 | CLI/default behavior, existing callers, startup missing-file tests |
| FR-002, FR-005, FR-010 | Freshness, same-timestamp bytecode, sync/async HTTP, native-debugging and PID/port checks |
| FR-003, FR-004, FR-015 | Shared paths, config-relative paths, atomic saves, deletion/recreation, duplicate/unchanged scans |
| FR-006, FR-007, FR-009 | Idempotence, module isolation, failed-load recovery, ownership/concurrency and in-flight tests |
| FR-008 | Module side-effect/global-state regression tests in both modes |
| FR-011, FR-013, FR-014 | Lifespan, shutdown/resource cleanup, logs, startup/runtime observer failures |
| FR-016 | README review against all documented limitations |
| SC-001 through SC-007 | Acceptance scenarios, measured timing/resources, regression suites and core coverage report |

## Approval Record and Stop Condition

Approved: polling architecture A; preserve startup missing-file rejection; preserve per-request execution in both modes; all six improvements (freshness, content detection, failure cleanup, lifecycle ownership, per-handler coordination, observability/performance boundaries).

The later explicit `speckit-plan` invocation authorizes setup metadata and Phase 0/1 design artifacts, superseding the original three-artifact-only boundary. Do not implement phases, run tests/benchmarks, generate tasks, create branches, commit, or modify unrelated user files without separate approval.

## Phase 0 Research and Phase 1 Design

See [research.md](research.md) for decisions and primary documentation, [data-model.md](data-model.md) for runtime state and ownership, [reload contract](contracts/reload-contract.md) for CLI/library/lifecycle guarantees, and [quickstart.md](quickstart.md) for future validation commands. All are design documents, not executable implementation.

Design decisions resolve the source-bytecode strategy, polling interval, coordination lifetime, scan cancellation, startup errors, HTTP lifespan testing, and measurement boundaries. Preserve existing source execution on the request thread; moving user module execution into a worker is not part of this design.

### Post-Design Constitution Review

All five architectural gates remain aligned: no new dependency, host-native execution, unchanged configuration schema, isolated observation, and test-first verification. Runtime compliance remains pending implementation and measurement. No known design violation or unresolved scope clarification is accepted; an observed budget violation must stop implementation acceptance rather than be waived by these artifacts.

## Complexity Tracking

No approved constitutional deviations. Added coordination and fingerprinting are limited to the stated freshness/lifecycle requirements; no dependency graph, persistent cache, configuration reload, or production-worker protocol is introduced.
