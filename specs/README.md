# Specification and Evidence Register

Specifications define scope; task lists record work; evidence records observations.
None is a substitute for the current user guides or an assertion that a remote issue
has been closed. Start with [the documentation index](../docs/README.md).

## Shared active records

| Record | Role and status |
| --- | --- |
| [003: Handler hot reload](003-handler-hot-reload/spec.md) | Functional implementation delivered in the checkout; original Phase 6 performance acceptance remains open |
| [003: Validation guide](003-handler-hot-reload/quickstart.md) | Current disposable/manual and automated validation instructions |
| [003: Memory amendment](003-handler-hot-reload/memory-budget-amendment.md) | Approved scoped <60MB baseline gate; <50MB optimization target |
| [003: Issue handoff](003-handler-hot-reload/issue-handoff.md) | Human-managed functional issue closure with separate performance tracking |
| [004: Performance remediation](004-performance-remediation/spec.md) | Follow-up requirements; ready for planning, not an implemented fix |
| [004: Implementation audit](004-performance-remediation/implementation-audit.md) | Existing code, reuse/preserve decisions, and known failures |
| [004: Issue body](004-performance-remediation/github-issue.md) | Text for a maintainer-created remote issue; no issue number is inferred |

Specification sequence 004 is not roadmap feature FEAT-004, which concerns proposed
additional language runtimes. Task IDs and checked requirement-quality items have
different meanings; a quality checklist does not certify runtime performance.

## Historical and local records

Local directories `001-core-gateway` and `002-pypi-packaging` preserve earlier design,
contract, task and research records. They are excluded by the existing publication
policy and are not linked as downloadable public documentation. Historical wording
must be interpreted in its original phase/date, not as present installation advice.

The local `archive` directory preserves the previous feature catalog before the
documentation refresh. Agent instructions and drafting prompts remain local
operational material; this register does not amend their approval rules.

## Verification artifacts

Reviewed top-level Markdown summaries under active `verification` directories may
be published. Generated raw outputs, executable diagnostic trees, caches and
temporary environments remain ignored. Historical summaries can link to local-only
raw evidence; those links are not promises of public downloads.

Current portable validation results are summarized in
[Performance and validation](../docs/performance.md). Preserve failed measurements
and original requirement versions. Never rewrite an old failure into a pass because
a threshold or workload was later changed.
