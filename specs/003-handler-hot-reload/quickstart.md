# Handler Hot-Reload Validation Guide

**Status**: Functional behavior is implemented in the current checkout. Original
Phase 6 performance acceptance remains open and has a separate
[follow-up specification](../004-performance-remediation/spec.md).
Commands below are instructions, not proof they ran on your machine.

## Prerequisites

Use the intended project environment and current source. Check `dev --help` for
`--reload`; published-release availability is not inferred from the checkout.
Use disposable files and an available loopback port. Do not edit real project
handlers during automated validation.

Start with the complete one-handler setup in
[the README quickstart](../../README.md#quickstart). All configured files must exist.

## Manual refresh journey

1. Start the disposable project with `python -m zerodock.cli dev --reload`.
2. Request its route and record response A, actual server PID, and listening port.
3. Save a distinguishable response B in the configured handler.
4. Wait for the invalidation log, then request again.
5. Confirm response B with unchanged PID and port.

The first post-invalidation request must use fresh source. Requests racing an
incomplete save may fail; an existing invocation can complete with its old callable.

## Recovery and compatibility matrix

| Scenario | Expected result |
| --- | --- |
| Sync or async handler save | Updated response after confirmed invalidation |
| Same-size/same-timestamp edit | Fresh source, including when old bytecode exists |
| Atomic replacement | Observation continues at the configured target |
| Invalid source/entrypoint | Existing structured error, not stale successful output |
| Corrected save | Recovery without restart |
| Post-startup deletion/recreation | Error while absent; recovery after recreation |
| Initially missing file | Configuration validation rejects startup |
| Reload disabled | No observer; existing per-request loading preserved |
| External config directory | Targets resolved relative to the YAML directory |
| Shared handler/two applications | Safe ownership and survivor behavior |
| Normal/cancelled shutdown | Drain owned work; preserve shared executor |
| Helper/YAML/new-route edit | Restart may be required; no automatic graph/config reload |

Automated regression tests cover scenarios that are impractical to reproduce
reliably in an editor. Correctness tests use temporary fixtures and controlled events.

## Automated checks

From the repository root, in the intended environment:

```bash
python -m pytest tests/unit/test_loader.py tests/unit/test_watcher.py tests/unit/test_cli.py
python -m pytest tests/integration/test_hot_reload.py
python -m pytest tests/unit tests/integration
python -m ruff check src/zerodock tests
python -m ruff format --check src/zerodock tests
python -m mypy src/zerodock tests
```

HTTPX transport construction alone does not enter application lifespan. Keep timing
checks separate from tracing, coverage, profiling, and paused debugging. Never reuse
a populated fixed `--basetemp` path without accounting for pytest's cleanup behavior.

## Debugging and shutdown

Follow [the debugger guide](../../docs/hot-reload.md#debugging), send a request,
inspect the handler event/source, and continue. Native controlled checks are recorded;
a complete GUI/IDE validation matrix has not been run.

Stop the gateway normally, wait for shutdown, and restart on the same port. A new
PID is expected for an intentional restart, not for a hot save. A hung filesystem
can delay draining; no forced-I/O-interruption guarantee is made.

## Performance and evidence

Use [the current performance protocol](../../docs/performance.md), including the
approved <60MB baseline current-RSS gate and separate <50MB optimization target.
Startup, dispatch and <=500ms detection requirements are unchanged. Preserve failed
runs and report untested environments rather than expanding a passing claim.

Historical evidence is in `verification/`, particularly phase-06-closeout.md,
live-acceptance.md, memory-amendment-validation.md and runtime-comparison.md.
Their raw output links may reference local artifacts excluded from publication.
The [issue handoff](issue-handoff.md) does not declare all Phase 6 gates complete.
