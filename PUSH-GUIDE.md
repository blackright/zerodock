# Push the Hot-Reload Delivery and Track Performance Separately

These commands are for the human maintainer. The agent has not run Git, inspected
Git state, pushed, or created/closed any GitHub issue. Do not treat this guide as
evidence that your branch, remote, staging area or CI is clean.

## 1. Create the performance follow-up first

On GitHub, create an issue using
`specs/004-performance-remediation/github-issue.md`. Record its actual issue number.
The new specification and its audit describe the remaining startup/dispatch failures.
Link that issue from #1 before closing #1 as functional delivery.

The user requested this separation, but it is not a statement that every original
Phase 6 gate passed. `specs/003-handler-hot-reload/issue-handoff.md` records the scope.

## 2. Inspect locally

From `C:\dev\python\zerodock`, run:

```powershell
git status --short --branch
git diff --check
git ls-files -ci --exclude-standard
```

The last command finds already tracked files that now match ignore rules. New
ignore patterns do not automatically remove tracked environments, secrets or caches.
Inspect every result. For an unwanted tracked file, untrack only its reviewed path:

```powershell
git rm --cached -- "REPLACE_WITH_REVIEWED_FILE_PATH"
```

For a reviewed generated directory, use `git rm -r --cached -- "REVIEWED_DIRECTORY"`.
These untrack files but keep local copies. Never run a blanket index reset or clean
command as a shortcut. If a real secret is already committed, stop, rotate it and
review history remediation before pushing; .gitignore is not a secret scanner.

Check that your remote points to the intended repository using your local Git UI
or `git remote -v`; do not publish credential-bearing remote URLs. If currently on
the default branch and a delivery branch is needed, create an unused branch:

```powershell
git switch -c feat/handler-hot-reload-delivery
```

If already on the correct feature branch, keep it. Do not force-reset another branch.

## 3. Stage only reviewed work

Use your editor's Source Control view to review and stage intended source/test
changes file by file. Do not use `git add .` or Stage All: unrelated user edits may
exist and no agent checked the index.

The delivery includes loader/watcher, CLI/server/app forwarding, shared fixtures,
reload tests and the reviewed quality-only corrections. Review all relevant modified
files under `src/zerodock` and `tests`; include the new watcher and test files if they
are untracked. Root `functions/hello.py` and `serverless-local.yaml` were preserved.

After review, shared documentation can be staged explicitly:

```powershell
git add -- .gitignore README.md CONTRIBUTING.md PUSH-GUIDE.md
git add -- .specify/memory/constitution.md
git add -- specs/003-handler-hot-reload specs/004-performance-remediation
```

The new ignore policy permits those two shared specification directories and
reviewed top-level Markdown verification summaries. It excludes generated raw
outputs, diagnostic execution folders, temporary environments/caches, credentials,
builds and agent/local Spec Kit state. Historical summaries can contain local paths;
review before staging. Their raw-artifact links may refer to intentionally unpublished
local files; the follow-up audit contains portable key measurements.

Other private planning/agent files remain ignored, including `Specs-Dafting.md`,
`Phase-Builder-Agent.md`, local roadmaps and `.specify/feature.json`. Do not force-add
them or ignored verification trees simply to make a directory appear complete.

## 4. Validate and inspect the staged patch

Run the existing checks, without installing new packages:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& './.venv/Scripts/python.exe' -B -m pytest tests/unit tests/integration -p no:cacheprovider -q
& './.venv/Scripts/python.exe' -B -m ruff check --no-cache src/zerodock tests
& './.venv/Scripts/python.exe' -B -m ruff format --check --no-cache src/zerodock tests
& './.venv/Scripts/python.exe' -B -m mypy src/zerodock tests
git diff --cached --stat
git diff --cached --check
git diff --cached
```

Latest recorded primary-runtime run passed 194 tests. The isolated Python 3.12 run
had 192 passes and two performance failures; those are the follow-up's known debt,
not a passing runtime. Do not claim new test results you did not run, keep rerunning
until green, bypass required CI/protection, or change limits merely to merge.

## 5. Commit and push

Only when the staged diff contains exactly the intended reviewed work:

```powershell
git commit -m "feat: add handler hot reload and specify performance follow-up"
git push -u origin HEAD
```

This pushes the current branch, not necessarily the default branch, and does not
itself guarantee issue closure. If remote/upstream configuration differs, use the
correct reviewed remote/branch rather than force-pushing.

## 6. Open and merge the delivery PR

Target the repository's actual default branch. In the PR description, use the text
below only after replacing `FOLLOW_UP_NUMBER` with the real issue number:

```text
Closes #1

Functional delivery: opt-in in-process handler hot reload, source freshness,
save/error recovery, native debugging, compatibility and clean shutdown.

Remaining cross-runtime startup/dispatch acceptance is tracked in #FOLLOW_UP_NUMBER
and specs/004-performance-remediation/spec.md. This closes functional delivery,
not all original Phase 6 performance gates. Existing limits remain unchanged.

Evidence: 194 tests passed on Windows/Python 3.14.6; isolated Python 3.12.0 had
192 passes and two performance failures. Configured quality checks and >90%
touched-core statement coverage pass. Baseline actual-server memory meets the
separately approved <60MB requirement; <50MB remains an optimization target.
```

Reviewers must accept the documented scope separation and all required CI checks
must pass before merge. If they do not, leave the PR/issue open; do not bypass checks.
GitHub closes #1 when the qualifying PR is merged into the default branch, not merely
because a spec was written or a feature branch was pushed. Verify the real follow-up
remains open and linked after merging.

References: [Git ignore semantics](https://git-scm.com/docs/gitignore) and
[GitHub issue-closing links](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue).
