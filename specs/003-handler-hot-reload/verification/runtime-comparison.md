# Phase 6 Isolated Python Runtime Comparison

**Date**: 2026-10-29 (Europe/Budapest)
**Status**: Approved comparison complete. No runtime switch, budget change, or production modification. Phase 6 remains incomplete.

## Approval and isolation

The user approved checking available runtimes, then explicitly approved creating an isolated Python 3.12 environment, installing matching dependencies there, and executing the comparison. Existing interpreter inventory used offline/no-download uv listing; Python 3.12.0 was already installed. No interpreter was downloaded or upgraded. This old patch release is diagnostic only, not a production recommendation.

Reviewed actual phase rules, loader/gateway/CLI and existing memory harness. Reused the same native CLI/loopback/sampling/shutdown procedure, current project source and unchanged 529-byte real handler. Preserved .venv, global Python packages, project dependencies, all thresholds and source behavior. No Git commands, Git data/config access, branches, commits or ignore-rule changes.

Created only specs/003-handler-hot-reload/verification/phase-06-python312-env using the existing interpreter's venv --without-pip --copies after checking the absolute path stayed inside the workspace and did not exist. Used uv pip install --python <isolated interpreter>, --only-binary :all:, no Python downloads and a workspace-local cache. Installed the 25 exact runtime/test pins listed in python312-comparison-requirements.txt; no optional standard extras, coverage, Ruff or mypy added. uv downloaded approved wheel artifacts as needed, with no source builds.

The existing local dist/zerodock-0.1.1-py3-none-any.whl was installed with --no-deps and --offline into only the isolated environment to match package version metadata. Measurements and tests explicitly use PYTHONPATH pointing to current src, so old wheel implementation is not mistaken for hot-reload source. Both supervisors asserted zerodock.__file__ was current src/zerodock/__init__.py. The prebuilt wheel smoke test is still not evidence a new release wheel contains these changes.

All 25 pins were verified in the isolated environment and reverified unchanged in the original .venv afterward. Base Python 3.12 still has no FastAPI package. No global installations or project dependency/lockfile edits. The environment and cache are retained for review, not recursively deleted.

## Method and raw evidence

Windows 11 build 26300, NTFS, earlier CPU inventory Intel Core 7 240H / 16 logical processors. Existing project venv: uv-managed CPython 3.14.6, MSVC 1944; comparison: python.org CPython 3.12.0, MSVC 1935. Both are 64-bit AMD64. Different builds/patches mean results are not solely attributable to Python language version.

For each interpreter: three trials, reload off followed by on within each trial; **12 listening servers total**, run sequentially with no concurrent agent checks. Python 3.12's six trials preceded Python 3.14's six (not randomized). One configured route, 529-byte handler; zero watched files off / one on, existing 100ms interval. Machine activity and OS cache state were not independently controlled.

Existing phase-06-live Child and current_rss helpers were invoked through inline Python via stdin. Each launched actual zerodock.cli.main through the existing PID-printing/stop-input wrapper. After first valid HTTP response: 250ms idle, then three current WorkingSetSize samples at 100ms intervals. Readiness includes interpreter/import/config/CLI/server/socket/request, not warm engine startup. Every trial verified graceful shutdown logs, zero exit, listener closure and collector completion.

Raw outputs:
- [phase-06-runtime-312-memory-output.txt](phase-06-runtime-312-memory-output.txt)
- [phase-06-runtime-314-memory-output.txt](phase-06-runtime-314-memory-output.txt)
- phase-06-live/server-<launcher PID>.log for each child.

## Live-server results

Each RSS value below was identical across that trial's three samples; raw files retain all samples in bytes. MB means decimal 1,000,000 bytes; the <50MB limit was not reinterpreted as MiB.

| Python | Trial | Mode | Actual / launcher PID | Readiness ms | Current RSS MB |
| --- | --- | --- | --- | --- | --- |
| 3.12.0 | 1 | Off | 30532 / 26308 | 1606.1327 | 49.979392 |
| 3.12.0 | 1 | On | 2368 / 21976 | 1134.3502 | 50.368512 |
| 3.12.0 | 2 | Off | 19068 / 43356 | 1375.0058 | 50.376704 |
| 3.12.0 | 2 | On | 33808 / 15112 | 1379.9307 | 50.786304 |
| 3.12.0 | 3 | Off | 32656 / 11360 | 1353.6260 | 49.823744 |
| 3.12.0 | 3 | On | 41860 / 44560 | 881.2084 | 50.208768 |
| 3.14.6 | 1 | Off | 41004 / 18876 | 899.8317 | 54.468608 |
| 3.14.6 | 1 | On | 11988 / 35912 | 908.8118 | 54.624256 |
| 3.14.6 | 2 | Off | 42828 / 41072 | 912.5733 | 54.439936 |
| 3.14.6 | 2 | On | 3524 / 28252 | 693.6220 | 54.571008 |
| 3.14.6 | 3 | Off | 40380 / 45112 | 894.3882 | 54.874112 |
| 3.14.6 | 3 | On | 11124 / 43932 | 1366.8555 | 54.661120 |

Memory verdict: Python 3.12 off passes 2/3 trials but fails 1/3; on fails all three. Python 3.14 fails all six. The lower 3.12 readings do not provide a robust <50MB solution, justify switching defaults, or erase 3.14 findings. Whole-process readiness is above 100ms in every trial and remains distinct from the warm config/app/lifespan boundary.

## Python 3.12 compatibility and unchanged performance tests

After all listening servers exited, ran once sequentially:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = "$PWD\src"
& './specs/003-handler-hot-reload/verification/phase-06-python312-env/Scripts/python.exe' -B -m pytest tests/unit tests/integration -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-06-python312-pytest-temp -q -s --tb=short
```

**Result**: exit 1; **188 passed, 1 failed in 11.65s**, no skips/deselections. Raw output: [phase-06-python312-pytest-output.txt](phase-06-python312-pytest-output.txt). All 181 non-performance cases passed, plus seven of eight performance cases. Native controlled debugger, failure/recovery, concurrency and lifecycle tests are included in those functional results.

Failure: reload-on direct ASGI total **5.3799ms**, above unchanged 5ms conservative gate; corresponding invoker-subtracted residual 5.3420ms. Other 19 measured totals in that case were below 5ms. No threshold relaxation or retry-until-green.

Other observations for the one 61-byte temporary benchmark handler:
- Warm-import startup: off 1.4385-18.9466ms; on 2.9220-14.5619ms (all <100ms).
- Reload-off direct ASGI total: 0.9661-3.3419ms (all <5ms).
- Same-metadata detection: 115.6005, 115.8105, 126.2486ms; atomic: 112.0589, 97.1647, 97.0773ms (all <=500ms with fresh responses).
- Isolated app-only idle RSS: off 44,400,640 bytes; on 45,371,392 bytes (three equal samples each). As before, app-only memory does not replace listening-server RSS failure.

The earlier 3.14 full suite (187 passed, two dispatch failures) is retained in path-resolution-optimization.md; it was not rerun during this comparison. Passing functional cases on 3.12 extend runtime evidence but do not prove a complete Python/platform matrix.

## Cleanup, limitations and decision

All 12 actual server PIDs were absent at final process check. All children had zero exits, graceful shutdown-complete logs, closed listeners and joined collectors. Real handler/config/parser SHA-256 hashes still match the earlier baseline. No application server remains running. No production changes were made.

Additional known compatibility issue remains separate: installed Starlette 1.9.0 declares Python >=3.11 although the project declares >=3.10. No packages were downgraded to hide this; Python 3.10/3.11/3.13 and non-Windows runtimes remain untested. Python 3.12.0 is old and not recommended as a deployment baseline based on this diagnostic.

Conclusion: switching to the available Python 3.12 does **not** close memory or dispatch gates. No further runtime switching, dependency substitution, server rewrite or budget amendment is authorized or proposed as an established fix. Phase 6 remains incomplete: memory, dispatch, repository-wide quality, coverage and final review need explicit resolution. T041-T048 remain unchecked. Any broader architectural remediation needs its own approved scope.

Official preparation references: [Python 3.12 virtual environments](https://docs.python.org/3.12/library/venv.html), [targeting uv environments](https://docs.astral.sh/uv/pip/environments/) and [package installation](https://docs.astral.sh/uv/pip/packages/).
