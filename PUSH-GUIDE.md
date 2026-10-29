# Maintainer Push and Issue-Handoff Guide

Use this guide to review and publish the functional hot-reload delivery while
tracking unresolved performance work separately. These are human-run commands;
no agent Git operation, push, merge, or remote issue status is implied.

## 1. Confirm the follow-up

Create or verify the actual GitHub performance issue using
`specs/004-performance-remediation/github-issue.md`. Record its real number and
link it from issue #1 and the delivery PR.

A local specification is not a remote issue. Functional issue closure does not mean
the original Phase 6 performance gates passed. The
[handoff record](specs/003-handler-hot-reload/issue-handoff.md) documents that boundary.

## 2. Inspect the working tree and tracked artifacts

From your repository directory, run:

```powershell
git status --short --branch
git diff --check
git ls-files -ci --exclude-standard
```

The last command lists tracked files that match current ignore rules. Review them;
`.gitignore` does not automatically untrack caches, environments, or credentials.

To untrack one reviewed unwanted file while preserving its local copy:

```powershell
git rm --cached -- "REPLACE_WITH_REVIEWED_FILE_PATH"
```

For a reviewed generated directory, use
`git rm -r --cached -- "REVIEWED_DIRECTORY"`. Never use a blanket reset or clean
command as a shortcut. If a secret was committed, stop, rotate it, and review history
remediation before pushing.

Confirm the intended remote and branch in your Git UI or with `git remote -v`.
Do not publish credential-bearing remote URLs. If a new delivery branch is needed
and the name is unused:

```powershell
git switch -c feat/handler-hot-reload-delivery
```

Keep an existing correct feature branch rather than resetting or replacing it.

## 3. Review and stage intended changes

Use your editor's Source Control view to stage reviewed files individually. Do not
use Stage All or `git add .` when unrelated changes may exist.

Include the intended loader/watcher, CLI/server/app forwarding, fixtures, tests,
and reviewed quality corrections. Check new files as well as modified files.

For reviewed shared documentation, explicit staging can include:

```powershell
git add -- .gitignore README.md CONTRIBUTING.md TROUBLESHOOTING.md PUSH-GUIDE.md docs
git add -- .specify/memory/constitution.md
git add -- specs/README.md specs/003-handler-hot-reload specs/004-performance-remediation
```

The ignore policy excludes agent/local state, private planning, environments, caches,
builds, raw verification output and executable diagnostic folders. Reviewed
top-level Markdown evidence summaries are allowed. Inspect them for local/private
details; their raw-artifact links may refer to intentionally unpublished files.

Do not force-add an ignored verification tree or private planning document merely
to make a directory appear complete.

## 4. Validate the reviewed work

Run the existing checks in the intended environment, separately from profiling:

```powershell
python -m pytest tests/unit tests/integration
python -m ruff check src/zerodock tests
python -m ruff format --check src/zerodock tests
python -m mypy src/zerodock tests
git diff --cached --stat
git diff --cached --check
git diff --cached
```

Consult [the validation record](docs/performance.md#validation-record) for known
performance failures. Record the results you actually obtain. Do not change limits,
rerun until green, or bypass required CI/branch protection to merge.

## 5. Commit and push

When the staged diff contains exactly the intended work:

```powershell
git commit -m "feat: add handler hot reload and specify performance follow-up"
git push -u origin HEAD
```

This pushes the current branch. It does not itself guarantee issue closure.
Use the correct reviewed remote/upstream if your configuration differs; do not
force-push to resolve an unexpected rejection.

## 6. Review and merge the PR

Target the repository's actual default branch. Use this description only after
replacing `FOLLOW_UP_NUMBER` with the real issue number:

```text
Closes #1

Delivers functional in-process handler hot reload, source freshness,
save/error recovery, native debugging, compatibility and clean shutdown.

Remaining cross-runtime performance acceptance is tracked in #FOLLOW_UP_NUMBER
and specs/004-performance-remediation/spec.md. Existing limits remain unchanged.
This is functional delivery, not a claim that all original Phase 6 gates passed.

Test evidence and known limitations: docs/performance.md.
```

Reviewers must accept the documented scope separation and required CI must pass.
Otherwise leave the PR/issue open. A qualifying PR merged into the default branch
automatically closes #1; opening or pushing a PR does not. Verify that the real
performance follow-up remains linked and open.

Package release publishing is a separate operation; see [Releasing](docs/releasing.md).

References: [Git ignore semantics](https://git-scm.com/docs/gitignore) and
[GitHub issue-closing links](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue).
