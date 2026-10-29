# FEAT-010: Local Object Storage Mock

**Status**: Proposal; not implemented or approved for coding by this document.
**Suggested labels**: enhancement, cloud-mock.

## User problem

Developers need a lightweight way to test object reads/writes locally without
requiring a cloud account or an external storage emulator.

## Proposed scope

Provide a local storage integration for named buckets and object keys, backed by
project-local runtime storage. Basic put, get and list behavior should be isolated
from the core loader and HTTP dispatcher.

Provider-SDK compatibility, a REST API, MIME/metadata behavior, bucket creation,
overwrite rules and missing-object errors require an approved contract before
implementation. Do not imply that existing ZeroDock YAML accepts a storage section
or that a boto3-compatible client already exists.

## Design and validation requirements

- Inspect existing extension boundaries before choosing a new API.
- Define bucket/key validation and prevent paths escaping the approved storage root.
- Specify returned bytes and metadata without inventing provider-parity claims.
- Keep runtime data and credentials out of source control.
- Test writes, reads, listings, missing resources, invalid paths and cleanup with
  disposable storage.
- Request approval before adding a dependency, public endpoint or YAML field.

See [the roadmap](../../docs/roadmap.md) and
[contribution guidance](../../CONTRIBUTING.md) before planning this work.
