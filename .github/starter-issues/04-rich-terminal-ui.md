# FEAT-014: Terminal Dashboard and Request Metrics

**Status**: Proposal; the current CLI uses its existing textual logging.
**Suggested labels**: enhancement, cli-tui.

## User problem

Developers need clear startup, route and request information without overwhelming
normal terminal output or breaking automation.

## Proposed scope

Consider a readable route summary and request timing/status presentation. Optional
color or dashboard behavior must preserve ordinary redirected/headless output.

A rendering dependency, new flags, metrics definitions and logging integration need
an approved design. In particular, `--plain` and `--no-color` are not current CLI
options and must not be documented as available.

## Design and validation requirements

- Reuse existing log levels, startup data and response diagnostics.
- Define what timing includes before labeling a value as handler or dispatch latency.
- Never log secrets, source text or request bodies to make output more informative.
- Keep terminal capabilities, accessibility and non-interactive output in scope.
- Test route summaries, status formatting, disabled/colorless behavior and overhead.
- Request approval before adding dependencies or changing public command options.

See [the roadmap](../../docs/roadmap.md) and
[performance requirements](../../docs/performance.md).
