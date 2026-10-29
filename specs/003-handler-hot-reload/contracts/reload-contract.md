# Reload Interface Contract

**Date**: 2026-10-29
**Status**: Proposed implementation contract within approved scope. No interface is implemented by this document.

## CLI

- Supported opt-in: `zerodock dev --reload` with existing `--config`, `--host`, `--port`, and `--log-level` options.
- Omission means `False`; implicit no-subcommand startup remains reload-disabled.
- Do not introduce top-level `zerodock --reload`, a YAML reload field, or configurable polling CLI flags.
- Missing startup handler files continue producing existing configuration errors.
- No extra package installation or Uvicorn restart mode is required.

## Library Interfaces

| Interface | Proposed extension / guarantee |
| --- | --- |
| `create_app(config=None, *, reload=False)` | Preserve existing positional config calls; application owns optional observer lifespan |
| `run_server(config_path=..., host=None, port=None, log_level=None, *, reload=False)` | Preserve existing positional calls; forward reload to app construction, not Uvicorn restart reload |
| `load_handler(file_path, handler_name, *, reload=False)` | Preserve two-argument callers and per-call execution; true bypasses stale handler bytecode |
| `invalidate_handler_cache(module_name: str) -> None` | Coordinated, idempotent removal limited to the requested loader-owned handler module; absent/foreign modules are no-ops |

Module identity is derived through one shared loader helper preserving the current algorithm. Track/validate loader ownership rather than treating an arbitrary matching prefix as proof of ownership. Invalidation does not remove dependency modules, recursively delete bytecode, cancel invocations, or invoke a handler. It cannot retroactively update existing callable references. Reliable bytecode freshness is guaranteed by reload-enabled loads, not by claiming `sys.modules` deletion alone refreshes every ordinary import.

## Lifecycle and Freshness

1. Existing configuration validation runs.
2. Reload-enabled lifespan registers ownership, obtains baseline/comparison scans, and starts the observer before startup completes.
3. Scans fingerprint exact configured targets off-loop. Changed revision states call the coordinated invalidation API.
4. The first request after completed stable-save invalidation loads fresh source. Earlier requests may already observe a change because modules still execute per request; observation is a guarantee boundary, not an exclusivity rule.
5. The default polling interval is 100ms between scans. Detection <=500ms is measured only under documented normal local workload conditions.
6. Shutdown drains outstanding scan work and releases app ownership; other applications' watchers and direct loader calls remain valid.

## Failure Contract

- Syntax errors, import failures, missing/unreadable files, absent entrypoints, and non-callable entrypoints use existing `HandlerLoadError`/gateway response conventions.
- No stale last-known-good response fallback or new public HTTP error envelope is introduced.
- Invalidation is not a request cancellation mechanism. Already held callables may finish normally.
- Corrected source recovers without restart; unrelated route behavior is preserved.
- Fatal observer initialization aborts startup. Recoverable per-file errors are retried without a tight loop. Unexpected runtime observer termination is error-logged; shutdown still cleans resources.

## Logging and Scope

Log enabled scope and invalidations at appropriate configured levels; detailed scan diagnostics belong at debug level. Never log each unchanged scan or source/request contents. Repeated identical filesystem errors are suppressed until a state/category transition or bounded retry notification.

No new HTTP routes, reload endpoint, helper dependency graph, dynamic route registration, source-history API, or production multi-worker protocol is added.
