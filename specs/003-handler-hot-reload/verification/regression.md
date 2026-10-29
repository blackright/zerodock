# Phase 6 Regression Evidence

**Date**: 2026-10-29 (Europe/Budapest)
**Current status (2026-10-29 closeout)**: Primary Windows/Python 3.14.6 full suite PASS, 194 passed in 8.48s. Subsequent isolated Python 3.12.0 full suite: 192 passed, 2 performance failures in 38.28s; all functional cases pass. Core coverage run: 142 passed/3 debugger cases deselected; these debugger cases pass in the uninstrumented runs. See phase-06-closeout.md and phase-06-final-regression-output.txt / phase-06-final-python312-output.txt. No combined-runtime acceptance or final phase completion; earlier runs below remain historical.

## Approved Sequential Full-Suite Rerun

The user approved the remaining live-server checks and a sequential full-suite run. The suite ran first; no concurrent quality checks, benchmark processes, or live servers were launched by the agent. No source or test changes were made for this rerun. Other machine activity was not controlled.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = "$PWD\src"
& './.venv/Scripts/python.exe' -B -m pytest tests/unit tests/integration -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-06-full-sequential-temp -q --tb=short
```

**Result**: exit 1; **183 passed, 1 failed in 21.48s**. No deselections or skips. Both isolated-app memory cases and the original startup/request benchmarks passed. Raw failure and samples: [phase-06-full-sequential-output.txt](phase-06-full-sequential-output.txt).

The only failed case was `test_lifespan_startup_and_isolated_dispatch[True]`: one of 20 measured direct ASGI totals was **5.3948ms**, exceeding the unchanged 5ms conservative total limit. The invoker-subtracted residual for that sample was **5.2357ms**. Reload-on startup samples were 7.2668-34.2297ms, below 100ms.

This sequential failure shows timing variability remains even without agent-launched concurrent quality checks. It does not identify a cause, prove a source-code regression, or invalidate the retained earlier performance-only pass. No rerun-until-green, threshold change, or production optimization was performed. As required by the budget stop rule, live-server execution was not started after discovering the failure. Investigation requires user direction.

## Authorized execution

Existing tests, benchmarks, CLI behavior, shared fixtures, and earlier evidence were inspected before changes. The existing two benchmark definitions were preserved. Added tests separately cover warm-import config/app/lifespan startup, direct ASGI dispatch, background detection for same-metadata and atomic saves, changed-file responses, and isolated Windows current RSS. No production code changed.

Command (project root; existing venv, bytecode disabled, PYTHONPATH=src):

```powershell
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit tests/integration -k 'not fresh_process_current_idle_rss' -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-06-regression-temp -q -s --tb=short
```

**Result**: exit 1; **180 passed, 2 failed, 2 deselected in 36.41s**. No skips were reported. Packaging, existing wheel-unpack/CLI smoke, diagnostics, loader, watcher, CLI, HTTP, and existing benchmarks ran in this suite. The wheel test unpacks an existing wheel into a disposable directory; it does not prove the current source has been built into a fresh release.

Failures:
- `test_lifespan_startup_and_isolated_dispatch[False]`: maximum direct ASGI total 19.0242ms exceeds conservative 5ms assertion.
- `test_lifespan_startup_and_isolated_dispatch[True]`: maximum warm-import lifespan startup 115.8036ms exceeds 100ms. Its recorded dispatch samples also exceed 5ms.
- Both isolated idle-RSS cases were intentionally deselected for later separate measurement; they have not run.

Raw output: [phase-06-regression-output.txt](phase-06-regression-output.txt). Expected negative-test tracebacks and timeouts in this file are not additional failed tests.

## Measurement caveat and stop boundary

Repository quality checks were launched concurrently with this suite. They competed for machine resources. Timing failures are retained, but this is not a controlled isolated benchmark or proof of a production regression. A sequential, otherwise idle rerun needs user approval after this budget stop. No limits were relaxed, no unrelated fixes made, and no performance optimization attempted.

Earlier red/green and cleanup evidence remains in foundations.md, us1.md, us2.md, and us3.md. No new full-suite registry/thread cleanup snapshot or supported-runtime matrix is claimed here. Repository config/parser and original handler hashes still match the earlier baseline.
