# Code review: 20261028-001-fix-dead-tree-master-settings (round 0)

Reviewed `git -C .worktrees/20261028-001-fix-dead-tree-master-settings diff claude/loving-cannon-jj9gmg...HEAD`. There is one commit, `91e5a72b docs(contributing): point settings links at main branch`. I re-ran every acceptance check myself in the worktree and did not rely on build.md.

## Verdict

**PASS**

## Independent verification

| AC | Check | Result |
|---|---|---|
| AC1 | `git diff --stat $B...HEAD` | `CONTRIBUTING.md \| 4 ++--`, `1 file changed, 2 insertions(+), 2 deletions(-)`. Only CONTRIBUTING.md changed. PASS |
| AC2 | `grep -n 'fluxnova-bpm-platform/tree/master' CONTRIBUTING.md` | No output, exit 1. PASS |
| AC3 | `grep -c` / `grep -n 'fluxnova-bpm-platform/tree/main/settings'` | `2` matches, on lines 307 and 399. PASS |
| AC4 | `grep -c 'Needs To Be Reviewed'`; changed `-U0` lines that match the marker | `6`; `0`. Line 305 appears only as unchanged context. PASS |
| AC5 | `--word-diff=porcelain`, removed and added tokens | 2 tokens removed and 2 added. Each pair differs only in `master` vs `main`. PASS |
| AC6 | `git diff $B...HEAD --name-only -- engine-rest/ \| wc -l` | `0`. PASS |

Extra checks:
- Byte-level check: I applied `307s#tree/master/settings#tree/main/settings#;399s#...#` to `git show $B:CONTRIBUTING.md` and ran `cmp` against the worktree file. They are **identical**. Nothing else changed: no whitespace, line-ending or trailing-newline differences.
- The link target exists. `git ls-tree $B settings/` lists `eclipse`, `intellij-idea` and `maven`.
- The cross-repo `camunda/camunda-bpm-platform/wiki/...` link on line 307 is untouched, as the spec requires.
- Commit style: `docs(contributing): ...` matches `<type>(<scope>): <subject>`. The spec allows this scope as its fallback. The commit has the required attribution trailers.
- Scope: no scope creep. No licence header applies to a root Markdown file. There are no tests to run, because the job is docs-only and the spec says Maven does not apply.

## Blocking issues

None.

## Non-blocking nits

1. The commit subject (`point settings links at main branch`) differs from the spec's first proposal. build.md records this as a foreman instruction, and it is still within the spec's allowed fallback form. No action needed.
2. Follow-up idea, out of scope for this job: `engine-rest/engine-rest-openapi/README.md:111-112` has the dead `blob/master` links noted in investigation.md. Line 111 also needs its path corrected. Consider adding this as a backlog item.
