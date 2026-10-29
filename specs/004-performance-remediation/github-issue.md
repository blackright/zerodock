# Follow-up Issue Body

Create a new GitHub issue manually with this title:

**[PERF] Resolve startup and dispatch variability across supported runtimes**

Copy the body below, keeping the reference to #1. Insert the new issue number into
the original issue/PR only after GitHub has actually created it.

---

## Background

Follow-up to #1, which delivers functional in-process handler hot reload. This issue
tracks unresolved project-wide performance acceptance, not missing reload behavior.

Specification: `specs/004-performance-remediation/spec.md`.
Audit: `specs/004-performance-remediation/implementation-audit.md`.

## Current evidence

- Windows/Python 3.14.6: 194 tests passed in the latest full run.
- Isolated Windows/Python 3.12.0: 192 passed, 2 performance failures; all functional cases passed.
- Reload-off direct ASGI total: 36.2505ms against <5ms.
- Reload-on warm-import startup: 230.2233ms against <100ms; recorded direct ASGI max 23.7090ms.
- Root cause is not established; do not assume either the host or application is responsible.
- Configured lint/format/type gates pass; touched-core statement coverage is >90%.
- The separately approved <60MB baseline actual-server memory gate passes; <50MB
  remains an optimization target, not this issue's failed gate.

## Acceptance

- Investigate with a fixed, predeclared protocol and retain all raw/failed runs.
- Preserve existing budget definitions, reload behavior, per-request execution and cleanup.
- Demonstrate unchanged <100ms startup and <5ms dispatch gates in three independent
  runs per required runtime/reload mode, using existing sample counts and warmups.
- Preserve <60MB baseline RSS, <=500ms detection, functional tests, configured quality
  and >90% touched-core statement coverage.
- Record supported/failed/untested environments; no favorable-run-only closure,
  runtime removal, hidden timing-boundary change or unapproved threshold relaxation.

No architecture rewrite, installation or dependency change is approved by opening
this issue. Plan the work and request approval for the specific implementation.
