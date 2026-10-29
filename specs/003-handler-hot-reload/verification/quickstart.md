# Phase 6 Quickstart Execution Status

**Date**: 2026-10-29 (Europe/Budapest)
**Current status (2026-10-29 closeout)**: Live refresh/recovery, PID/port continuity, controlled native pdb, graceful stop and same-port restart are verified in live-acceptance.md. Amended baseline memory passes in memory-amendment-validation.md. Final full suites: Windows/3.14.6 194 passed; Windows/3.12.0 192 passed/2 performance failures. Repository quality and >90% touched-core statement coverage now pass; see phase-06-closeout.md. Runtime-status validation is recorded, not a claim that every performance environment or GUI/IDE passed. Final Phase 6 acceptance remains open.

The feature quickstart was corrected to describe the implemented flag, existing test files, project interpreter commands, and known baseline limitations. README now documents opt-in/default behavior, polling/freshness, recovery, exact handler scope, helper limitations, debugging, and shutdown limitations without promising unverified resource budgets.

Phase 6 live evidence is in live-acceptance.md with raw logs and retained harness failures. No GUI/IDE session was executed. Earlier live-server evidence remains in us1-live-server.md; controlled debugger and lifecycle evidence remains in us3.md. Historical and new observations are distinguished explicitly.

The later separately approved runtime comparison created an isolated Windows/Python 3.12.0 environment with matching dependency versions; see runtime-comparison.md. Its full suite had 188 passes/1 dispatch failure, while all reload-on live RSS trials still exceeded 50MB. Original .venv and base/global packages were not modified. Python 3.10, 3.11, 3.13, Linux, macOS and GUI/IDE-specific behavior remain untested. Final acceptance remains open; no runtime default was switched.
