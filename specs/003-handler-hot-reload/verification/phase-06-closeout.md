# Phase 6 Closeout Work — Not Yet Complete

**Date**: 2026-10-29 (Europe/Budapest)
**Authorization**: User requested finishing Phase 6 and marking it complete after work.
**Status**: Quality and core coverage now pass; primary-runtime full suite passes.
Final completion is withheld because the isolated Python 3.12 performance run failed.

## Reuse / preserve / change

Reused existing Ruff/mypy configuration, pytest suites, performance assertions,
current source and previously authorized isolated environment. Preserved all limits,
including <100ms startup, <5ms dispatch and amended <60MB baseline memory. No runtime
default switch, dependency change, installation, source caching or process-reload mode.

The user request to finish the phase authorized resolving the already reported
quality gate findings. Applied reviewed Ruff import/format diffs using file patches,
removed unused imports and redundant string prefixes, wrapped overlong strings
without changing their contents, shortened two test docstrings, removed one redundant
overlong comment, and corrected the test helper annotation headers: dict | None.
No routing, parsing, response, invocation or reload behavior was changed.

Formatting/import-only source edits: zerodock/__init__.py, config/models.py,
config/parser.py, engine/event.py, gateway/errors.py and gateway/response.py.
Corresponding test import/format cleanup affects existing diagnostics/config/event,
packaging/type/response/error/dispatch/wheel tests plus the static test hello fixture.
The real functions/hello.py and serverless-local.yaml were not changed. Parser's old
hash no longer matches by design because formatting changed; no unchanged-parser
hash claim is made for this closeout.

## Repository-wide quality — PASS

Existing project interpreter, -B, PYTHONDONTWRITEBYTECODE=1. Executed sequentially,
not during benchmark collection:

```powershell
& './.venv/Scripts/python.exe' -B -m ruff check --no-cache src/zerodock tests
& './.venv/Scripts/python.exe' -B -m ruff format --check --no-cache src/zerodock tests
& './.venv/Scripts/python.exe' -B -m mypy --cache-dir=specs/003-handler-hot-reload/verification/phase-06-closeout-mypy-cache src/zerodock tests
```

All exit 0. Ruff: all checks passed. Format: **34 files already formatted**.
Configured mypy: **no issues in 34 files**; existing notes about unchecked untyped
function bodies remain notes, not proof those bodies have strict typing.
Raw final output: phase-06-final-ruff-output.txt, phase-06-final-format-output.txt,
phase-06-final-mypy-output.txt. Earlier 28 lint findings/nine formatting files/one
type error remain recorded in historical reports, not deleted.

## Touched-core statement coverage — PASS

Used the existing Python standard-library trace module; no coverage tool installed.
Script: measure_core_coverage.py. Trace collection runs the four focused correctness
files with three debugger cases deselected because pdb replaces tracing; those three
cases are included in the uninstrumented full runs below. Performance tests are not
executed under tracing, so tracer overhead cannot be reported as dispatch acceptance.

Initial harness attempt was incomplete: stdlib trace's basename-keyed ignore cache
confused loader.py with an ignored dependency, and runfunc alone did not trace new
worker threads. Retained phase-06-core-coverage-output.txt and its reports. Corrected
only the harness to filter exact code filenames and register/restore tracing for
new threads. No production changes or ignored executable lines to inflate results.

Corrected run: **142 passed, 3 deselected in 4.67s**, exit 0.

| Module | Covered executable lines | Missing | Statement coverage |
| --- | --- | --- | --- |
| engine/loader.py | 125/126 | 1 | 99.2063% |
| engine/watcher.py | 166/174 | 8 | 95.4023% |

Both exceed 90%. This is statement/line coverage, not branch coverage or coverage.py
output. The denominator and missing-line listings use stdlib trace's report writer.
Raw evidence: phase-06-core-coverage-v2-output.txt; annotated .cover files under
phase-06-core-line-coverage-v2/. Trace hooks restored; script formatting checked.

## Full primary-runtime suite — PASS

```powershell
$env:PYTHONPATH = "$PWD\src"
& './.venv/Scripts/python.exe' -B -m pytest tests/unit tests/integration -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-06-final-regression-temp -q -s --tb=short
```

Windows / CPython 3.14.6: **194 passed in 8.48s**, exit 0; no skips/deselections.
Includes packaging, diagnostics, all debugger/compatibility cases and unchanged
performance assertions. Raw output: phase-06-final-regression-output.txt.

One 61-byte handler performance observations:
- Warm-import config/app/lifespan startup: maximum 13.5758ms off, 18.3976ms on.
- Direct ASGI total (conservative tiny-handler dispatch bound): maximum 1.4612ms off,
  2.9545ms on, below 5ms in all 40 measured samples. Invoker subtraction remains
  separately recorded and is not a universal overhead definition.
- Same-metadata save detection: 117.1806, 99.2796, 102.0029ms; atomic replacement:
  114.0914, 107.6861, 103.6622ms. Fresh responses followed all six saves.
- App-only RSS: maximum 48,709,632 bytes off / 49,598,464 on. This supplements, not
  replaces, the 18 actual-server samples under the amended memory protocol in
  memory-amendment-validation.md (maximum 54,988,800 bytes, <60MB).

This is one passing closeout run, not proof that prior outliers were fixed by
formatting or that every scheduler/workload will meet the same timings. Earlier
failures remain valid recorded observations. Startup measurements use the approved
warm-import/lifespan boundary; whole-process readiness remains separately reported
and must not be advertised as <100ms.

## Isolated compatibility-runtime full suite — FAILED

One subsequent sequential run, no concurrent agent-launched checks, same source and
matching dependency pins, no changes to the already-approved environment:

```powershell
& './specs/003-handler-hot-reload/verification/phase-06-python312-env/Scripts/python.exe' -B -m pytest tests/unit tests/integration -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-06-final-python312-temp -q --tb=short
```

CPython 3.12.0: **192 passed, 2 failed in 38.28s**, exit 1. No skips/deselections.
Raw output: phase-06-final-python312-output.txt. All functional cases passed.

Failed cases:
- Reload off direct ASGI total maximum **36.2505ms**, above 5ms.
- Reload on warm-import startup maximum **230.2233ms**, above 100ms; its recorded
  direct ASGI total maximum also exceeds 5ms at **23.7090ms**.

No trace/profiler ran concurrently. Other machine activity was not independently
measured, so neither scheduler contention nor an application cause is established.
The existing Python 3.12.0 build is old and diagnostic only; this does not justify
erasing the failed evidence, quietly excluding a tested runtime, changing defaults,
relaxing limits or rerunning until green. Per the budget stop rule, no additional
performance runs or speculative production fixes followed this failed gate.

## Task and platform status

T041 documentation, T042 benchmark implementation and T044 quality/core coverage
have their required completed work/evidence and can be checked. T046 live quickstart,
debugger, PID/port, shutdown and explicit runtime status recording is complete as a
validation action; recording a failed performance environment does not accept it.
T043 combined regression acceptance, T045 combined performance acceptance, T047
final acceptance and T048 final reconciliation remain open. Phase 6 is NOT complete.

Verified Windows functional/runtime evidence: 3.14.6 full pass; 3.12.0 functional pass
but performance failures. Python 3.10/3.11/3.13, Linux, macOS and GUI/IDE sessions are
untested. The pinned Starlette snapshot requires >=3.11, so it is not a demonstrated
Python 3.10 environment. No additional installation is authorized by this report.

No Git commands/config/data access, branch operations, commits or ignore-rule changes.
Specification ignore behavior is known from earlier audit, not freshly inspected;
the human must review local/untracked documentation before publication. No known
user-edited real handler/config file was overwritten. Existing live-server cleanup
evidence remains in live-acceptance.md and memory-amendment-validation.md; this turn
did not start new listening servers. No blanket claim that all release/platform
gates are passed is made.
