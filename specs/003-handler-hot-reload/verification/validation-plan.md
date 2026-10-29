# Phase 1 Tool Inventory and Validation Plan

**Date**: 2026-10-29 (Europe/Budapest)
**Scope**: T002; approved measurements only, no installation or feature changes.

## Available Environment

- Interpreter: `C:\dev\python\zerodock\.venv\Scripts\python.exe`.
- Python 3.14.6, 64-bit AMD64; Windows 11 build 26300.
- CPU: Intel(R) Core(TM) 7 240H, 16 logical processors.
- Workspace filesystem: NTFS on drive C, confirmed through `System.IO.DriveInfo`.
- Existing packages: pytest 9.1.1, pytest-asyncio 1.4.0, HTTPX 0.28.1, FastAPI 0.146.0, Starlette 1.9.0, Uvicorn 0.54.0, Pydantic 2.14.1, PyYAML 6.0.3, Ruff 0.17.1, mypy 2.4.0.
- Missing from this environment: coverage, pytest-cov, psutil. Nothing is installed to replace them. Core coverage is a future gate, not a result measured here.
- Python and uv are present on PATH; Poetry and the `py` launcher were not returned by command discovery. Use the existing project interpreter, not a global substitute.
- The virtual-environment Python launcher and Windows CPU/filesystem queries were blocked in the sandbox. Approved escalation was requested rather than bypassing the restrictions. Tool queries succeeded outside the sandbox.
- Only the available Windows/Python 3.14 environment is tested here. Python 3.10-3.13, Linux, and macOS remain untested; package classifiers do not constitute runtime evidence.

No Ruff, mypy, coverage, full-suite, or platform-matrix execution was performed. Inventory availability is not evidence those checks pass.

## Workloads and Boundaries

1. Existing pytest run: six loader tests plus two unchanged performance tests. Use `-B`, `PYTHONDONTWRITEBYTECODE=1`, and `-p no:cacheprovider` to avoid new source bytecode/pytest-cache writes. Use a fresh phase-specific temporary base under `verification/`; pytest is allowed to write disposable fixture files there.
2. Existing app measurements: one configured route, one deduplicated handler (`functions/hello.py`, 529 bytes), config file 216 bytes. There is no watcher yet, so watched file count is zero. Do not claim detection or reload-on numbers.
3. Config/app and explicit lifespan entry measurements: use monotonic `perf_counter_ns`, report all samples and separately identify imports outside the timing boundary. No current lifespan entry creates a file observer.
4. Isolated direct ASGI measurements: use a minimal in-memory HTTP scope and existing hello handler, avoiding HTTPX client overhead. Time request dispatch and separately time the existing `invoke_handler()` call with a temporary in-process wrapper; restore it in `finally`. Report both raw times and the residual. This residual also excludes signature inspection and is not a complete proof of the <5ms constitutional dispatch budget. No on-disk source patching is involved.
5. Process readiness: briefly launch the current CLI on a dynamically selected loopback-only port. Measure process creation through first valid HTTP response, including interpreter/imports/server/lifespan. Check the child exits after owned cleanup. Do not launch a visible window or external network listener.
6. Current idle RSS: use Windows `GetProcessMemoryInfo` / `WorkingSetSize` for the live child after a short no-request settling interval. Record bytes and decimal MB; do not substitute peak working set or Python allocation memory. Shared Windows pages count as resident working set. This does not require psutil.

## Approved Test Command

From the repository root, using a fresh disposable base path:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit/test_loader.py tests/integration/test_performance_benchmarks.py -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-01-pytest-temp -v --durations=0
```

Do not repeat a pytest `--basetemp` path that now contains data: pytest may clear that directory. On repeats use a new verified in-workspace directory name instead of deleting prior artifacts.

## Approval-Dependent Follow-Up

- User has authorized the existing baseline tests and brief local-server run in Phase 1 only.
- No full-suite, lint, typing, installation, or coverage execution is included in this phase's approval.
- Budget failures are reported as observed baseline issues, not fixed or waived.
- Completing reports does not authorize Phase 2 or marking tasks done before user review.
- Branch verification is left to the human because Git commands/data access are forbidden for this phase.

## Official Measurement References

- [Python monotonic performance counter](https://docs.python.org/3/library/time.html#time.perf_counter_ns).
- [Python subprocess ownership and cleanup](https://docs.python.org/3/library/subprocess.html#subprocess.Popen).
- [Microsoft GetProcessMemoryInfo](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessmemoryinfo) and [current versus peak working set](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters).
- [HTTPX does not drive ASGI lifespan automatically](https://www.python-httpx.org/advanced/transports/#asgi-startup-and-shutdown).
