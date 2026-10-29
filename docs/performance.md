# Performance Requirements and Validation

Performance figures apply to a stated workload and environment. They are not
unqualified promises for arbitrary handlers, imports, disks, or scheduler load.
The [constitution](../.specify/memory/constitution.md) is authoritative.

## Requirements and measurement boundaries

| Measurement | Requirement or interpretation |
| --- | --- |
| Configuration parsing and application creation | Existing benchmark: <100ms |
| Configuration/application/lifespan startup with imports already resident | Separate <100ms engine-startup gate used by the current validation plan |
| Direct ASGI dispatch | <5ms; current tiny-handler total is a conservative bound that includes loading/invocation |
| Existing HTTPX ASGI round trip | Best of three <30ms; not a substitute for isolated dispatch |
| Save completion to invalidation | <=500ms for the disclosed small local workload |
| Actual listening-server current idle RSS | <60,000,000 bytes for the baseline below |
| Memory optimization target | <50,000,000 bytes, reported separately and non-blocking |

Whole-process readiness includes interpreter startup, imports, server initialization,
binding, and the first response. Report it separately: the current results do not
establish <100ms whole-process readiness. Do not present warm-import startup as a
fresh-interpreter or cold-disk result.

User-handler work, loader cost, and instrumentation boundaries must be explicit.
The existing invoker-subtracted diagnostic also excludes signature inspection and
is not a universal definition of gateway overhead. Do not silently change clocks,
exclude additional work, replace maxima with percentiles, or relax assertions.

## Baseline memory protocol

The approved baseline is one actual listening gateway, one route exercised with GET,
one trivial handler source and a config each no larger than 1KiB, no additional
handler dependencies, and no attached debugger or allocation profiler.

1. Run three fresh processes with reload disabled and three with reload enabled.
2. After the first valid response, leave each server idle for 250ms.
3. Record three current RSS samples 100ms apart from the actual server PID.
4. Require every sample to be below 60,000,000 bytes; do not average away a failure.
5. Record the <50,000,000-byte optimization target separately.

Use current working set on Windows or another approved actual-RSS method elsewhere.
Peak RSS, private bytes, traced Python allocations, and app-only processes are not
substitutes. One MB is 1,000,000 bytes; it is not one MiB.

Record OS/filesystem, hardware, runtime/build and dependency versions, source/config
sizes, route/watched-file counts, all raw samples, readiness boundaries, cleanup,
and relevant host conditions. Untested environments remain untested.

The user explicitly amended the former 50MB acceptance gate to the scoped 60MB gate
on 2026-10-29. Historical failures remain failures under their original requirement.
This amendment did not change startup, dispatch, detection, or quality requirements.

## Validation record

The following is recorded local evidence as of 2026-10-29, not a live CI result:

| Environment/check | Recorded result |
| --- | --- |
| Windows / Python 3.14.6 final full suite | 194 passed |
| Windows / isolated Python 3.12.0 final full suite | 192 passed; two performance failures |
| Repository lint/format/configured typing | Pass across 34 source/test files |
| Loader statement coverage | 125/126 executable lines, 99.2063% |
| Watcher statement coverage | 166/174 executable lines, 95.4023% |
| Fresh baseline actual-server memory | All 18 samples pass 60MB; maximum 54.9888MB |

The primary-runtime final run measured startup maxima of 13.5758ms off / 18.3976ms on
and direct ASGI maxima of 1.4612ms off / 2.9545ms on for one 61-byte handler. Six save
detection samples ranged from 99.2796ms to 117.1806ms.

The subsequent isolated Python 3.12 run failed reload-off dispatch at 36.2505ms and
reload-on startup at 230.2233ms. Its recorded reload-on dispatch maximum was also
above 5ms at 23.7090ms. Root cause was not established. The passing primary run
does not erase prior variability or demonstrate stable tail latency everywhere.

Python 3.12.0 is an old patch release used for a controlled diagnostic comparison,
not a deployment recommendation. The package declares Python >=3.10; Python
3.10/3.11/3.13, Linux/macOS and GUI debugger sessions were not locally validated in
this work. The inspected dependency snapshot includes Starlette requiring >=3.11,
so that exact snapshot is not proof of Python 3.10 compatibility. Configured CI
matrices are separate from observed local results.

## Reproducing and reporting

Run functional/quality checks separately from profiling and performance runs.
The existing performance cases are in
`tests/integration/test_performance_benchmarks.py`. Use fresh test temporary paths;
pytest may clear a reused `--basetemp` directory.

Statement coverage was measured with Python's standard-library tracing tool, with
exact core-file filtering and worker tracing. Three debugger cases were excluded
from trace collection because they replace tracing, then included in uninstrumented
full suites. This is not branch coverage. Preserve coverage-tool failures as well
as successful corrected runs.

Use fixed sample counts and predeclared conditions. Keep failed, contended, and
untested runs visible; do not rerun until green and call the defect fixed.

Remaining remediation is specified in
[004-performance-remediation](../specs/004-performance-remediation/spec.md).
No remote issue number or completion is inferred from the existence of that spec.
