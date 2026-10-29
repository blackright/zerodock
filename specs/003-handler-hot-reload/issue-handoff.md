# Issue #1 Functional Delivery and Performance Follow-up

**Date**: 2026-10-29 (Europe/Budapest)
**Status**: User requested separate performance tracking and human push/closure steps.
No remote issue or pull request was created, pushed, merged or closed by the agent.

The implemented delivery includes opt-in native reload, targeted invalidation,
same-metadata/atomic-save freshness, recovery, sync/async invocation, debugging,
shared-handler coordination and clean shutdown. Primary-runtime full suite: 194 pass.

Unresolved cross-runtime startup/dispatch acceptance is now specified in
[004-performance-remediation](../004-performance-remediation/spec.md), with the
current failure evidence and issue body beside that specification. The human must
create the actual follow-up GitHub issue and link it from #1/the delivery PR before
closing #1 as functional delivery. A local specification is not a remote issue.

This scope handoff does not declare the original Phase 6 universally complete,
erase failed runs, change declared runtime support, weaken constitution 2.0.0,
or mark T043/T045/T047/T048 as passing. If the maintainer does not accept separating
project performance debt from functional delivery, #1 must stay open. Required CI
or branch protection must not be bypassed merely to obtain closure.

See PUSH-GUIDE.md at the repository root for human-only review, staging and PR steps.
