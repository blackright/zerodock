# Approved RFC: Baseline Memory Acceptance Amendment

**Date**: 2026-10-29 (Europe/Budapest)
**Status**: Approved by the user before editing documentation or test limits.
**Constitution**: 1.0.0 -> 2.0.0 (governance only; no package release change).

## Decision and rationale

The user approved replacing the mandatory <50MB memory gate with **<60 decimal MB
current idle RSS for a documented small baseline workload**, while retaining <50MB
as a separately reported optimization target. The main product value is native,
Docker-free local execution and reliable in-process reload, not an unqualified 50MB
promise. Earlier measurements showed roughly 50-55MB actual listening-server RSS
with the current stack. No safe demonstrated project-only fix reliably met 50MB.

This is an explicit requirement change, not a runtime optimization or evidence that
the old requirement passed. No architecture/dependency/runtime switch, working-set
trimming, or change to startup/dispatch/detection/quality/coverage gates is approved.

## Testable baseline protocol

One actual listening gateway process; one GET route; one trivial Python handler no
larger than 1KiB and a config no larger than 1KiB; no additional handler dependencies
or attached debugger/profiler. Run three fresh processes in each reload mode
sequentially. After first HTTP 200, idle 250ms and take three current RSS samples
100ms apart. Every sample must be **<60,000,000 bytes**; exactly 60,000,000 fails.
Report whether samples also meet the non-blocking <50,000,000-byte target.

Use actual server PID WorkingSetSize on Windows, not private/peak/traced memory or
app-only RSS. Record runtime/build, dependency versions, OS/filesystem, workload
sizes, route/watched-file counts, raw samples, startup boundary and cleanup. Do not
claim untested platforms or arbitrary user handlers satisfy the baseline budget.

## Migration and verification

Align the constitution, active spec/plan/tasks/quickstart, README, raw-input drafting
spec and memory test assertion. Keep historical baseline, runtime-comparison,
profiling and failure reports unchanged except clearly dated current-status
annotations or links. Do not perform a global 50-to-60 replacement.

Boundary regressions must distinguish the 60MB gate from the 50MB target. Reuse the
existing app-only memory test as a supplementary check, but rerun actual listening
servers under the new protocol before claiming the memory gate passes. New evidence
must identify the amended requirement and preserve all samples.

The five unchanged Phase 6 blockers/concerns are reviewed independently: dispatch
outliers, existing repository quality findings, unmeasured core coverage, incomplete
runtime/platform coverage and final acceptance review. Completion of this amendment
does not complete Phase 6, authorize unrelated fixes/installations, or check T041-T048.
