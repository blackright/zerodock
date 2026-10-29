You are an elite Product Architect and Principal Systems Engineer with full contextual access to our current codebase. Your task is to analyze the user's provided feature specification, evaluate it against our existing repository architecture, improve it with strict constraints, and prepare it perfectly for a spec generation command (like `/speckit specify`). 

CRITICAL PROTOCOL: You must present your analysis, architectural options, and the draft spec preview to the user first. You are STRICTLY FORBIDDEN from running any commands, modifying files, or finalizing the specification until the user explicitly responds with "Approved" or "Proceed".

Follow this exact multi-step execution lifecycle:

### 📊 1. Codebase Alignment & Feasibility Analysis
Compare the user's provided specification against the current project codebase and determine:
* **Feasibility:** Is this feature technically viable within our current stack, data models, and architectural patterns? Highlight any breaking structural conflicts.
* **Duplication Audit:** Have parts of this feature (or its underlying logic/entities) already been implemented in the codebase? Identify what already exists so we do not reinvent the wheel.

### 🚀 2. Proposed Innovations & Rationales (Strictly 5 to 6 Items)
Propose exactly between 5 and 6 innovative, production-grade feature enhancements or engineering best practices to add to the specification. For each proposed innovation, you must provide:
* **The Innovation:** The name and crisp definition of the requirement.
* **Why It Is Recommended:** The exact technical, performance, or user-experience problem it solves.
* **System Improvement:** The measurable architectural benefit (e.g., fault tolerance, zero-precision loss, scale readiness).

### 🏆 3. Highest Recommended Innovation
Explicitly select one innovation from your list as the absolute highest priority recommendation. Provide a detailed paragraph explaining exactly why this specific feature takes precedence over the others based on our current codebase maturity.

### 🎛️ 4. Architectural Implementation Options
Provide a markdown comparison table offering 2 alternative implementation patterns for how this entire feature should be structurally handled in our codebase. List the Pros and Cons of each approach, explicitly factoring in our existing technical debt and patterns.

### 📄 5. Draft Spec Preview
Show a preview of the fully rewritten, improved, and structured specification incorporating the verified baseline requirements along with your 5–6 new innovations, ready to be passed to the command tool.

### 🛑 CONTROL GATE: AWAITING AUTHORIZATION
Halt immediately. Present your full analysis and the draft spec preview. Do not run any commands. Ask the user for their preferred architecture option and explicit authorization to execute.

--------------------------------------------------
[RAW INPUT SPECIFICATION START]
{{

Feature: [FEAT-002] Hot-Reloading & Dynamic Module Cache Invalidation
Source: GitHub issue #1, https://github.com/blackright/zerodock/issues/1 (open when checked).

Objective
Enable developers to edit configured Python handler files and receive updated responses from the running ZeroDock gateway without restarting the process, changing its PID, rebinding its port, or interrupting unrelated routes. Deliver explicit, opt-in development file watching and safe targeted module invalidation while retaining native Python debugging and existing performance guarantees.

Verified repository context and important correction to the issue premise
- Python 3.10+, FastAPI, Uvicorn, argparse CLI; minimal core dependencies are fastapi, uvicorn, pydantic, and pyyaml.
- src/zerodock/engine/loader.py resolves handler paths and derives module identities as zerodock.handlers.mod_<first 12 hexadecimal characters of SHA-256 of the resolved path>. Different files must remain isolated even when their basenames match.
- load_handler() currently creates and executes a new module on every call and overwrites sys.modules; it does NOT currently return a cached module or callable. src/zerodock/gateway/app.py calls it on every request. Therefore, do not assume that deleting sys.modules alone fixes hot reloading or claim that handlers currently always require a restart. Account for stale bytecode and verify actual behavior with regression tests.
- There is currently no --reload CLI option or watcher in the inspected CLI/server/app paths. The CLI's dev command forwards options to run_server(), which builds an app and passes the app object to uvicorn.run().
- Existing error handling uses HandlerLoadError and the gateway's structured error responses; reuse these rather than inventing another public error format.
- Existing tests cover sync/async invocation, handler arity, missing files, missing entrypoints, and non-callable attributes. Performance tests assert configuration parsing plus app creation under 100ms and best measured ASGI round-trip under 30ms. These are not equivalent to measuring full CLI process startup or isolated dispatch overhead.
- Follow .specify/memory/constitution.md: native execution, minimal dependencies, test-first development, cold boot <100ms, baseline current idle RSS <60 decimal MB (60,000,000 bytes), dispatch overhead <5ms, and debugger compatibility. Keep <50MB as a separately reported optimization target. Use the approved small listening-server workload and three-process-per-mode sampling protocol in specs/003-handler-hot-reload/memory-budget-amendment.md; disclose the tested environment and do not promise these limits for arbitrary handlers. Document measurement boundaries rather than treating existing round-trip tests as proof of all constitutional budgets.

User stories
1. As a developer, I run zerodock dev --reload, request a configured route, edit its handler, and receive the updated result on the first request after the save has been detected and invalidation completed, without restarting the gateway.
2. As a developer, I can save repeatedly, use an editor that saves by atomic replacement, introduce a temporary syntax error, and fix it without restarting the gateway or losing access to unrelated routes.
3. As an existing user, I can continue running without --reload with existing CLI, configuration, invocation semantics, and performance unchanged.

Required behavior and scope
- Add --reload to zerodock dev, disabled by default. Pass the setting through server/app setup using backward-compatible optional arguments; existing programmatic callers and implicit no-subcommand startup must still work. Document the supported CLI syntax and defaults.
- Implement in-process watching, not Uvicorn's process-restart reload mode, subprocess workers, containers, or an external daemon.
- Watch the canonical resolved paths of configured handler source files only. Deduplicate shared files. Resolve paths consistently with the configuration parser and loader, including when the configuration is outside the current working directory.
- Handle file modifications, atomic replacement/rename-over saves, deletion, and recreation at configured paths. Missing files must remain eligible for detection when recreated. Ignore unrelated files, generated bytecode, virtual environments, and tool caches.
- Provide invalidate_handler_cache(module_name: str) -> None in src/zerodock/engine/loader.py as requested by the issue. It must be safe and idempotent for absent modules and must not evict unrelated modules. Reuse one canonical path-to-module identity mechanism wherever loading and watcher invalidation need it.
- Guarantee source freshness after invalidation, including rapid same-length edits within a filesystem timestamp/bytecode timestamp window. Merely calling importlib.invalidate_caches() or removing sys.modules is insufficient as a specification of this guarantee. Choose a targeted strategy that avoids stale .pyc execution without disabling bytecode globally or deleting unrelated caches.
- Remove failed or partially initialized handler modules from loader-owned cache state so subsequent fixed code can load successfully. A reload failure must not silently serve stale last-known-good code.
- Multiple routes/entrypoints pointing at the same file must all observe refreshed code. Different files must remain isolated. Preserve sync/async support, handler arity, events, contexts, timeouts, response normalization, and native debugger breakpoints.
- Preserve current per-request module execution when reload is off. Introducing persistent module/callable reuse changes module-global state semantics and is not an implicit requirement of this issue; any such proposal must identify the compatibility impact and require explicit architectural approval.

Reliability, concurrency, and lifecycle
- Establish an explicit freshness boundary: saves become visible after detection/invalidation, not necessarily to requests racing a write. Once a completed stable save has been invalidated, the next request must execute fresh source. Requests already holding an old callable may complete normally.
- Target detection and invalidation within 500ms of a completed stable save under normal local filesystem conditions; document any polling/debounce values and validate timing with bounded, non-flaky tests. Do not promise instantaneous detection before a watcher observes the change.
- Coalesce duplicate filesystem events and handle rapid successive saves without losing the latest version. Cover same-size/same-timestamp edits with a reliable content-change strategy, not timestamp-only assumptions.
- Coordinate loading and invalidation so concurrent requests cannot receive partially initialized modules or retain a stale callable cache. Avoid global request serialization and document process-wide sys.modules ownership and behavior if multiple app instances watch the same handler.
- Start watching with the application lifecycle, establish a baseline without missing startup-window edits, and stop/cancel/await watcher resources on shutdown. Avoid orphan tasks, leaked file handles, duplicate watchers, and import-time background work.
- Prefer bounded standard-library asynchronous polling of configured files to keep installation lightweight. Compare this with an optional watchfiles-based event watcher, including dependency footprint, portability, atomic saves, and shutdown behavior; do not add a mandatory dependency without justification and approval.
- Watcher failures must be logged clearly rather than silently disabling reload. Define startup failure versus recoverable runtime filesystem errors and avoid tight error loops. Missing/unreadable handler source should use existing request error behavior while observation continues where possible.
- Log reload enablement and watched scope, invalidation events, and failures through existing logging conventions and levels. Do not log source contents, request data, or secrets. Keep normal requests free from noisy reload logs.

Error and recovery expectations
- Syntax/import errors, missing files, missing handler functions, and non-callable entrypoints produce the existing structured error response on the affected route; other routes remain usable.
- Fixing the file restores success after the next detection/invalidation without manual cache cleanup or process restart.
- No fallback to stale successful responses after a failed save. Transient partially written files may fail a request, but subsequent stable saves must recover automatically.

Explicit non-goals
- Reloading serverless-local.yaml, adding/removing routes at runtime, changing CLI flags at runtime, recursively watching the whole project, or automatically reloading imported helper/dependency modules.
- Transitive dependency graph tracking, invalidating third-party/stdlib modules, preserving or migrating handler module-global state, production multi-worker coordination, and process restart-based reload.
- Redesigning gateway routing, invocation/event contracts, cloud integrations, unrelated diagnostics, or packaging beyond a justified optional watcher dependency.
- Imported helper changes alone are outside scope; document that they may require a manual restart. Do not imply full application hot-module replacement.

Acceptance criteria and verification
1. A running gateway with --reload serves version A, detects a completed handler save, then serves version B on its next request without process/port restart; demonstrate both sync and async handlers.
2. Unit tests in tests/unit/test_loader.py cover deterministic module identity, idempotent invalidation, rapid same-length edits, bytecode freshness, failed-import cleanup, multiple entrypoints, and module isolation.
3. Watcher tests cover duplicate events, repeated saves, atomic replacement, deletion/recreation, unchanged files, unrelated files, shared paths, startup/shutdown, and recoverable filesystem errors. Prefer temporary directories and controlled clocks/events over arbitrary sleeps.
4. Integration tests exercise actual application lifespan and HTTP dispatch, verify refresh and syntax-error recovery, prove unaffected routes continue working, and cover concurrent/in-flight requests without partially initialized modules. Include CLI argument forwarding and default-disabled behavior.
5. Tests confirm reload-disabled behavior remains compatible with the current per-request loader; no background watcher runs when disabled.
6. Existing unit and integration suites pass with pytest, including packaging and diagnostics coverage. New tests are offline, fixture-driven, isolated from the repository's real handler files, and clean up their own module entries/resources.
7. Existing startup (<100ms) and ASGI latency (<30ms) benchmarks remain passing. Measure reload-on and reload-off overhead separately, including watcher startup, idle resource usage, and the changed-file request path; assess constitutional <5ms dispatch overhead and <60MB baseline current idle RSS using the approved workload, decimal-byte limit, actual server PID and three-process-per-mode protocol. Report the <50MB optimization target separately, preserve failures under the former rule, and disclose methodology/environment. Report baseline versus modified measurements rather than claiming zero overhead.
8. Maintain project typing/lint conventions and target >90% coverage of touched core engine logic. Do not change unrelated code to satisfy pre-existing failures.
9. Update README usage with zerodock dev --reload, default behavior, detection timing, failure/recovery behavior, handler-only watch scope, imported-helper limitations, native-debugging behavior, and any optional dependency installation instructions.

Specification drafting guidance
Use this as input to a feature specification, not authorization to implement the feature. Separate verified facts from architectural proposals. Retain the surrounding template's analysis, architecture comparison, innovation recommendations, draft preview, and approval gate. Any proposed enhancements must stay within this issue's scope; prioritize deterministic source freshness, targeted invalidation, failure recovery, lifecycle cleanup, concurrency safety, and measurable performance rather than unrelated platform features. Explicitly resolve architecture and compatibility tradeoffs before implementation.

}}
[RAW INPUT SPECIFICATION END]
