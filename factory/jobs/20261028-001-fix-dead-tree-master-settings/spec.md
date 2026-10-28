# Spec: 20261028-001-fix-dead-tree-master-settings

Round 0. First version of this spec.

## Goal
Fix the two dead `tree/master/settings` links in `CONTRIBUTING.md` so they point to `tree/main/settings`. The repo's default branch is `main`, there is no `master` branch, and `settings/` exists on `main`.

## Scope
- `CONTRIBUTING.md:307`: change `https://github.com/finos/fluxnova-bpm-platform/tree/master/settings` to `https://github.com/finos/fluxnova-bpm-platform/tree/main/settings`.
- `CONTRIBUTING.md:399`: make the same change.
- Make both changes as targeted single-line edits. Do not run a whole-file `master` -> `main` replace.

## Non-goals
- Do not change any "Needs To Be Reviewed" marker (lines 23, 42, 131, 305, 380, 411). This includes line 305, which is in the diff context.
- Leave the `camunda/camunda-bpm-platform/wiki/Coding-Style-Java` link on line 307 alone. It points to another repo.
- Leave the dead links at `engine-rest/engine-rest-openapi/README.md:111-112` alone. They are a candidate follow-up backlog item, and line 111 also needs its path changed from `org/camunda/bpm` to `org/finos/fluxnova/bpm`.
- Leave every `tree/master` or `blob/master` link that points to another repo alone (camunda, OAI, angular, FasterXML and so on).
- Make no other wording, formatting or whitespace changes. Do not change line endings or the trailing newline.

## Acceptance criteria
1. AC1: `git diff --stat $BASE...HEAD` lists only `CONTRIBUTING.md`, with `2 insertions(+), 2 deletions(-)`.
2. AC2: `grep -n 'fluxnova-bpm-platform/tree/master' CONTRIBUTING.md` returns no matches (exit code 1).
3. AC3: `grep -c 'fluxnova-bpm-platform/tree/main/settings' CONTRIBUTING.md` returns `2`, and those matches are on lines 307 and 399 (`grep -n`).
4. AC4: `grep -c 'Needs To Be Reviewed' CONTRIBUTING.md` returns `6`. `git diff $BASE...HEAD -U0 -- CONTRIBUTING.md` contains no changed line (`^[+-][^+-]`) that matches `Needs To Be Reviewed`.
5. AC5: Apart from `master` -> `main` in the URL, each changed line is byte-identical to the original. `git diff $BASE...HEAD --word-diff=porcelain -- CONTRIBUTING.md` shows exactly two removed tokens and two added tokens, and they differ only in `master`/`main`.
6. AC6: `git diff $BASE...HEAD --name-only -- engine-rest/` is empty. The out-of-scope README links are untouched.

## Affected files
- `CONTRIBUTING.md`

## Maven modules to test
`modules`: `docs-only`

This is a placeholder value so that the validator, which needs a non-empty list, accepts the spec. It is **not** a real Maven module. The root `CONTRIBUTING.md` is not part of any module build and does not need a licence header. Do not run `test.module` or `lint`, which take `-pl {modules}`. They do not apply, and `-pl docs-only` would fail.

## Test plan
The `git diff --stat` and `grep` checks in AC1-AC6 replace Maven tests and lint. Run them in the worktree against `BASE` (`claude/loving-cannon-jj9gmg`). There is no code, there are no callers and there are no unit or integration tests to run.

## Risk flags
None. `CONTRIBUTING.md` matches no R-* path glob, and it is not a protected path. R-LICENCE covers only `LICENSE*`, `NOTICE`, `GOVERNANCE.md` and `SECURITY.md`. This change only edits a URL branch name, not contribution-legal wording. R-SIZE does not apply, because the diff is 4 lines against a limit of 800.

## Assumptions
- `main` is the right branch for the link target. `policy base_branch = main`, `origin HEAD -> main`, and `settings/` exists on `origin/main` (investigation.md).

## Commit message proposal
```
docs: fix dead settings links in CONTRIBUTING.md
```
No Maven module scope applies, so the `(<scope>)` part is left out. If a scope is required, use `docs(contributing): fix dead settings links`.
