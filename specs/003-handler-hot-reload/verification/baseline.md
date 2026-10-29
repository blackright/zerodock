# Phase 1 Baseline Measurements

**Date**: 2026-10-29 (Europe/Budapest)
**Status**: Approved Phase 1 measurements finished; user review pending. No feature implementation started.

## Initial Harness Attempt

The first approved pytest run collected eight unchanged tests. Five passed; three errored before their test bodies because the selected `--basetemp` directory's parent report directory did not yet exist (`FileNotFoundError`, WinError 3). This was a measurement setup error, not a handler regression. The two existing performance checks passed in that attempt. Total pytest time was 0.97s.

Creating these three approved reports established the missing parent directory. The same unmodified tests were rerun with a fresh phase-specific base. No source or test fix was required. Initial errored results are retained here rather than represented as a passing run.

## Existing Test Rerun

Command, from repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit/test_loader.py tests/integration/test_performance_benchmarks.py -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-01-pytest-temp-rerun -v --durations=0
```

**Result**: Exit code 0; 8 passed in 0.90s. No test body was edited.

| Test | Result |
| --- | --- |
| `test_load_and_invoke_sync_handler` | PASS |
| `test_load_handler_missing_file` | PASS |
| `test_load_handler_missing_function` | PASS |
| `test_load_handler_not_callable` | PASS |
| `test_invoke_async_handler` | PASS |
| `test_invoke_single_arg_handler` | PASS |
| `test_cold_boot_under_100ms` | PASS |
| `test_request_dispatch_latency` | PASS |

Pytest reported the complete request-dispatch test call at 0.05s, not its individual request durations. This includes setup/warm-up/multiple requests and is not the <30ms best-request assertion value. Separate raw request measurements follow.

## Environment and Timing Boundaries

Windows 11 build 26300, NTFS, Intel Core 7 240H (16 logical processors), project venv Python 3.14.6. Dependency inventory is in [validation-plan.md](validation-plan.md). Only this environment is measured. No dependency was installed or upgraded.

Workspace workload: one route, one deduplicated configured handler (`functions/hello.py`, 529 bytes), configuration 216 bytes. The current code has no watcher; observed/watched file count is zero. There is no reload-on or detection baseline to report.

Supplementary measurement ran as an inline, non-persisted Python process through the existing venv, with `PYTHONPATH` pointing to `src` and bytecode writes disabled. It used `perf_counter_ns()` and printed raw JSON. Application imports occurred before in-process startup timing. In-memory timing instrumentation was restored in `finally`; no source files were changed. Samples below preserve that output, rounded to four decimal places where floating-point representation is noisy.

## Startup Including Explicit Application Lifespan

Ten repeated measurements of `load_config()` + `create_app()` + entry into `app.router.lifespan_context(app)`, with imported modules already resident. Each lifespan exited before the next iteration.

Raw milliseconds:

```text
[1.3537, 1.0411, 0.9264, 0.9222, 0.8806, 0.9461, 0.9337, 0.9277, 0.9126, 0.9119]
```

Minimum 0.8806ms; median 0.92705ms; maximum 1.3537ms. These samples and the original config/app test are below 100ms for their stated boundary. This is not a fresh-interpreter cold-start measurement, and no current watcher is initialized by lifespan.

## HTTPX ASGI Round Trip

Explicit lifespan, one warm-up request, then three sequential GET requests to `/api/hello?name=Benchmark`. All responses were HTTP 200. This reproduces the existing best-of-three request method while also entering lifespan.

```text
milliseconds = [1.9281, 1.6584, 1.4192]
```

Best 1.4192ms; median 1.6584ms; maximum 1.9281ms. Best is below the existing 30ms assertion. This is in-process HTTPX, not a socket round trip or isolated dispatch measurement.

## Direct ASGI Dispatch Supplement

The existing app received a minimal in-memory GET scope through direct `await app(scope, receive, send)` calls. Three warm-ups were discarded, followed by 20 measurements. All responses were HTTP 200. A temporary in-memory wrapper separately timed the existing `invoke_handler()` call and was restored afterward. This includes its signature inspection and the small synchronous greeting handler.

Direct ASGI total milliseconds, including handler/invoker and wrapper cost:

```text
[0.7666, 0.8291, 0.7801, 0.7400, 0.7305, 0.7012, 0.7495, 0.7064, 0.7193, 0.7327,
 0.7478, 0.8938, 0.8549, 0.8617, 0.7595, 0.7811, 0.7402, 0.7576, 0.7029, 0.6491]
```

Invoker milliseconds for the same requests:

```text
[0.0230, 0.0250, 0.0237, 0.0219, 0.0210, 0.0212, 0.0205, 0.0200, 0.0232, 0.0205,
 0.0223, 0.0238, 0.0260, 0.0246, 0.0217, 0.0221, 0.0209, 0.0216, 0.0208, 0.0200]
```

Residual dispatch milliseconds, subtracting the measured invoker duration:

```text
[0.7436, 0.8041, 0.7564, 0.7181, 0.7095, 0.6800, 0.7290, 0.6864, 0.6961, 0.7122,
 0.7255, 0.8700, 0.8289, 0.8371, 0.7378, 0.7590, 0.7193, 0.7360, 0.6821, 0.6291]
```

| Boundary | Minimum ms | Median ms | Maximum ms |
| --- | ---: | ---: | ---: |
| Direct ASGI total | 0.6491 | 0.74865 | 0.8938 |
| Invoker | 0.0200 | 0.02180 | 0.0260 |
| Residual | 0.6291 | 0.72725 | 0.8700 |

Both the total and residual are below 5ms in this small warmed workload. The residual excludes signature inspection as well as the handler and is therefore not the universal definition of gateway overhead. The total provides a conservative measured comparison for this handler only; no assertion is made for arbitrary imports, handlers, concurrency, or platforms.

## Fresh-Process Readiness and Current Idle Memory

Three CLI trials bound only to `127.0.0.1`, with a free dynamically selected port. A short child wrapper printed its actual Python PID, then called the unchanged `zerodock.cli.main()` with `dev --config <absolute path> --host 127.0.0.1 --port <selected> --log-level error`. Using the actual PID matters because the venv executable launches a separate Python process on this machine.

Readiness time starts immediately before subprocess creation and ends after the first valid HTTP 200 greeting response. Polling used a 10ms retry interval, 200ms request timeout, and 10s overall deadline; localhost proxying was disabled. Measurements include launcher/interpreter/imports/configuration/server startup/lifespan/socket/request overhead. OS/file caches were not deliberately flushed; this is fresh-process readiness, not a guaranteed cold-disk measurement.

After the first response, each child was left without requests for 250ms, then current working set was sampled three times at 100ms intervals via Windows `GetProcessMemoryInfo`. This is current resident working set, not peak working set, private bytes, or Python-only allocation size.

| Trial | Launcher PID | Actual server PID | Port | Process-to-response ms | Three current RSS samples, bytes |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 39192 | 22364 | 65081 | 760.6834 | 53948416, 53948416, 53948416 |
| 2 | 38280 | 5032 | 57888 | 775.8206 | 53747712, 53747712, 53747712 |
| 3 | 10624 | 16884 | 63764 | 716.8270 | 53755904, 53755904, 53755904 |

Readiness minimum 716.8270ms, median 760.6834ms, maximum 775.8206ms. Current idle RSS is 53.747712-53.948416 decimal MB, also above 50MiB (52,428,800 bytes).

Each owned server was stopped after measurement using Windows process termination through `SIGTERM`; child wrappers were waited/reaped. Exit code 15 is expected from this measurement cleanup, not an app crash. This was NOT a graceful-lifespan shutdown test. All three stderr captures were empty, all three listeners were closed, and a later process check found none of the six recorded PIDs alive. No test server remains running.

## Findings and Acceptance Boundaries

| Gate / observation | Result |
| --- | --- |
| Existing loader/performance tests | 8/8 PASS on clean rerun |
| Existing config/app <100ms check | PASS |
| Warm imports + config/app/lifespan | All ten samples <100ms |
| Existing best-of-three ASGI <30ms boundary | PASS; supplementary best 1.4192ms |
| Direct warmed tiny-handler dispatch | All samples <5ms for stated boundary |
| Current idle RSS <50MB | FAIL in all three fresh-server trials before feature changes |
| Full fresh-process readiness <100ms | Not met; 716.8270-775.8206ms. Distinct from the existing config/app benchmark |
| True cold engine/import startup interpretation | Not established by the warm in-process benchmark; full readiness must not be described as <100ms |
| Reload-on, <=500ms detection, watcher cleanup | Not applicable yet; feature is not implemented |
| Other Python versions/platforms, full suite, lint/type/coverage | Not executed in Phase 1 |

The pre-existing RSS budget failure is a real finding requiring review. Do not optimize unrelated code, change package versions, weaken thresholds, or mark the complete feature constitution-compliant without further user direction. Readiness numbers also expose a gap between the current benchmark label and whole-process startup; no startup metric is silently substituted for another.

## Unchanged Files and Review Status

All nine source/test/config/handler hashes in [implementation-audit.md](implementation-audit.md) matched after measurements. Three requested reports were authored. Disposable pytest fixture files were left under the verified workspace report directory; no recursive deletion or dependency installation was performed. No Git commands or Git configuration/data access occurred.

## Review Gate

Tasks T001-T003 remain unchecked until user review. Phase 2 has not started. No Git commands, dependency installation, source edits, or test edits are authorized by these measurements.

Current-branch verification was intentionally not performed under the no-Git rule; the human can confirm it during review. Phase 1's reports and measurements are ready for review, not a declaration that all runtime budgets passed.
