# Security review: 20261028-001-fix-dead-tree-master-settings (round 0)

Diff reviewed: `git -C .worktrees/20261028-001-fix-dead-tree-master-settings diff claude/loving-cannon-jj9gmg...HEAD` (one commit, `91e5a72b docs(contributing): point settings links at main branch`).

## Verdict
PASS

What I checked myself:
- The diff touches only `CONTRIBUTING.md`, with 2 insertions and 2 deletions, at lines 307 and 399.
- `--word-diff=porcelain` shows exactly two removed tokens and two added tokens. Each pair differs only in `master` -> `main`.
- Both new URLs stay on the same first-party host and repo (`github.com/finos/fluxnova-bpm-platform`). The link is not redirected to a third-party domain, a look-alike repo or a fork. There is no supply-chain or phishing risk.
- `settings/` exists on `origin/main` (it contains `eclipse`, `intellij-idea` and `maven`), so the target resolves.
- `grep -c 'Needs To Be Reviewed' CONTRIBUTING.md` still returns 6. No marker line is in the changed lines, and line 305 appears only as unchanged context.
- The diff adds no secrets, tokens, credentials, scripts, dependencies, build or CI files, or code.
- No policy rule is hit. R-AUTH, R-PAY, R-MIG and R-DEPS do not apply. R-LICENCE does not cover `CONTRIBUTING.md`, and the change only edits a URL branch name, not legal wording. The file is not a protected path.

## Blocking issues
None.

## Non-blocking nits
- Line 307 still points to the dead third-party `camunda/camunda-bpm-platform/wiki/Coding-Style-Java` link. This is out of scope per spec.md and is a candidate follow-up.
- `engine-rest/engine-rest-openapi/README.md:111-112` still has dead `blob/master` links. These are out of scope per spec.md. Line 111 also needs its path fixed. Consider a backlog item.
