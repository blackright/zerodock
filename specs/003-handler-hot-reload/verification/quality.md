# Phase 6 Quality Evidence

**Date**: 2026-10-29 (Europe/Budapest)
**Current status (2026-10-29 closeout)**: PASS. Ruff check and format pass for src/zerodock and tests (34 files); configured mypy reports no issues in 34 files. Touched-core statement coverage measured with Python's built-in trace: loader 99.2063%, watcher 95.4023%. No tools installed. See phase-06-closeout.md and final raw quality/coverage files. Earlier findings below are historical, not current failures. Overall Phase 6 still has a Python 3.12 performance failure gate.

Commands used the existing venv Python, -B and PYTHONDONTWRITEBYTECODE=1:
- `-m ruff check --no-cache src/zerodock tests`: exit 1, **28 findings** (20 marked auto-fixable). See phase-06-ruff-output.txt.
- `-m ruff format --check --no-cache src/zerodock tests`: exit 1, **9 files would be reformatted, 25 already formatted**. See phase-06-format-output.txt.
- `-m mypy src/zerodock tests --cache-dir=specs/003-handler-hot-reload/verification/phase-06-mypy-cache`: exit 1, **1 error in 1 file, 34 files checked**. Error: tests/unit/test_event_builder.py:12 uses None as the default for a non-optional dict parameter. See phase-06-mypy-output.txt.

Reported lint/format/type findings are in files untouched by Phase 6. They are existing findings at the inspected snapshot, not silently repaired. The changed performance test had its pre-existing unused Path import and overlong comment removed; its code was formatted using the existing formatter before the repository-wide checks. Repository output reports no lint or type finding in that file.

Coverage, pytest-cov, and psutil are not installed (availability rechecked with importlib.util.find_spec). Nothing was installed. **The >90% touched-core coverage gate is unmeasured, not passed.**

Runtime verified by inventory: Windows 11 build 26300, Python 3.14.6. Other Python versions/platforms remain untested. No new dependencies, configuration changes, or production source changes were made. Quality checks overlapped regression execution; performance evidence discloses this contamination.
