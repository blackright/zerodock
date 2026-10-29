# Release and Publishing Guide

This is a maintainer procedure, not authorization to create a release or evidence
that PyPI/GitHub account settings have been verified. Coding agents do not run Git
or publish artifacts under the current project workflow.

## Before a release

1. Review the intended source, documentation, dependency and compatibility changes.
2. Resolve required CI failures or obtain an explicit reviewed scope decision; do
   not bypass branch protection or describe deferred defects as fixed.
3. Inspect package version metadata, including `[project].version` and the legacy
   `[tool.poetry].version` section. Avoid conflicting release metadata.
4. Build fresh artifacts and verify their contents, version and installed CLI.
   An older wheel in `dist/` is not evidence that current reload code is packaged.
5. Confirm credentials, trusted-publisher configuration, repository permissions and
   the exact publishing destination with the repository owner.

## Configured workflows

The repository's `.github/workflows/ci.yml` configures Ubuntu tests for Python
3.10-3.13 on pushes/PRs targeting `main`. That configuration is not a report that
those jobs passed for a particular commit.

`.github/workflows/publish.yml` is configured for published GitHub releases,
version-pattern tag pushes, and manual dispatch. It builds artifacts with `uv build`,
then defines wheel-install/CLI smoke jobs on Linux, Windows and macOS across Python
3.10-3.13 before its PyPI publishing job.

The publishing job uses the `pypi` environment and OIDC/trusted publishing. Account
configuration must match the repository/workflow/environment. See the official
[PyPI trusted publishing guide](https://docs.pypi.org/trusted-publishers/).

### Important current limitations

- The manual `target_env` input is not wired to an alternate destination in the
  inspected publishing job. Do not assume selecting `testpypi` publishes to TestPyPI.
- Tag, release and manual triggers are distinct entrypoints. Review which one to
  use and avoid accidentally publishing the same version through multiple triggers.
- The inspected workflow does not establish a tag-to-package-version consistency
  check. Verify this deliberately before publishing.
- The smoke matrix checks wheel installation and CLI version/help, not all handler,
  lifecycle, security or performance guarantees.

These are documented workflow limitations, not changes to workflow behavior.

## Local build review

When the existing build tools and build execution are approved:

```bash
uv build
```

Inspect both source distribution and wheel, confirm intended package contents and
`py.typed`, and test a fresh isolated installation. Ensure the reported version and
available CLI flags match the intended release. Avoid global installation and keep
generated archives out of the repository.

Only the human maintainer should create/push the chosen tag or publish the GitHub
release after those checks. Do not treat the examples in a guide as permission to
change package versions, credentials or remote state.

## Release notes

State the shipped behavior, compatibility changes, tested environments, known
limitations and linked follow-ups. Do not advertise all cloud adapters, guaranteed
whole-process startup, or passing performance on an unverified runtime.
The [push guide](../PUSH-GUIDE.md) covers functional issue handoff separately from
package publishing.
