# Phase 6 Approved Single-Resolution Optimization

**Date**: 2026-10-29 (Europe/Budapest)
**Status**: Narrow fix implemented and compatibility verified; performance acceptance still fails. Phase 6 remains incomplete and all T041-T048 boxes remain unchecked.

## Scope and implementation

User approved the candidate in dispatch-diagnostic.md: reuse an already-canonical path instead of resolving it again during identity hashing. Reviewed actual loader and identity tests before edits. Preserved the SHA-256 identity algorithm, public helper canonicalization, per-request module execution, fresh compilation, ownership/locks, error contracts, and both loading modes. No path cache, callable cache, dependency change, symlink policy change, or threshold change.

Production change: src/zerodock/engine/loader.py extracts private _resolved_module_name(Path). Public handler_module_name still resolves input then delegates; load_handler resolves once and delegates directly. Python path semantics were checked against [official Path.resolve documentation](https://docs.python.org/3.14/library/pathlib.html#pathlib.Path.resolve).

Test change: tests/unit/test_loader.py adds four cases proving exactly one resolution on present/missing relative targets in both modes, unchanged module identity and successful invocation, plus a public-helper resolution test. Existing same-basename, failure/recovery, stale-bytecode, metadata/debugger, coordination and shared-app tests were reused, not duplicated. No new cross-platform or symlink-runtime evidence is inferred.

## Tests first: red evidence

Existing venv, -B, PYTHONDONTWRITEBYTECODE=1; no concurrent agent-launched checks:

```powershell
& './.venv/Scripts/python.exe' -B -m pytest tests/unit/test_loader.py -k 'resolves_target_once or public_module_identity_still_resolves' -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-06-resolve-red-temp -q --tb=short
```

Before production changes: **4 failed, 1 passed, 60 deselected in 0.48s**, exit 1. All four failures observed duplicate resolution; the public-helper preservation case already passed. Raw output: phase-06-resolve-red-output.txt.

## Focused green evidence

```powershell
& './.venv/Scripts/python.exe' -B -m pytest tests/unit/test_loader.py tests/unit/test_watcher.py tests/unit/test_cli.py tests/integration/test_hot_reload.py -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-06-resolve-green-temp -q --tb=short
```

After the fix: **145 passed in 3.73s**, exit 0. Raw output: phase-06-resolve-green-output.txt. This includes all five added regressions and the prior 140 focused cases.

## Sequential full suite and unchanged performance gates

```powershell
& './.venv/Scripts/python.exe' -B -m pytest tests/unit tests/integration -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-06-resolve-full-temp -q -s --tb=short
```

PYTHONPATH points to project src. **187 passed, 2 failed in 12.48s**, exit 1. No skips/deselections. Both failures are the unchanged conservative <5ms direct ASGI assertions: maximum **20.1003ms off**, **5.9510ms on**. The corresponding invoker-subtracted residuals are 20.0459ms and 5.9006ms. Raw samples and failure output: phase-06-resolve-full-output.txt.

| Measurement | Reload off | Reload on |
| --- | --- | --- |
| Warm-import lifespan startup range, ms | 1.6440-24.6725 | 3.1334-29.5376 |
| Direct ASGI total range, ms | 1.1007-20.1003 | 0.9451-5.9510 |
| Samples above 5ms | 3/20 | 1/20 |
| Isolated app current RSS samples, bytes | 49106944, 49111040, 49115136 | 49274880, 49278976, 49278976 |

Same-metadata detection: 103.7101, 104.5708, 123.6774ms. Atomic detection: 111.4517, 104.7995, 108.9151ms. All six first changed responses were correct and all detection samples meet 500ms. Original startup/request checks, startup samples, isolated-app RSS, and functional tests passed. App-only memory is not live-server memory or proof that the earlier server RSS finding is resolved.

The duplicate-resolution regression is fixed, but that did not guarantee elimination of wall-clock spikes. Sequential execution prevents agent-launched overlap, not arbitrary machine load. Neither a causal speedup nor the cause of individual outliers is established. No further performance rerun, live server, or production optimization was attempted after this failed gate.

## Changed-file quality

Executed sequentially after regression completion:
- Ruff check --no-cache on loader.py and test_loader.py: PASS.
- Ruff format --check --no-cache on those two files: both already formatted.
- mypy --follow-imports=silent with a fresh phase-06-resolve-mypy-cache: no issues in two files.

No unrelated repository-wide quality findings were repaired. Coverage tools remain unavailable and no >90% coverage claim is made. Remaining live-server, release, runtime-matrix and final acceptance work is still open. Review this fix separately from whole-feature acceptance; do not mark incomplete Phase 6 tasks done merely because focused tests pass.
