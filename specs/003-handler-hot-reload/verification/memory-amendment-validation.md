# Phase 6: Approved Memory Requirement and Fresh Validation

**Date**: 2026-10-29 (Europe/Budapest)
**Requirement**: Constitution 2.0.0 / memory-budget-amendment.md.
**Result**: Baseline memory gate PASS on the disclosed Windows/Python 3.14 workload.
**Not a result**: Final Phase 6 acceptance, a runtime optimization, or a retrospective
pass under the former 50MB rule. The <50MB optimization target remains unmet.

## Approval and alignment

The user explicitly approved changing the mandatory documented baseline memory gate
to <60 decimal MB while retaining <50MB as an optimization target, aligning related
documents/tests, and validating the new requirement. This is a policy amendment, not
permission to change startup/dispatch/detection limits or fix unrelated code.

Reviewed governing instructions and actual test/harness first. Reused current-RSS
sampling, actual CLI/PID discovery, disposable server ownership and graceful cleanup.
Production src, dependency versions, project runtime default and package release
version were not changed. The constitution's major bump from 1.0.0 to 2.0.0 records a
redefined governance requirement, not a software major release.

Aligned constitution, README, CONTRIBUTING, project-features, raw-input drafting
specification, active feature spec/plan/tasks/quickstart and test limit. Reviewed
templates, contract, research and data-model for stale hardcoded memory gates; none
needed a numeric replacement. Historical evidence files and raw failures remain
historical; current summary annotations point here rather than rewrite their results.

## Boundary tests and supplementary app-only memory

Added five boundary cases using the shared test constant: 49MB, 55MB and 59,999,999
bytes accepted; exactly 60,000,000 and 60,000,001 rejected. Ran against the former
50MB value first: **2 failed, 3 passed, 8 deselected in 0.50s**, exit 1. Raw evidence:
phase-06-memory-amendment-red-output.txt.

After aligning the limit to 60,000,000 bytes, ran:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = "$PWD\src"
& './.venv/Scripts/python.exe' -B -m pytest tests/integration/test_performance_benchmarks.py -k 'approved_baseline_memory_budget_boundary or fresh_process_current_idle_rss' -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-06-memory-amendment-green-temp -q -s --tb=short
```

**7 passed, 6 deselected in 4.29s**, exit 0. Raw evidence:
phase-06-memory-amendment-green-output.txt. The two app-only RSS cases are explicitly
supplementary, not actual listening-server acceptance. The other six performance
cases were not rerun and their limits remain unchanged. No full-suite pass is claimed.

## Fresh actual listening-server acceptance

Command (same environment, sequential, no concurrent agent tests/profiling):

```powershell
& './.venv/Scripts/python.exe' -B specs/003-handler-hot-reload/verification/phase-06-live/verify_memory_amendment.py
```

Used existing loopback-only CLI harness and Windows GetProcessMemoryInfo on actual
server PID WorkingSetSize. Three fresh processes per mode, 250ms idle after first
HTTP 200, three samples 100ms apart. All 18 samples are recorded in
[phase-06-memory-amendment-live-output.txt](phase-06-memory-amendment-live-output.txt).
All assertions and shutdown checks passed; exit 0.

Environment: Windows 11 build 26300, NTFS, CPython 3.14.6 64-bit / MSVC 1944, earlier
CPU inventory Intel Core 7 240H / 16 logical processors. Dependencies are recorded
in raw output: FastAPI 0.146.0, Uvicorn 0.54.0, Starlette 1.9.0, Pydantic 2.14.1,
pydantic-core 2.50.1, PyYAML 6.0.3, AnyIO 4.15.1, h11 0.16.0, Click 8.5.0 and
opentelemetry-api 1.45.1. Machine activity was not independently controlled.

One configured route exercised with GET; its existing config also permits POST,
but no POST workload was exercised. Handler 529 bytes, config 216 bytes, no extra
handler dependencies, no attached debugger/profiler. Reload off watches zero files;
on watches one at the existing 100ms interval. Harness stop thread is included in
server RSS. Readiness includes interpreter/import/CLI/server/socket/response and is
not the warm-import engine-startup benchmark.

Each trial's three RSS samples were equal; all values are decimal bytes:

| Trial | Mode | Actual PID | Port | Readiness ms | Three RSS samples, bytes |
| --- | --- | --- | --- | --- | --- |
| 1 | Off | 41468 | 50791 | 1141.7675 | 54550528, 54550528, 54550528 |
| 1 | On | 37652 | 50802 | 689.6312 | 54554624, 54554624, 54554624 |
| 2 | Off | 35192 | 54723 | 903.9706 | 54587392, 54587392, 54587392 |
| 2 | On | 12032 | 54732 | 890.5183 | 54853632, 54853632, 54853632 |
| 3 | Off | 18468 | 54741 | 1128.8488 | 54988800, 54988800, 54988800 |
| 3 | On | 24528 | 49394 | 889.3083 | 54689792, 54689792, 54689792 |

**Maximum 54,988,800 bytes (54.9888MB): all 18 samples <60,000,000.** Every sample
still exceeds the <50,000,000-byte optimization target. Neither samples nor the
former requirement were adjusted to conceal a failure. No claim covers arbitrary
handlers/imports, more routes or untested runtimes/platforms. Historical Python 3.12
measurements were not rerun or relabeled as new acceptance.

## Quality, cleanup and next gate

Changed test and new verification script: Ruff check PASS; Ruff format --check
reports two files already formatted; mypy --follow-imports=silent reports no issues
in two files (separate phase-06-memory-amendment-mypy-cache). Initial local formatting
findings were corrected without touching unrelated files. Later script formatting
only changed layout, not the executed measurement logic.

All six servers logged complete graceful shutdown, returned zero, closed listeners
and joined log collectors; their actual PIDs were absent at the final process check.
Real handler/config/parser hashes match earlier baseline. No test server remains.
No Git commands/data access, environment/package changes or installations this turn.

The current memory blocker is resolved only for this approved baseline. Existing
dispatch failures, repository-wide lint/format/type findings, unmeasured >90% core
coverage, remaining runtime/platform verification and final review remain open.
Startup/readiness boundaries were not relaxed or redefined. T041-T048 remain unchecked
pending remaining work and user review. Next work requires its applicable approval;
the amendment alone does not authorize unrelated fixes or installing coverage tools.
