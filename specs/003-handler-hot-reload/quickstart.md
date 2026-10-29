# Quickstart Validation: Handler Hot Reload

**Status**: Reload is implemented and Phases 1-5 are approved. Phase 6 validation is authorized and in progress; final acceptance is not granted. See verification reports for actual results, budget failures, and untested environments. Commands below are instructions, not evidence they all passed.

## Prerequisites

- Existing Python 3.10+ project environment with project/dev dependencies already available.
- A disposable directory containing `serverless-local.yaml` and a valid configured handler. Do not edit repository fixtures or real handlers during verification.
- Available local port; no cloud account, network service, container, or optional watcher package.
- See [contract](contracts/reload-contract.md) for interfaces and [runtime model](data-model.md) for state/ownership semantics.

If dependencies or measurement tools are unavailable, request approval before installation. Do not assume coverage tooling is already installed.

## 1. Establish Baseline

From repository root, when authorized:

```powershell
python -m pytest tests/unit/test_loader.py
python -m pytest tests/integration/test_performance_benchmarks.py
```

Record unchanged baseline timings before implementing changes. Existing cold-boot test measures config parsing plus app creation; request benchmark measures best-of-three ASGI round trip. Neither proves process readiness, watcher startup, isolated dispatch overhead, or idle RSS.

## 2. Run a Disposable Gateway

In the disposable directory, prepare a valid config pointing to its own handler and route `/hello`. Run:

```powershell
zerodock dev --reload --config serverless-local.yaml --port 8080
```

In a second terminal:

```powershell
Invoke-WebRequest http://127.0.0.1:8080/hello
```

Expected: original handler result. Record the actual process ID and bound port using existing local process tools. Edit the disposable handler to return a distinguishable result; after confirmed invalidation request again. Expected: updated result, same process ID and port. Repeat with an async handler and atomic replacement.

## 3. Failure and Compatibility Scenarios

- Save a syntax/import error: affected route returns the existing error format, not old success; another route still succeeds.
- Correct source and wait for detection: affected route recovers without restarting.
- Delete a handler after startup, then recreate it: errors while absent, recovery after recreation.
- Preserve length/timestamp while changing contents with an existing bytecode file: next post-invalidation request uses fresh contents. Automate this case in temporary-file regression tests rather than relying on manual editor timestamps.
- Start without `--reload`: no observer exists and module top-level execution remains per request.
- Start with a missing configured file: existing startup validation still rejects configuration.
- Change an imported helper only: automatic helper refresh is not promised; restart may be required.
- Shut down normally and through test cancellation: no application-owned scan/observer tasks or file handles remain. Repeat app startup/shutdown and test two apps sharing a handler.

## 4. Automated Verification After Implementation

The test paths below exist. Run from the repository root with the project virtual environment:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit/test_loader.py tests/unit/test_watcher.py tests/unit/test_cli.py -p no:cacheprovider
& '.\.venv\Scripts\python.exe' -B -m pytest tests/integration/test_hot_reload.py -p no:cacheprovider
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit tests/integration -p no:cacheprovider
& '.\.venv\Scripts\python.exe' -B -m ruff check --no-cache src tests
& '.\.venv\Scripts\python.exe' -B -m mypy src/zerodock
```

Use existing equivalent test files if implementation extends them instead. HTTPX ASGI tests must explicitly enter application lifespan; transport creation alone is insufficient. Correctness tests should use controlled scan events, not arbitrary sleeps. Maintain >90% touched core coverage target using available approved coverage tooling.

## 5. Performance Evidence

Measure reload off/on with tiny no-op handlers and disclose OS, Python/dependency versions, CPU, filesystem, watched file count/bytes, interval, sample count, raw durations, and measurement boundary.

| Measurement | Acceptance / reporting |
| --- | --- |
| Existing config + app benchmark | <100ms; retain original definition |
| Lifespan-inclusive engine startup | <100ms constitutional gate; separately report interpreter/import/process readiness |
| Isolated dispatch overhead | <5ms, with user handler work excluded and instrumentation boundary explained |
| Existing ASGI round trip | Best of three <30ms; retain raw samples |
| Completed-save to invalidation | <=500ms under stated normal local conditions; sample both atomic replacement and same-metadata edits |
| Changed-file next request | Fresh response; report time without disguising source compilation cost |
| Baseline idle memory | Actual listening-server current RSS <60,000,000 bytes; <50,000,000 remains an optimization target. Use the approved workload and every sample from three processes per reload mode; app-only/peak/private memory is not a substitute |

Recorded historical baseline findings under the former 50MB rule: current Windows idle RSS was 53.75-53.95MB and fresh-process readiness was 716.83-775.82ms. These findings remain unchanged. The user-approved [memory amendment](memory-budget-amendment.md) now requires <60MB current RSS for one listening gateway, one GET route and one trivial handler/config each <=1KiB, with no extra handler dependencies or attached debugger/profiler. After the first valid response idle 250ms, then sample three times 100ms apart in each of three fresh processes per reload mode; every sample must be below 60,000,000 bytes. Report OS/filesystem, runtime/build, dependencies, raw samples, actual PID, route/watched-file counts and cleanup; untested environments remain untested. Warm-import startup and whole-process readiness are not interchangeable. No other limit is changed. If current results violate a gate, report it and seek approval rather than silently adjust thresholds or optimize unrelated code. Hung/remote filesystem shutdown timing is not guaranteed.
