# Roadmap and Capability Status

This roadmap distinguishes implemented behavior in the current checkout from
proposals. It is not a release announcement, delivery schedule, or implementation
approval. Published packages and remote issue status must be verified separately.

## Implemented in the checkout

| Area | Available behavior | Qualification |
| --- | --- | --- |
| FEAT-001: HTTP gateway | YAML routes, native sync/async invocation, local events/context, normalized responses and diagnostics | Local development, not full cloud emulation |
| FEAT-002: Handler reload | Opt-in content observation, targeted invalidation, fresh source, save/error recovery, lifecycle cleanup | Configured handlers only; cross-runtime performance remains open |
| Packaging and CLI foundation | Package entrypoint, version/help, build/publish workflow definitions | A workflow definition is not proof a release was published |

Performance remediation has a separate
[specification](../specs/004-performance-remediation/spec.md). Its directory number
004 is a specification sequence, not the FEAT-004 multi-language proposal below.

## Proposed capabilities

| Feature | Intended direction | Current status |
| --- | --- | --- |
| FEAT-003 | Middleware and cloud lifecycle pipeline | Proposal; current timeout behavior is not a complete lifecycle emulator |
| FEAT-004 | Additional language runtimes | Proposal; Python handlers only today |
| FEAT-005 | Expanded AWS payload/context adapter | Proposal; current v2-style event is not full provider parity |
| FEAT-006 | Cloudflare Workers adapter | Proposal |
| FEAT-007 | Google Cloud Functions/CloudEvent adapter | Proposal |
| FEAT-008 | Local environment/secrets loading | Proposal; no automatic `.env` loading |
| FEAT-009 | Key-value/document-store mock | Proposal |
| FEAT-010 | Local object-storage mock | Proposal |
| FEAT-011 | Pub/sub and queue simulation | Proposal |
| FEAT-012 | Scheduled trigger simulation | Proposal |
| FEAT-013 | Plugin and project scaffolding commands | Proposal; existing `dev` CLI is not a scaffolder |
| FEAT-014 | Terminal dashboard and live metrics | Proposal; no `--plain` dashboard flag exists |
| FEAT-015 | Inspector UI and event replay | Proposal |

Imported-helper dependency reload is not part of the current handler-reload contract.
Do not extend scope based on an older planning card without a new approval.

## Contributing to a proposal

Check the implementation and existing tests first. Describe the user problem,
reuse/replace/preserve decisions, compatibility impact and acceptance evidence.
Separate proposed flags, APIs and YAML fields from implemented interfaces.
Dependency, architecture and budget changes require explicit review.

See [Contributing](../CONTRIBUTING.md) and the
[specification register](../specs/README.md).
