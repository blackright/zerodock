# Phase 6 Acceptance Matrix — Not Accepted

**Date**: 2026-10-29 (Europe/Budapest)
**Current status (2026-10-29 closeout)**: Phase 6 remains incomplete. Documentation/benchmark implementation, repository quality, core coverage and live/runtime-status validation are complete (T041/T042/T044/T046). Final Windows/3.14 suite passes 194 tests; subsequent Windows/3.12 suite has 192 passes/2 performance failures. Loader statement coverage is 99.2063%, watcher 95.4023%. The amended <60MB actual-server memory gate passes 18 samples, maximum 54.9888MB; <50MB remains an unmet non-blocking target. T043/T045/T047/T048 remain open. See phase-06-closeout.md; no failing runtime is silently excluded and earlier evidence remains preserved.

| Requirement | Current evidence / remaining gate |
| --- | --- |
| FR-001 opt-in/backward compatibility | us1.md/us3.md; regression compatibility cases pass |
| FR-002 in-process continuity | us1-live-server.md and live-acceptance.md: sync/async A/B/C responses retained PID 40764 and port 53347 |
| FR-003 exact/deduplicated/config-relative targets | us1.md/us3.md; regression cases pass |
| FR-004 content/atomic/deletion detection | us1.md/us2.md; two new save timing cases pass |
| FR-005 fresh source including stale bytecode | us1.md; existing reload regressions pass |
| FR-006 targeted/idempotent invalidation | foundations.md/us2.md; regression cases pass |
| FR-007 failed-load cleanup and recovery | us2.md; regression cases pass |
| FR-008 per-request execution | us3.md; regression cases pass |
| FR-009 coordination/in-flight calls | foundations.md/us2.md/us3.md; regression cases pass |
| FR-010 invocation/debugging compatibility | us3.md and live-acceptance.md: final controlled real-HTTP pdb source/event/continue check passes; GUI/IDE untested |
| FR-011 lifespan ownership/cleanup | us3.md plus live shutdown-complete logs, zero exit, listener closure and same-port restart; no new full-suite resource snapshot |
| FR-012 startup/runtime missing-file distinction | us2.md/us3.md; regression cases pass |
| FR-013 logging/privacy | Watcher call sites reviewed: enablement/scope/targeted identity/state/category only; unchanged scans emit nothing. No source/request bytes enter reload messages. Existing gateway exception diagnostics remain their separate unchanged contract |
| FR-014 observable failures/recovery | us2.md/us3.md; regression cases pass |
| FR-015 duplicate coalescing/latest revision | us1.md/us2.md; regression cases pass |
| FR-016 documentation | README and feature quickstart cover flags/default, 100ms polling, freshness/recovery, helper limitations, debugging, no extra watcher install and the scoped memory amendment; final overall acceptance remains open |
| SC-001 acceptance journeys/no restart | Earlier story evidence plus Phase 6 live sync/async normal/atomic save and recovery without restart; same PID/port verified |
| SC-002 <=500ms detection | Six new samples 80.0743-117.599ms for one 61-byte local handler |
| SC-003 failure/recovery/isolation | Existing unit/integration scenarios pass in Phase 6 suite |
| SC-004 observer cleanup | Existing gated lifecycle cases pass; live final shutdown/restart and process/listener cleanup verified; initial debugger-harness failure retained |
| SC-005 benchmark preservation | Original config/app and best-of-three ASGI checks pass in both final runs. Added timing gates pass on 3.14; two cases fail on 3.12 |
| SC-006 budgets | PARTIAL: amended memory passes 18 actual-server samples, max 54.9888MB. Final 3.14 startup/dispatch gates pass; isolated 3.12 off dispatch 36.2505ms and on startup 230.2233ms fail unchanged limits. Whole-process readiness is separately reported, not claimed <100ms |
| SC-007 offline suite/core coverage | Final 3.14 suite 194 passed; isolated 3.12 192 passed/2 performance failures, no skips. Statement coverage loader 125/126 (99.2063%), watcher 166/174 (95.4023%) passes >90%; combined-runtime regression acceptance remains open |

Six reliability improvements reviewed against code and final tests: fresh bytecode-independent source (loader compilation/metadata tests); safe per-target coordination (active lease/owner and concurrent-load tests); atomic/missing-file recovery (watcher state and HTTP recovery tests); lifecycle ownership (gated cancellation/draining, repeated and shared-app lifespans); visible observer failures (fatal startup/terminal-task logging tests); bounded exact-target observation (deduplication, one outstanding scan, unchanged/duplicate revisions and content-only state). No persistent source/callable history, helper graph, configuration reload, process replacement or new public endpoint was introduced. Functional acceptance journeys pass; these findings do not waive the separate failed performance environment.

Constitution review: no new runtime dependency, daemon, persistent callable cache, helper graph, route/config reload, or production worker protocol was added. Native execution and configuration/invocation boundaries remain unchanged. Constitution 2.0.0 amends only scoped memory acceptance. Repository quality and touched-core statement coverage now pass. Startup/dispatch do not pass in every tested environment; supported-runtime/platform coverage is explicitly bounded. No other exception is approved and no blanket constitution-compliant release claim is made.

User's no-Git rule was followed: no Git commands, Git data/config access, branch creation, commits, or ignore-rule changes. Feature selection used .specify/feature.json directly; no repository script with potential Git side effects was executed. Existing specification ignore behavior is reported historically, not freshly verified. No hooks file exists. Requirements-quality checklist remains 19 checked, 0 unchecked; these markers are not feature acceptance and were not changed.

Task status: T041/T042/T044/T046 checked for completed documentation/benchmark work, passing configured quality/core coverage, and completed live/runtime-status recording. T043/T045/T047/T048 remain unchecked because combined-runtime regression/performance and final acceptance/reconciliation are incomplete. Recording a failing platform is not acceptance of it. No Phase 6 completion or budget waiver; further fixes/installations must respect user approval.
