# Contributing to ZeroDock

Contributions should solve a clearly scoped problem, preserve existing behavior,
and include evidence that the change works.

## Before starting

Read the [architecture](docs/architecture.md), [roadmap](docs/roadmap.md),
[performance requirements](docs/performance.md), and
[project constitution](.specify/memory/constitution.md).

Check the implementation and existing tests before proposing a new component.
State what you will reuse, replace, and preserve. Discuss new dependencies,
architecture changes, or changes to acceptance limits before implementing them.

Treat other contributors respectfully and keep reviews focused on the work.

## Development environment

The package declares Python 3.10+. The current validation record covers particular
Windows/Python builds, not a completed support matrix. The pinned development
snapshot also includes dependencies that require Python 3.11 or later.
See [the validation matrix](docs/performance.md#validation-record).

In a cloned checkout:

```bash
python -m venv .venv
```

Activate it in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```bash
source .venv/bin/activate
```

Install the editable package and existing development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Do not change a shared environment or install additional tools without the applicable
maintainer approval. Use a separate environment for runtime comparisons.

## Checks before review

Run checks sequentially when collecting performance results:

```bash
python -m pytest tests/unit tests/integration
python -m ruff check src/zerodock tests
python -m ruff format --check src/zerodock tests
python -m mypy src/zerodock tests
```

`ruff check` is the linter; `ruff format` is the formatter. Inspect any proposed
automatic fix before applying it. Do not suppress findings or relax tests to obtain
a passing result.

The wheel-install smoke test uses a prebuilt wheel and may skip if none exists.
A smoke test against an old wheel does not prove that current source was packaged.
Build/release validation requires a separately reviewed artifact.

## Tests and evidence

- Write a regression test before changing behavior; retain meaningful red/green evidence.
- Use temporary handlers and configurations. Tests must not modify real project handlers.
- Enter application lifespan explicitly in in-process HTTP tests that exercise reload.
- Use event/barrier synchronization for races and cleanup, not guessed sleep durations.
- Keep timing acceptance separate from debugging, tracing, coverage, and profiling.
- Maintain more than 90% statement coverage for touched core logic; report the tool,
  denominator, exclusions, and whether branch coverage was measured.
- Report failed and untested environments honestly. A favorable rerun does not erase
  an earlier failure or establish its cause.

The existing validation used Python's standard-library tracing tool for loader and
watcher statement coverage; no coverage package is required at runtime.
Do not infer current results from historical reports.

## Architectural boundaries

Preserve native execution, configuration-relative paths, handler identity,
per-request module execution, and ownership-safe cleanup. Keep optional integrations
separate from the loader and HTTP dispatch path.

The baseline memory gate is below 60,000,000 bytes of current listening-server RSS;
below 50,000,000 bytes is an optimization target. Startup, dispatch, and detection
limits remain separate. The precise protocol is in [Performance](docs/performance.md).

## Pull requests and issue tracking

1. Agree on scope and identify the issue being addressed.
2. Make focused changes, including documentation and tests for changed behavior.
3. Run the relevant checks and disclose remaining failures or unsupported environments.
4. Review the staged diff, including generated files and secrets.
5. Open a pull request with a summary, test evidence, limitations, and linked issues.

Use closing keywords only for issues the pull request actually delivers. Document
any approved follow-up rather than describing deferred work as fixed.
The [push guide](PUSH-GUIDE.md) covers the hot-reload delivery and its separate
performance follow-up.

The local coding-agent workflow prohibits the agent from running Git commands.
Human contributors manage branching, staging, commits, pushing, and merging.

## Releases

Release instructions and workflow limitations are maintained in
[the release guide](docs/releasing.md). Do not publish, create tags, or change
credentials as part of ordinary feature validation.

## Getting help

Use the [issue tracker](https://github.com/blackright/zerodock/issues) for actionable
reports and proposals. Include a minimal sanitized reproduction, runtime and package
versions, commands, expected/actual behavior, and relevant redacted output.
