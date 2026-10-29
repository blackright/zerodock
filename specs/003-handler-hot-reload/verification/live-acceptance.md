# Phase 6 Live-Server Evidence

**Date**: 2026-10-29 (Europe/Budapest)
**Status**: Functional live checks passed after harness corrections. Actual listening-server RSS exceeds 50MB. Dispatch and other acceptance gates remain open; no waiver or final acceptance.

## Authorization and method

The user explicitly approved collecting remaining live-server evidence while retaining unresolved dispatch-budget findings. Reviewed phase rules, earlier live/baseline methodology, actual CLI and installed Uvicorn shutdown handling. Reused existing native CLI, parser, gateway, invocation contracts and watcher; no production source or acceptance tests were changed in this turn.

Disposable harness and fixtures live in phase-06-live/. It launches the actual zerodock.cli.main with dev, --host 127.0.0.1, an available port, --config and --log-level info; --reload only when requested. A child wrapper prints its actual Python PID because the venv launcher has a separate PID. It adds a harness-only stdin stop thread which raises SIGINT, allowing Uvicorn's real signal handler and lifespan shutdown to run; the wrapper catches the final KeyboardInterrupt after Uvicorn returns. No production endpoint or mocked server implementation is used. No visible windows or external listeners.

Readiness begins before Popen and ends after the first valid HTTP response, including interpreter/import/CLI/server/socket overhead. Retry interval 10ms, per-readiness-request timeout 200ms, deadline 10s; proxy use disabled. The memory method samples actual server WorkingSetSize using Windows GetProcessMemoryInfo after 250ms idle, three times with 100ms intervals. This is current RSS, not peak RSS or pytest memory. Source bytecode writes were disabled; project PYTHONPATH points to src.

Commands (sequential, no concurrent agent checks):

```powershell
& './.venv/Scripts/python.exe' -B specs/003-handler-hot-reload/verification/phase-06-live/verify_live.py
& './.venv/Scripts/python.exe' -B specs/003-handler-hot-reload/verification/phase-06-live/verify_debugger.py
```

Raw supervisor outputs are retained as phase-06-live-output.txt, phase-06-live-rerun-output.txt, phase-06-live-debugger-output.txt, phase-06-live-debugger-rerun-output.txt and phase-06-live-debugger-final-output.txt. Child output is retained in phase-06-live/server-<launcher PID>.log. Runtime save simulations touched only these disposable handlers; original source was restored in finally.

## Functional journeys

Successful main run: **actual PID 40764, port 53347**. Three routes use two deduplicated files: sync/async entrypoints share handler.py (200 bytes); healthy.py is 49 bytes. Total configured handler source 249 bytes; internal interval 100ms. Handler-reported PID matched the wrapper PID throughout.

- Both sync/async routes returned A, then B after a normal save, then C after atomic replacement; every changed request followed actual invalidation-log acknowledgement. Same process and port served all versions.
- Syntax error returned HTTP 500 with existing HandlerLoadError envelope; healthy route stayed HTTP 200. Valid source recovered both affected entrypoints to A without restart.
- Deletion after startup returned HTTP 500 while healthy route still worked. Recreation recovered A without restart.
- Controlled breakpoint invocation returned HTTP 200 and continued. Full source-frame/event transcript was separately verified in the final debugger-only run below.
- Normal shutdown logged Application shutdown complete, returned CLI control, exited zero, closed the listener and joined the supervisor's log collector. No forced termination.
- A deliberate new start reused **port 53347** successfully with **new actual PID 22340** and response A. It too exited zero with complete shutdown logs. A new PID is expected for a deliberate restart, not a hot save.

The disposable journey's process-to-response readiness was 914.8053ms, not a warm engine-startup sample or a timing guarantee.

## Listening-server RSS and readiness

These two trials used the original, unchanged repository configuration (one route) and functions/hello.py (529 bytes), not the disposable debugger fixture. Neither memory process imported pdb through the hook. One trial per mode, not the three-per-mode repetition needed for a stronger comparative distribution.

| Mode | Launcher / actual PID | Port | Process-to-response ms | Current RSS bytes (3 samples) |
| --- | --- | --- | --- | --- |
| Reload off | 30892 / 5196 | 63562 | 1353.1611 | 54652928, 54652928, 54652928 |
| Reload on | 8176 / 43612 | 61049 | 1342.1706 | 54517760, 54517760, 54517760 |

**RSS FAIL**: off 54.652928 decimal MB; on 54.517760MB, both above 50MB (and 50MiB). There are zero watched files off and one on. Both servers shut down gracefully, exited zero and closed their listeners.

Earlier pre-feature live-server RSS was 53.747712-53.948416MB and process readiness 716.8270-775.8206ms. This run has info-level logs and a harness stop thread unlike the earlier error-level baseline; samples were collected at different times with machine activity uncontrolled. Do not interpret the tiny on/off difference as a reload memory saving, infer causal overhead, or silently replace the actual-server failure with the earlier app-only <50MB result. Whole-process readiness is distinct from warm-import config/app/lifespan startup; no <100ms whole-process claim is made.

## Controlled native debugger and harness corrections

Initial main attempt completed refresh/recovery journeys but exited 1 on shutdown: the custom Pdb hook installed a SIGINT handler, and its finite command stream was exhausted when the harness sent stop, producing BdbQuit. Listener closed; no server survived. Fixed only the disposable hook using documented Pdb(nosigint=True); successful main rerun then had graceful shutdown.

Two subsequent debugger-only supervisor assertions failed before the final successful check:
1. Printing from the custom hook after set_trace caused the first stop in an encoding helper rather than handler event inspection. Corrected the hook to return immediately to the target frame and retain transcript until CLI exit.
2. The diagnostic incorrectly expected legacy httpMethod; the actual event correctly uses version 2.0 with routeKey and requestContext.http. Corrected only the assertion to the actual GET /sync event shape. No application event changes.

Final debugger-only run: **actual PID 34824, launcher 29984, port 53428**, exit 0. The captured transcript shows handler.py:sync_handler, a native (Pdb) prompt, event routeKey GET /sync, source stack and continuation to response A with the same PID. This verifies controlled native pdb under a real HTTP request, not an interactive GUI/IDE session or stock terminal Ctrl+C-after-pdb behavior. The harness explicitly owns debugger input, stop input and SIGINT policy.

## Cleanup and remaining gates

All eight actual server PIDs across attempts (10144, 40764, 22340, 5196, 43612, 40120, 32320, 34824) were absent on the final process check. Every supervisor recorded a closed listener; seven shutdowns completed gracefully, while the initial harness failure is retained. One retired launcher PID had been reused by an unrelated chrome process; it was identified and left untouched, not terminated by PID alone. No server remains running. Original disposable source A was restored and no breakpoint remains.

Unchanged baseline SHA-256 checks:
- config/parser.py: 35C3AEB2C3A8D5066EB081ACA4A3A4ED84AF596F09BC52D9DD389626AC2D700E
- functions/hello.py: D074824B0502F5C84F5CC8B043837BFB9A2D496FC531729FD0D3AF54CE1FD95E
- serverless-local.yaml: AA911D6FD685700AB4B2BA33546E1CB22880E9C5681F108B5B772742B93D43F7

Current feature acceptance is still blocked by dispatch outliers, live RSS failure, repository-wide quality findings, unmeasured >90% core coverage and untested Python/platform matrix. No dependencies were installed, no unrelated fixes made, no Git commands/data access, no ignore changes. Phase 6 boxes remain unchecked. More runtime optimization or tool installation requires separate approval.

Official references: [Python Pdb SIGINT policy](https://docs.python.org/3.14/library/pdb.html#pdb.Pdb), [subprocess ownership](https://docs.python.org/3.14/library/subprocess.html#subprocess.Popen), and [Windows current process memory](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessmemoryinfo). Installed Uvicorn server.py was inspected for SIGINT handling and shutdown; no external documentation availability is treated as proof of observed behavior.
