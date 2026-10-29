# Architecture

ZeroDock is a Python CLI, a declarative route loader, and a native HTTP execution
gateway. It does not launch containers or deploy functions to a cloud service.

## Request flow

```text
CLI -> YAML validation -> configured FastAPI application -> Uvicorn listener
HTTP request -> handler load -> event/context -> invocation -> response normalization
```

The CLI resolves startup options and passes an application object to the server.
Configuration-relative paths identify Python source files and callable entrypoints.
For each request, the gateway loads the target, constructs local event/context
objects, invokes the function, and normalizes its result.

## Components

| Area | Responsibility |
| --- | --- |
| `src/zerodock/cli.py` | Argument parsing and default startup |
| `config/models.py` and `config/parser.py` | Schema, diagnostics, path resolution, and file-existence validation |
| `gateway/server.py` and `gateway/app.py` | Listener setup, lifespan, routing, invocation orchestration, and errors |
| `engine/loader.py` | Canonical identity, ownership, loading, invalidation, and invocation conventions |
| `engine/watcher.py` | Optional exact-target content observation and lifecycle cleanup |
| `engine/event.py` and `engine/context.py` | Local HTTP event and invocation metadata |
| `gateway/response.py` and `gateway/errors.py` | Response conversion and development diagnostics |

## Loading and identity

Handler identity uses the canonical resolved path and the existing truncated SHA-256
path hash. Distinct files remain separate even when their basenames match.

The loader executes a fresh handler module on every call in both modes. Reload mode
reads and compiles fresh source rather than trusting timestamp-based bytecode. The
default mode preserves the ordinary loading path. Neither is a persistent handler
callable cache, and neither is a security sandbox.

Loader-owned module registration and per-target reentrant coordination are shared
across application instances. Active leases and watcher ownership keep coordination
state alive while it is needed. Loader/invalidation locks are released before handler
invocation and are not held while awaiting its result; unrelated targets do not
share a global execution lock.

## Observation lifecycle

With reload enabled, application lifespan owns the observer. Startup establishes a
baseline and comparison before readiness. Scans fingerprint only configured paths
off the event loop, with at most one outstanding scan per observer. Revision changes
cause coordinated targeted invalidation on the application side, not in scan workers.

Missing/unreadable source is retained as a recoverable state. Fatal setup errors
prevent a misleading startup, and unexpected observer termination is logged.
Shutdown wakes interval waiting, drains outstanding work, and releases registrations.

Content fingerprints are observation state, not a retained source-history API.
Imported helpers, route configuration, dependency graphs and production workers
are outside the reload scope.

## Boundaries to preserve

Future performance or integration work must preserve the native handler contract,
per-request execution, source freshness, targeted ownership and cleanup. Proposed
cloud adapters or service mocks are not existing plugin APIs. Review and approve
their design before adding coupling to the engine.

See [performance validation](performance.md), [security](security.md), and
[the specification register](../specs/README.md) for requirements and evidence.
