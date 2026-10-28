# Build: 20261028-001-fix-dead-tree-master-settings

## Round 0

Commit `91e5a72b docs(contributing): point settings links at main branch` on `factory/20261028-001-fix-dead-tree-master-settings`. Not pushed.

### Changes
- `CONTRIBUTING.md:307`: `tree/master/settings` -> `tree/main/settings`.
- `CONTRIBUTING.md:399`: `tree/master/settings` -> `tree/main/settings`.
- I made both edits with a line-addressed `sed` (`307s#...#...#;399s#...#...#`), not a whole-file replace. Nothing else changed.

### Verification (run in WORKTREE, `B=claude/loving-cannon-jj9gmg`)
No Maven run, because the job is docs-only (`modules: docs-only` is a placeholder, see spec.md).

```
## AC1  git diff --stat $B...HEAD
 CONTRIBUTING.md | 4 ++--
 1 file changed, 2 insertions(+), 2 deletions(-)
## AC2  grep -n 'fluxnova-bpm-platform/tree/master' CONTRIBUTING.md
exit=1
## AC3  grep -c / grep -n 'fluxnova-bpm-platform/tree/main/settings' CONTRIBUTING.md
2
307
399
## AC4  grep -c 'Needs To Be Reviewed' CONTRIBUTING.md ; changed lines matching the marker
6
0
## AC5  git diff $B...HEAD --word-diff=porcelain -- CONTRIBUTING.md | grep -E '^[+-][^+-]'
-files](https://github.com/finos/fluxnova-bpm-platform/tree/master/settings)
+files](https://github.com/finos/fluxnova-bpm-platform/tree/main/settings)
-settings](https://github.com/finos/fluxnova-bpm-platform/tree/master/settings),
+settings](https://github.com/finos/fluxnova-bpm-platform/tree/main/settings),
## AC6  git diff $B...HEAD --name-only -- engine-rest/ | wc -l
0
```

All of AC1 to AC6 pass.

### Deviations / notes
- The commit subject is `docs(contributing): point settings links at main branch`, as the foreman instructed. The spec proposed `docs: fix dead settings links in CONTRIBUTING.md`.
- The worktree branch was cut from `a0e5f30a`. BASE has since moved to `32e5b5ca` with one factory-state commit (`chore(factory): dry-run job state`), which does not touch `CONTRIBUTING.md`. I ran the checks with triple-dot (`$B...HEAD`) as the spec says, so they cover only this branch's change.
- The `CONTRIBUTING.md:307` diff numstat counts the whole line. `--stat` shows `4 ++--`, which is 2 insertions and 2 deletions, so AC1 is met.
- Nothing is blocked.
