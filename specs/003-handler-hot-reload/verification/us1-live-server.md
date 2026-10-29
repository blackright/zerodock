# Phase 3 Live-Server Continuity Check

**Date**: 2026-10-29 (Europe/Budapest)
**Task**: T020; explicitly authorized disposable, loopback-only validation.
**Result**: PASS; awaiting user review. Server and measurement process are stopped.

## Setup and Boundary

Used the existing project venv Python 3.14.6 with `PYTHONPATH` set to project `src`, bytecode writes disabled, and no package changes. The actual CLI was invoked with `dev --reload --config <absolute disposable config> --host 127.0.0.1 --port 58805 --log-level info`. A short PID-printing wrapper called the unchanged CLI entrypoint; no test-specific endpoint was added to production code.

Disposable files, added via explicit file patches:

- `phase-03-live/handler.py`: synchronous and asynchronous entrypoints, both initially A.
- `phase-03-live/serverless-local.yaml`: two GET routes sharing that one source file.

The handler source was 339 bytes before and after the A-to-B patch. The actual Python PID is distinguished from the Windows venv-launcher PID. The local supervisor disabled proxy use, waited for valid HTTP responses, and collected actual Uvicorn/reload logs. No application handler in `functions/` or test fixture outside this directory was modified.

## Observed Results

```json
{
  "port": 58805,
  "launcher_pid": 38772,
  "actual_server_pid": 27368,
  "configured_files": 1,
  "source_bytes_before": 339,
  "source_bytes_after": 339,
  "before": [
    {"version": "A", "pid": 27368, "kind": "sync"},
    {"version": "A", "pid": 27368, "kind": "async"}
  ],
  "after": [
    {"version": "B", "pid": 27368, "kind": "sync"},
    {"version": "B", "pid": 27368, "kind": "async"}
  ],
  "same_pid": true,
  "same_port": true,
  "invalidation_acknowledged": true,
  "exit_code_after_owned_termination": 15,
  "listener_closed": true
}
```

Both before and after responses were HTTP 200. The A-to-B edit changed only version literals in the disposable source. The supervisor waited for the actual invalidation log before requesting the B responses; it did not merely poll until a changed response happened to appear.

Actual captured logs:

```text
INFO:     Started server process [27368]
INFO:     Waiting for application startup.
INFO:     Reload enabled for 1 handler file(s)
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:58805 (Press CTRL+C to quit)
INFO:     Invalidated handler zerodock.handlers.mod_5c7f65d93f3e
```

There was only one observed handler despite two routes. No replacement server was started between A and B; both handler-reported PIDs matched the original actual server PID, and the same bound port served all four requests.

## Cleanup and Limitations

After success, the supervisor terminated its owned actual Python server using Windows `SIGTERM`, waited/reaped the launcher, joined its log collector, closed pipe handles, and confirmed the listener was closed. Exit code 15 reflects this intentional termination. This is not proof of graceful lifespan shutdown; basic normal lifecycle cleanup is covered separately by the focused tests, with harder cancellation cases deferred to their planned phase.

This check proves real HTTP freshness and process/port continuity for the two disclosed entrypoints. It does not measure cold boot, RSS, latency percentiles, atomic replacement, error recovery, dependency reload, or production multi-worker behavior. Detection timing is recorded separately in [us1.md](us1.md), not inferred from the supervisor's file polling.

The disposable source remains at version B for user review. No live test server should remain running.
