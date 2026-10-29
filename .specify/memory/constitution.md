<!--
Sync Impact Report:
- Version change: 1.0.0 -> 2.0.0
- Ratification preserved: 2026-10-18; amendment approved by the user on 2026-10-29.
- Modified principle: I. Featherweight & Instant (<100ms, <50MB) ->
  I. Featherweight & Instant (<100ms, <60MB baseline RSS).
- Major bump: redefines the mandatory memory gate and its workload boundary;
  this is a governance version, not a package release/version change.
- Added guidance: baseline memory protocol; <50MB remains an optimization target.
- Unchanged: startup, dispatch, detection, architecture, quality and coverage gates.
- Approved rationale/migration: specs/003-handler-hot-reload/memory-budget-amendment.md.
- Removed sections: none. Dependent artifacts align through the separately approved update.
- Deferred items: None.
-->

# ZeroDock Constitution

## Core Principles

### I. Featherweight & Instant (<100ms, <60MB baseline RSS)
ZeroDock MUST boot up in under 100 milliseconds and maintain current idle RSS below
60 decimal MB for the documented baseline workload and memory protocol below.
Below 50MB remains an optimization target, not an acceptance gate. This baseline
limit is not a guarantee for arbitrary handlers, imports, route counts or environments.
Core execution is built exclusively on native asynchronous Python (`asyncio` and `FastAPI`).
No heavy containerization (Docker), virtual machines, or heavy background daemon
processes are permitted in the hot execution path.

### II. Native Execution & Total Debuggability
Function execution MUST run natively in the host Python runtime. ZeroDock utilizes dynamic module loading (`importlib` and targeted `sys.modules` cache management) to isolate invocations. Code under test MUST remain 100% accessible to standard IDE debuggers, allowing developers to set breakpoints (`breakpoint()`) and step through execution without black-box container boundaries.

### III. Declarative Zero-Config Onboarding
All routes, target files, and handler entrypoints MUST be declared in a concise, human-readable `serverless-local.yaml` file. A new developer MUST be able to clone a project, install dependencies, and run a single command to have a fully operational local serverless API gateway running without cloud credentials or complex setup.

### IV. Contributor-First Modular Architecture
Extensibility is strictly prioritized over monolithic completeness. Event transformers (AWS Lambda, Cloudflare Workers, GCP CloudEvents) and cloud simulation services (KV stores, Pub/Sub, S3 buckets, Cron loops) MUST exist as isolated, decoupled plugins. Adding or modifying an integration MUST NOT require modifications to the core event dispatch engine.

### V. Test-First & Fixture-Driven Quality (NON-NEGOTIABLE)
Test-Driven Development (TDD) is mandatory for all core components, transformers, and mock integrations. Every transformer MUST be validated against authentic, sanitized cloud payload fixtures. Tests MUST execute deterministically in sub-second time without relying on network access or external services.

## Technical Constraints & Performance Standards

- **Runtime Target**: Python 3.10+ using `asyncio` and `FastAPI` / `Uvicorn`.
- **Dependency Philosophy**: Keep core dependencies minimal (`fastapi`, `uvicorn`, `pydantic`, `pyyaml`). Cloud vendor SDKs (such as `boto3` or `google-cloud-*`) MUST NOT be required dependencies for running the core gateway.
- **Performance Budgets**:
  - Cold engine boot time: `< 100ms`.
  - Baseline memory consumption (idle): `< 60MB current RSS` (60,000,000 bytes).
  - Memory optimization target: `< 50MB current RSS` (50,000,000 bytes), reported separately.
  - Dispatch overhead per request: `< 5ms`.
- **Module Reloading**: Code changes MUST reload dynamically without requiring manual gateway restarts, preserving developer feedback speed.

### Baseline Memory Measurement

- Measure one actual listening gateway process with one configured GET route and
  one trivial handler source file no larger than 1KiB, a config no larger than 1KiB,
  no additional handler dependencies, and no attached debugger or allocation profiler.
- Measure reload disabled and enabled separately. Run three fresh processes per mode,
  with no concurrent agent-launched tests or profiling. After the first valid response,
  leave each server idle for 250ms, then collect three current RSS samples 100ms apart.
  Every sample MUST be below 60,000,000 bytes; do not average away a failing sample.
- On Windows use actual server PID WorkingSetSize; elsewhere use an approved current-RSS
  method. Peak RSS, private bytes, traced Python allocations and app-only processes
  MUST NOT substitute for actual server RSS. One MB is 1,000,000 bytes, not one MiB.
- Record OS/filesystem, runtime/build, dependency versions, source/config sizes, route
  and watched-file counts, all raw samples, readiness boundary and process cleanup.
  Compliance is limited to each disclosed environment/workload; untested environments
  remain untested. Record the <50MB optimization target separately from acceptance.
- Preserve evidence collected under the previous <50MB rule as historical results.
  A requirement amendment MUST NOT retroactively relabel old runs as passing.

## Development Workflow & Quality Gates

- **TDD Workflow**: Unit test cases and fixture JSONs must precede or accompany any feature implementation (Red -> Green -> Refactor).
- **Code Quality & Typing**: Strict type annotations enforced via `mypy`. Code formatting and linting enforced via `ruff`.
- **Contributor Ergonomics**: Every new event transformer or plugin MUST include clean interface documentation, automated tests, and a minimal working example in the `examples/` directory.
- **Review Gates**: Pull requests MUST maintain or improve test coverage (>90% target on core engine logic) and satisfy performance budgets.

## Governance

- The ZeroDock Constitution supersedes individual implementation preferences and ad-hoc architectural changes.
- Any change introducing external infrastructure dependencies or exceeding latency/memory budgets requires an explicit RFC and approval.
- Semantic Versioning (`MAJOR.MINOR.PATCH`) is strictly applied to all releases and configuration schemas.

**Version**: 2.0.0 | **Ratified**: 2026-10-18 | **Last Amended**: 2026-10-29
