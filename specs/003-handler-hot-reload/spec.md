# Feature Specification: FEAT-002 Hot-Reloading & Dynamic Module Cache Invalidation

**Feature Branch**: Not created; current branch remains `main`.
**Created**: 2026-10-29
**Status**: Phases 1-5 implemented and approved; Phase 6 acceptance remains open. The user approved the 2026-10-29 baseline-memory amendment; see memory-budget-amendment.md. This does not approve other scope changes or waive remaining gates.
**Input**: GitHub issue #1 and the decisions approved in conversation: standard-library asynchronous content polling, existing missing-file startup validation, per-request execution in both modes, and all six reliability improvements.
**User-directed issue handoff (2026-10-29)**: Functional delivery may be reviewed for issue #1 closure after a real linked performance follow-up is created. See [issue-handoff.md](issue-handoff.md) and [004-performance-remediation](../004-performance-remediation/spec.md). This is not a declaration that unresolved Phase 6 performance criteria passed or a change to project budgets.
**Source**: https://github.com/blackright/zerodock/issues/1

The directory number 003 follows the existing specification sequence; FEAT-002 is the issue label, not a renumbering of the existing packaging feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See saved handler changes without restarting (Priority: P1)

As a developer, I enable reload, edit a configured handler, and receive its updated result without restarting the gateway or reconnecting to a different port.

**Why this priority**: Reliable execution of saved source is the feature's primary value.

**Independent Test**: Start a reload-enabled gateway, observe response A, save response B, wait for confirmed detection/invalidation, and request the same route again.

**Acceptance Scenarios**:
1. **Given** a running reload-enabled gateway, **When** a completed save is detected and invalidated, **Then** its next request executes the saved source without process restart or port rebinding.
2. **Given** a rapid same-length edit whose timestamp is unchanged, **When** observation completes, **Then** the next response reflects the changed contents rather than outdated compiled code.
3. **Given** multiple routes or entrypoints sharing one source file, **When** that file changes, **Then** every affected route observes the updated source while unrelated files remain isolated.
4. **Given** either a synchronous or asynchronous handler, **When** it is edited, **Then** reload preserves its invocation and response behavior.

### User Story 2 - Recover from saves and errors (Priority: P2)

As a developer, I can use atomic editor saves, temporarily delete a handler, or introduce an error and then fix it without restarting the gateway.

**Why this priority**: Normal editing workflows must not leave the gateway permanently broken or silently serving obsolete results.

**Independent Test**: Introduce a syntax error, observe the existing error response, fix it, and observe recovery while another route continues responding.

**Acceptance Scenarios**:
1. **Given** invalid handler source, **When** its route is requested, **Then** the existing structured error response is returned rather than a stale successful result.
2. **Given** an affected route returning a load error, **When** valid source is saved and detected, **Then** that route succeeds without manual cleanup.
3. **Given** a handler present at startup, **When** it is replaced atomically or deleted and recreated, **Then** observation continues and the recreated source becomes usable.
4. **Given** an in-flight invocation, **When** its source is invalidated, **Then** that invocation may finish with its existing callable and subsequent requests observe refreshed source.

### User Story 3 - Preserve existing behavior and clean shutdown (Priority: P3)

As an existing user, I retain the current behavior without enabling reload, and enabling reload does not leave observation resources behind after shutdown.

**Why this priority**: The development feature must remain backward-compatible and lightweight.

**Independent Test**: Compare default operation with reload-enabled operation and exercise application startup/shutdown repeatedly.

**Acceptance Scenarios**:
1. **Given** reload is not enabled, **When** the gateway runs, **Then** no file observer starts and handler modules retain existing per-request execution behavior.
2. **Given** a configured handler is missing before startup, **When** configuration is loaded, **Then** existing startup validation rejects it in both modes.
3. **Given** a running observer, **When** the application shuts down, **Then** its observation work ends and its resources are released.
4. **Given** a configuration outside the working directory, **When** reload runs, **Then** the same handler targets used by normal execution are observed.

### Edge Cases

- Repeated saves and duplicate observations converge on the latest completed save; intermediate versions need not execute.
- Requests racing incomplete writes may fail; a later valid stable save must recover automatically.
- Missing functions, non-callable entrypoints, unreadable files, and import errors retain existing route error contracts.
- Unrelated files, generated bytecode, environments, and tool caches do not cause handler invalidation.
- Shared paths are observed once per application; multiple application instances must not corrupt process-wide handler state.
- Startup baseline collection must not swallow changes made before the observer starts serving requests.
- Observation failures must be visible and must not produce tight retry loops or silently disable reload.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Developers MUST be able to opt into reload; it MUST be disabled by default and preserve existing callers and implicit default startup.
- **FR-002**: Reload MUST occur within the running gateway without process replacement, port rebinding, or an external daemon.
- **FR-003**: Only configured handler source paths MUST be observed; shared paths MUST be deduplicated and configuration-relative resolution preserved.
- **FR-004**: Detection MUST identify content changes even when size and timestamp match the previous version, including atomic replacement and post-startup deletion/recreation.
- **FR-005**: After detection and invalidation of a completed stable save, the next request MUST execute fresh source, including when outdated compiled code exists.
- **FR-006**: Invalidation MUST be targeted and idempotent; unrelated handlers and dependencies MUST NOT be evicted.
- **FR-007**: Failed loads MUST NOT leave partially initialized handler registrations or silently serve a stale successful version; corrected source MUST recover without restart.
- **FR-008**: Per-request module execution MUST be preserved in both modes; persistent callable/module reuse MUST NOT be introduced.
- **FR-009**: Loading and invalidation MUST be coordinated per handler; unrelated routes MUST NOT be globally serialized and existing invocations MAY complete normally.
- **FR-010**: Existing invocation signatures, synchronous/asynchronous support, events, contexts, timeouts, response normalization, and native debugging MUST remain compatible.
- **FR-011**: Observation MUST start and end with application lifespan, establish a safe initial baseline, and release owned tasks and resources on shutdown.
- **FR-012**: Existing missing-handler startup rejection MUST remain unchanged; runtime observation MUST continue after a previously present handler disappears.
- **FR-013**: Enablement, scope, invalidation, and observation failures MUST be logged using appropriate existing conventions without source contents, request data, or secrets.
- **FR-014**: Recoverable filesystem errors MUST permit later recovery; fatal observer initialization failures MUST prevent a misleading reload-enabled startup. Unexpected observer termination MUST be explicitly logged as an error rather than silently ignored.
- **FR-015**: Duplicate observations MUST be coalesced without losing the latest completed saved version; unchanged contents MUST NOT trigger repeated invalidation.
- **FR-016**: Documentation MUST explain enablement, default behavior, freshness timing, error recovery, handler-only scope, helper-module limitations, and debugger compatibility.

### Key Entities

- **Handler target**: A configured source path with one or more callable entrypoints and routes.
- **Observed revision**: A content fingerprint or missing/unreadable state for a handler target.
- **Reload lifecycle**: Application-owned observation state with explicit initialization, running, failure, and shutdown behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All acceptance scenarios demonstrate fresh responses after confirmed invalidation without process/port restart, including same-size/same-timestamp edits.
- **SC-002**: Detection and invalidation complete within 500ms of a completed stable save under the documented local test workload; environment and workload limits accompany results.
- **SC-003**: Syntax/import failures and deletion/recreation recover after corrected source is detected; unrelated route requests continue succeeding throughout.
- **SC-004**: Default operation creates zero observer tasks, and shutdown leaves zero application-owned observer tasks or file handles active.
- **SC-005**: Existing startup and request benchmarks remain passing; baseline and modified measurements distinguish startup, request processing, detection, and idle resources.
- **SC-006**: Project budgets remain acceptance gates: cold engine boot below 100ms, documented baseline current idle RSS below 60 decimal MB (60,000,000 bytes), and isolated dispatch overhead below 5ms. Below 50MB is a separately reported optimization target, not a blocking gate. Memory acceptance uses the approved small listening-server workload and three-fresh-processes-per-reload-mode protocol in [memory-budget-amendment.md](memory-budget-amendment.md), with every sample below the limit and the tested runtime/platform disclosed. App-only RSS and existing end-to-end timing benchmarks do not substitute for these measurements. Historical failures under the former 50MB requirement remain unchanged.
- **SC-007**: Offline unit/integration regression suites pass, with a greater-than-90% coverage target for touched core engine logic and no repository handler modifications by tests.

## Assumptions

- This is local development functionality, not a production multi-worker coordination mechanism.
- A save is stable once writing has completed; visibility is guaranteed after detection/invalidation, not before observation or during a racing write.
- The 500ms target applies under normal local filesystem conditions, not arbitrary file sizes, remote filesystems, or a stalled event loop; verification must state its actual workload.
- Initial handler files must exist. Changing configuration, adding routes, following changed imports, and migrating handler globals are outside scope.
- Imported-helper changes alone may require a manual restart.
- Approved technical choices and exact interface requirements are recorded in [plan.md](plan.md), keeping implementation mechanics separate from user requirements.
- Existing user edits to unrelated files must remain untouched. No implementation, test execution, branch creation, or commit is authorized by artifact creation.
