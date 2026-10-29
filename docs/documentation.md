# Documentation Standards and Review Record

Documentation should help a reader complete a task and accurately describe the
current implementation. It must distinguish requirements, observed evidence,
proposals, and historical records.

## Writing standards

- Lead with the reader's task and prerequisites. Prefer short sections and direct language.
- Provide one complete working path before advanced options. Create every referenced file.
- Identify shell/platform differences and use the intended Python environment explicitly.
- Check field names, defaults, paths, return formats and error examples against code.
- Label proposed interfaces and local-checkout features; do not imply release availability.
- Publish measured performance with scope and boundaries, not unsupported comparative claims.
- Avoid absolute local links, private paths, unverifiable promises and unnecessary superlatives.
- Do not change requirements, approval rules or historical outcomes as a prose cleanup.
- Never include credentials or unsanitized request/log data in examples or reports.

## Current documentation structure

The README is the entrypoint and complete quickstart. The documentation index links
task-focused configuration, handler, reload, troubleshooting, security, architecture,
performance, roadmap, contributor and release guides. Maintainer push/issue handoff
instructions remain separate from onboarding.

## 2026-10-29 review scope

The current documentation refresh checked the CLI, parser/models, event/context,
response/error normalization, loader/watcher, IDE launch configuration and workflow
definitions before rewriting guidance. No production code, acceptance budget,
dependency, release artifact, Git state or remote issue was changed by this refresh.

Corrections include a one-handler quickstart, configuration-relative paths, v2-style
event fields, text/base64 body handling, nullable query parameters, synchronous
timeout limitations, descriptive memory metadata and honest release/platform status.

Historical specifications, measurement reports, constitution requirements, approved
task markers, and local agent/drafting instructions are preserved rather than
rewritten into present-tense success claims. Their roles are explained in the
[specification register](../specs/README.md). Tool-managed skill/template documentation
and generated environments are not product guides and are outside the rewrite.

Local planning aliases point to the canonical roadmap. Starter issue cards are
labeled as implemented handoff or unimplemented proposals. Workflow files themselves
are not edited; the release guide documents their actual configured limitations.

## Validation expectations

Validate relative links in active guides, parse JSON/YAML examples, and exercise
complete handler examples against the actual loader/gateway using disposable files.
Check behavior without query parameters as well as with expected inputs. Run no
package installation, Git command or release operation just because a guide contains it.

Archive reports can contain local-only raw-artifact links. Preserve their provenance
and label publication limits instead of inventing missing evidence or deleting
unfavorable results. A documentation-only validation is not a new full performance
or platform certification.

## Validation Results — 2026-10-29

- Checked 22 active Markdown documents, including current guides, roadmap aliases,
  the specification register, hot-reload validation guide and starter issue cards.
- Verified 90 local links/heading anchors, balanced fences, Python syntax and
  JSON/YAML examples. External links were not treated as proof of remote release/CI status.
- Executed the README handler through the real application lifespan and HTTP
  transport: named query, no-query default and method restriction all passed.
- Validated five additional complete handler examples: basic response, JSON body,
  explicit 201 response, debugger example and timezone-aware datetime response.
  Invalid JSON, missing body and non-UTF-8 body handling passed the documented checks.
  The debugger example used a pause stub; this was not a new GUI/pdb session.
- Ran existing CLI/configuration/event/response/error integration checks:
  **39 passed in 6.35s**, with no source changes. Raw local output is retained at
  `specs/004-performance-remediation/verification/documentation-regression-output.txt`
  and intentionally excluded from publication.
- Checked representative ignore rules: shared indexes/guides are eligible for
  publication; the historical planning archive and raw verification output remain private.
- Confirmed the real `functions/hello.py` and `serverless-local.yaml` hashes were
  unchanged. No package installs, Git commands, remote operations or workflow edits.

The previous detailed private feature catalog is preserved in the local archive
listed by the specification register. Historical specifications, evidence, approval
rules and task completion markers were not rewritten or reclassified as passing.
