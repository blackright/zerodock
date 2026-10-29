# Feature Specification: Reliable Startup and Dispatch Performance

**Feature Branch**: Not created; no Git operations performed.
**Created**: 2026-10-29
**Status**: Draft follow-up specification; ready for planning, not implemented.
**Input**: User requested a separate specification for the remaining performance
failures after functional handler hot reload was implemented for issue #1.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trust Local Startup and Request Speed (Priority: P1)

As a developer, I can start the gateway and invoke a small handler without
unexplained startup or request-delay failures in the supported test environments.

**Why this priority**: A working reload loop is less useful if speed varies enough
to break its existing performance requirements.

**Independent Test**: Execute a fixed, predeclared baseline protocol independently
in each required runtime, with reload disabled and enabled. Preserve every measured
sample and verify the unchanged startup and dispatch limits.

**Acceptance Scenarios**:
1. **Given** the baseline environment meets declared test conditions, **When** the
   fixed startup/dispatch experiment runs, **Then** all samples satisfy their
   existing limits without retries-until-green or different rules for each runtime.
2. **Given** an over-budget sample, **When** it is investigated, **Then** the report
   identifies measured contributors or explicitly records that the cause is unknown.
3. **Given** host contention, **When** a run is classified, **Then** only objective
   admission rules approved before measurement may distinguish it from the baseline;
   the run and its failed samples remain visible rather than silently discarded.

### User Story 2 - Keep Working Reload and Invocation Behavior (Priority: P2)

As an existing user, I retain correct responses, per-request handler initialization,
native debugging and reliable save recovery while performance is improved.

**Why this priority**: A faster result is not acceptable if it changes application
behavior or hides invalid source behind an old successful response.

**Independent Test**: Run the existing functional and lifecycle journeys before and
after each proposed change, independently from timing/profiling runs.

**Acceptance Scenarios**:
1. **Given** a saved configured handler, **When** invalidation completes, **Then** its
   next invocation executes fresh source without process or port replacement.
2. **Given** invalid code, deletion or an in-flight invocation, **When** recovery is
   exercised, **Then** the existing error, recovery and completion contracts remain.
3. **Given** reload is disabled or two applications share a handler, **When** requests
   and shutdown occur, **Then** compatibility and resource ownership are preserved.

### User Story 3 - Make Release Decisions From Honest Evidence (Priority: P3)

As a maintainer, I can distinguish a fixed performance defect from a favorable run,
a different measurement boundary, or a changed requirement.

**Why this priority**: Closing a functional issue must not erase unresolved project
performance debt or imply that untested environments passed.

**Independent Test**: Another maintainer follows the documented protocol and can
identify each measurement boundary, environment, result and remaining limitation.

**Acceptance Scenarios**:
1. **Given** earlier failed runs and newer passing runs, **When** completion is
   reviewed, **Then** both are retained with the actual changes and conditions.
2. **Given** an untested or failed runtime/platform, **When** support is documented,
   **Then** it is labeled explicitly, not silently dropped to improve results.

### Edge Cases

- Filesystem/security-scanner latency, process scheduling, and clock resolution
  can produce wall-clock outliers without proving which component caused them.
- Debuggers, coverage tracers and profilers add overhead and must not run during
  timing or memory acceptance measurements.
- A minimal handler does not represent arbitrary handler imports or execution time.
- Warm startup, interpreter/import startup and first HTTP readiness are different
  boundaries; reporting one as another can conceal an unmet requirement.
- Shared-handler races, partial writes and shutdown cancellation must remain safe.
- A runtime may have compatible functional behavior but fail a performance gate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Reuse existing measurements, functional tests and recorded failures;
  inspect existing implementations before proposing a replacement.
- **FR-002**: Record a bounded experiment protocol before execution, including fixed
  sample counts, warmups, workload, clock, boundaries, required environments and
  objective host-condition admission rules. Retain non-comparable/contended runs.
- **FR-003**: Investigate startup, loading, dispatch, filesystem waiting and host
  scheduling separately where measurements permit; distinguish evidence from inference.
- **FR-004**: Preserve the <100ms engine-startup and <5ms dispatch gates and their
  approved boundaries. Do not remove loader cost, switch to CPU time, replace maximum
  samples with a percentile, or weaken limits without a separate explicit amendment.
- **FR-005**: Preserve the <60,000,000-byte baseline actual listening-server RSS gate
  and its existing protocol; report <50,000,000 as an optimization target only.
- **FR-006**: Preserve opt-in/default behavior, fresh source, per-request execution,
  sync/async invocation, events/context/responses/timeouts, native source debugging,
  error recovery, targeted coordination and clean shutdown.
- **FR-007**: Do not introduce persistent callable/source caching, stale fallback,
  global serialization, process restarts or dependency/helper reload as shortcuts.
- **FR-008**: Prove an actionable bottleneck before making an optimization. Write a
  focused regression first and retain before/after evidence for each approved change.
- **FR-009**: Run functional, quality, statement-coverage and performance checks
  separately. Preserve passing configured lint/type checks and >90% statement coverage
  for touched core logic. Do not interpret profiled timings as acceptance evidence.
- **FR-010**: Do not disable security tools, force working-set trimming, tune the host
  to conceal failures, install tools/runtimes, change dependencies or rewrite the
  gateway without explicit approval of the specific proposal.
- **FR-011**: Report raw samples, source/config sizes, route/watched-file counts,
  runtime/build/dependencies, platform/filesystem, cleanup and the comparison method.
- **FR-012**: Keep failed and untested environments visible. Resolving this follow-up
  must not retroactively mark the original hot-reload Phase 6 evidence as passing.
- **FR-013**: Track this work in a separate issue linked from issue #1 before the
  maintainer closes #1 as a functional delivery. This specification is not itself a
  remote issue, approval to merge failing CI, or a constitutional exception.

### Key Entities

- **Experiment protocol**: Approved workload, environment set, admission conditions,
  measurement boundaries and fixed sample schedule.
- **Measurement run**: Samples and results tied to one protocol and source revision.
- **Performance hypothesis**: Suspected contributor, supporting evidence, confidence
  and the bounded experiment needed to test it.
- **Remediation decision**: Approved change or explicit rejection, associated tests,
  before/after observations and remaining limitations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every required startup and dispatch sample satisfies <100ms and <5ms
  respectively in three independently launched validation runs per required runtime
  and reload mode. Each run retains the existing ten startup samples and twenty
  dispatch samples after three dispatch warmups; no adaptive retry-until-pass.
- **SC-002**: Actual listening-server RSS is <60,000,000 bytes in every sample of the
  existing three-process-per-mode memory protocol. The <50MB goal is reported separately.
- **SC-003**: Save-to-invalidation detection remains <=500ms for the documented small
  local workload, including same-metadata and atomic saves, with fresh next responses.
- **SC-004**: All existing functional cases and configured quality checks pass, with
  >90% statement coverage for touched core logic and no owned observer leaks.
- **SC-005**: Completion evidence includes all registered runs, a supported/failed/
  untested matrix and a measured explanation of the remediation; an unexplained
  favorable run alone does not count as resolving the earlier variability.

## Assumptions

- Initial required comparison environments are the available Windows x64 Python
  3.12.0 and 3.14.6 builds with matched dependency versions. The old 3.12.0 patch is
  diagnostic, not a deployment recommendation. Any replacement patch/runtime requires
  separate approval and both old/new results must remain visible.
- The project still declares Python >=3.10; 3.10/3.11/3.13 and other operating systems
  remain explicitly untested until authorized checks are available. Planning must
  record this limitation and the pinned dependency snapshot's >=3.11 requirement;
  it must not silently redefine support or claim a complete platform matrix.
- The baseline remains one small configured handler and route under normal local
  conditions. The constitution and approved memory protocol remain authoritative.
- Existing hot-reload functionality is delivered; cross-runtime performance
  acceptance is still open. Technical audit/evidence is in implementation-audit.md.
- No implementation, benchmark execution, installation, Git operation or budget
  amendment is authorized by writing this specification. The next step is planning.

## Non-Goals

No Rust rewrite, replacement web framework/server, helper/config reload, cloud
adapter work, new public flags/endpoints, release publishing, unapproved support
changes, or relaxed performance thresholds. Such proposals require separate scope
and governance approval rather than being presumed fixes.
