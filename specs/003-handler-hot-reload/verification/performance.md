# Phase 6 Performance Evidence — Acceptance Stopped

**Date**: 2026-10-29 (Europe/Budapest)
**Current status (2026-10-29 closeout)**: Amended <60MB baseline actual-server memory passes 18 samples, maximum 54.9888MB; <50MB remains an unmet optimization target. Final 3.14 full suite passes unchanged timing gates: maximum warm-import startup 18.3976ms and direct ASGI total 2.9545ms; save detection <=117.1806ms. The subsequent isolated 3.12 suite fails off dispatch (36.2505ms) and on startup (230.2233ms); on dispatch also records >5ms. See phase-06-closeout.md. Earlier measurements remain historical; no other threshold or runtime default changed. Combined performance acceptance remains open.

## Later Sequential Full-Suite Finding

The user approved live-server checks and a sequential full suite. The suite ran first without concurrent agent-launched checks or servers. Result: **183 passed, 1 failed in 21.48s**. See [phase-06-full-sequential-output.txt](phase-06-full-sequential-output.txt) and regression.md for the command and raw failing-case samples.

Reload-on warm-import startup remained below 100ms (7.2668-34.2297ms). One of the 20 direct ASGI samples was **5.3948ms**, above 5ms; its invoker-subtracted residual was **5.2357ms**. The other 19 totals in that case were below 5ms. No failure was reported for reload-off dispatch, detection, original benchmarks, or isolated-app RSS.

The earlier 8/8 performance-only pass is not erased, and this later failure is not waived. Absence of concurrent agent checks does not mean the whole machine was idle or identify the cause. No live server was launched after the failed gate. Next recommended action, requiring approval: inspect timing instrumentation and perform a bounded diagnostic profile of this case without changing limits or production behavior. Do not blindly rerun until green.

## Approved Sequential Rerun

The user approved a performance-only sequential rerun. No concurrent quality checks, production edits, threshold changes, or installations were performed. Other machine activity was not independently controlled or measured.

Command from the repository root, with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH pointing to src:

```powershell
& './.venv/Scripts/python.exe' -B -m pytest tests/integration/test_performance_benchmarks.py -p no:cacheprovider --basetemp=specs/003-handler-hot-reload/verification/phase-06-sequential-performance-temp -q -s -x --tb=short
```

**Result**: exit 0; **8 passed in 8.76s**. Raw samples: [phase-06-sequential-performance-output.txt](phase-06-sequential-performance-output.txt). Same test definitions and one 61-byte handler workload; original startup/request checks also passed.

| Measurement | Reload off | Reload on |
| --- | --- | --- |
| Warm-import config/app/lifespan startup (10 samples), ms | 2.7683-29.4119 | 4.3255-37.8426 |
| Direct ASGI total (20 samples after 3 warmups), ms | 1.2520-2.9158 | 1.0182-2.6222 |
| Invoker-subtracted residual, ms | 1.2090-2.8474 | 0.9760-2.5411 |
| Isolated idle app current RSS, bytes | 48807936, 48812032, 48812032 | 48992256, 48996352, 48996352 |

Same-metadata detection: 116.3966, 99.8328, 102.6501ms; changed-request HTTPX durations: 6.0094, 3.9957, 6.3469ms. Atomic detection: 111.4707, 99.6525, 98.8896ms; changed-request durations: 6.2113, 6.0248, 5.3664ms. All six responses reflected the saved version and all detection samples met 500ms.

Isolated app RSS maxima are 48.812032MB off and 48.996352MB on (decimal MB), below 50MB in these child processes. This measures a fresh app/lifespan without a listening Uvicorn server, not the earlier live-server boundary. Child commands returned zero after lifespan exit. Fresh-process listening-server RSS/readiness, live PID/port/shutdown, and other supported platforms remain unverified in Phase 6. Earlier live-server RSS failure is not resolved by this narrower measurement.

The rerun demonstrates that the earlier timing failures did not recur under the sequential conditions; it does not prove their cause or guarantee all workloads meet the budgets. No complete feature acceptance is claimed.

## Earlier Concurrent-Load Run (Retained)

## Workload and method

Windows 11 build 26300, Python 3.14.6, existing project dependencies. Earlier machine inventory: Intel Core 7 240H, 16 logical processors, NTFS. No runtime/package upgrades were performed. One configured temporary handler, **61 source bytes**, one route; reload-on watches exactly one file, reload-off watches zero. The observer uses its existing 100ms interval.

The test module uses perf_counter_ns. Startup times include config parsing, app creation, and explicit lifespan entry with imports already resident (10 samples each). Direct ASGI totals include source loading/compilation, event/context/response handling, tiny synchronous handler, invoker and timing instrumentation (3 warmups, 20 samples). The separately timed invoker includes signature inspection; subtracting it does not define universal dispatch overhead. Total <5ms is used as a conservative tiny-handler check. No whole-process startup claim follows from warm imports.

All raw samples are printed in phase-06-regression-output.txt. Quality checks ran concurrently and contaminated timing conditions. These results cannot establish a controlled baseline comparison or attribute causality to hot reload. They must not be hidden or declared passing.

| Boundary | Reload off | Reload on |
| --- | --- | --- |
| Warm-import lifespan startup range | 7.0865-70.6323ms | 13.3215-115.8036ms |
| Direct ASGI total range | 5.9042-19.0242ms | 8.2829-39.1928ms |
| Invoker-subtracted residual range | 5.8005-18.8979ms | 5.8407-34.2388ms |
| Existing config/app <100ms benchmark | PASS (original default-mode test) | Not the original benchmark |
| Existing best-of-three ASGI <30ms | PASS (original default-mode test) | Separate direct ASGI samples above |

The reload-on startup maximum violates 100ms. Both modes have dispatch observations above 5ms. The test stops at its first assertion failure per case, so the reload-on dispatch observation is not a separately executed failed assertion.

## Detection and first changed request

These cases used the actual background observer; no scan was manually forced. The callback timestamps acknowledgement after the real invalidation helper returns. The completed-save timestamp is captured after source write/rename and metadata restoration. Three saves B/C/D each; all responses matched the saved version.

| Save | Save-to-invalidation ms | Changed HTTPX ASGI request ms |
| --- | --- | --- |
| Same length and restored timestamps | 117.599, 83.1827, 94.2167 | 31.4238, 44.1991, 23.1982 |
| Atomic replacement | 113.9062, 80.0743, 83.4434 | 17.6939, 16.2316, 14.8618 |

All six detection samples meet <=500ms for this small local workload under the disclosed conditions. Request durations include HTTPX overhead and are not isolated dispatch values. Stale pre-existing bytecode correctness remains covered by earlier loader/integration tests.

## Unexecuted gates and baseline comparison

Current idle RSS tests were authored but **not run** after stopping acceptance. Their method launches an isolated app/lifespan process (not pytest RSS), settles 250ms, samples Windows WorkingSetSize three times 100ms apart, and exits lifespan normally. This does not include a listening Uvicorn server and must not be presented as directly comparable to the earlier live-server baseline.

Fresh-process listening-server readiness, actual idle server RSS, PID/port stability, and live graceful shutdown were not measured in Phase 6. Earlier baseline: 53.747712-53.948416 decimal MB current live-server RSS; readiness 716.8270-775.8206ms. Earlier warm-import startup 0.8806-1.3537ms and direct ASGI total 0.6491-0.8938ms used a different 529-byte repository handler and no concurrent quality checks. Neither a causal overhead percentage nor final compliance can be inferred.

Next recommended step, requiring approval: rerun the new timing checks sequentially on an otherwise idle machine; preserve both runs. If violations persist, investigate the measurement boundary and actual hotspots before proposing narrow fixes. No production optimization is authorized by this report.

## Official method references

- [Python 3.14 performance counter](https://docs.python.org/3.14/library/time.html#time.perf_counter_ns).
- [Microsoft current process memory information](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessmemoryinfo).
- [HTTPX lifespan responsibility](https://www.python-httpx.org/advanced/transports/#asgi-startup-and-shutdown).
