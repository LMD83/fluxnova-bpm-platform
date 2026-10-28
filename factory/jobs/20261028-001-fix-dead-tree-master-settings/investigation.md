# Investigation: 20261028-001-fix-dead-tree-master-settings

Round 0. I read the main checkout at `/home/user/fluxnova-bpm-platform`, HEAD `e10e3c5c` on `claude/loving-cannon-jj9gmg`. `git diff main HEAD -- CONTRIBUTING.md` is empty, so BASE and `main` have the same content for this file.

## Current behaviour (premise confirmed)
- The remote default branch is `main`: `git ls-remote --symref origin HEAD` gives `ref: refs/heads/main`. There is no `master` branch locally or on the remote (`git branch -a` lists `main` and `claude/loving-cannon-jj9gmg` only). So any `tree/master/...` link is dead.
- `settings/` exists on `origin/main` and contains `settings/eclipse`, `settings/intellij-idea` and `settings/maven` (`git ls-tree origin/main settings/`).
- `CONTRIBUTING.md:307` reads `[our template and settings files](https://github.com/finos/fluxnova-bpm-platform/tree/master/settings)`.
- `CONTRIBUTING.md:399` reads `[IDE settings](https://github.com/finos/fluxnova-bpm-platform/tree/master/settings)`.
- The fix in both places is `tree/master/settings` -> `tree/main/settings`. Every other repo-self link in CONTRIBUTING.md already uses `main` (for example `CONTRIBUTING.md:5`, `blob/main/CONTRIBUTING.md`).

## "Needs To Be Reviewed" markers (do not touch)
The markers are at `CONTRIBUTING.md` lines 23, 42, 131, 305, 380 and 411. Line 305 (`** Wiki Pages are missing. Needs To Be Reviewed **`) is two lines above the line 307 edit, so it will show up in diff context. It must stay byte-identical. Line 307 also has a dead `camunda/camunda-bpm-platform/wiki/...` link. That link points to another repo and is out of scope.

## Whole-repo scan for repo-self `tree/master` / `blob/master` links
Command: `grep -rnI 'github.com/finos/fluxnova-bpm-platform/(tree|blob)/...'`, excluding `.git`, `node_modules` and `.worktrees`.
- `CONTRIBUTING.md:307`: in scope.
- `CONTRIBUTING.md:399`: in scope.
- `engine-rest/engine-rest-openapi/README.md:111`: `blob/master/engine-rest/engine-rest-openapi/src/main/templates/models/org/camunda/bpm/engine/rest/dto/ExceptionDto.ftl`. This link is out of scope and also dead for a second reason: the path does not exist. The real file is `engine-rest/engine-rest-openapi/src/main/templates/models/org/finos/fluxnova/bpm/engine/rest/dto/ExceptionDto.ftl`, so changing only the branch would still leave the link broken.
- `engine-rest/engine-rest-openapi/README.md:112`: `blob/master/engine-rest/engine-rest-openapi/src/main/templates/paths/process-instance/suspended/put.ftl`. This link is also out of scope. The path exists, so changing `master` to `main` alone would fix it.
- `factory/backlog.md:8`, plus this job's `request.md` and `triage.md`, quote the URL as text. They are not links to fix.
- Every other repo-self link already uses `main`, or a commit SHA (`engine-rest/engine-rest-openapi/README.md:117`).
- The other `tree/master` or `blob/master` hits in the repo point to other repos: `camunda/camunda-bpm-examples`, `camunda/camunda-bpm-platform`, `OAI/OpenAPI-Specification`, `angular/protractor`, `angular-ui/bootstrap` and `FasterXML/jackson-databind`. Examples are `spring-boot-starter/README.adoc:19,24`, `clients/java/README.md:14`, `quarkus-extension/README.md:14` and `engine/src/main/java/.../DefaultDeserializationTypeValidator.java:31`. They are out of scope and should not be changed.

## Affected modules / files
- `CONTRIBUTING.md` (repo root, not a Maven module). There is no code, there are no callers, and no tests cover it.

## Build / test
- The `test.module` and `lint` commands in `factory/policy.md` take Maven `-pl {modules}`. No module applies, because the root `CONTRIBUTING.md` is not part of any module build and has no licence header requirement.
- Verification: `git diff --stat` shows `CONTRIBUTING.md | 2 +-` only. `grep -n 'fluxnova-bpm-platform/tree/master' CONTRIBUTING.md` returns nothing. `grep -c 'Needs To Be Reviewed' CONTRIBUTING.md` stays at 6.

## Constraints
- Docs-only. Change exactly two lines, `CONTRIBUTING.md:307` and `CONTRIBUTING.md:399`.
- Leave all "Needs To Be Reviewed" markers unchanged (request.md).
- `CONTRIBUTING.md` is not a protected path and does not match any R-* glob (`factory/policy.md`). R-LICENCE covers only `LICENSE*`, `NOTICE`, `GOVERNANCE.md` and `SECURITY.md`.
- Commit style `<type>(<scope>): <subject>` (`factory/policy.md`). No module scope applies, for example `docs: fix dead settings links in CONTRIBUTING.md`.

## Open questions
- None blocking. The two dead links in `engine-rest/engine-rest-openapi/README.md:111-112` are out of scope. They could go in a follow-up backlog item, and line 111 also needs its path corrected (`org/camunda/bpm` -> `org/finos/fluxnova/bpm`).

## Risks
- Minimal. The main risk is an editor or a whole-file `master`->`main` replace changing more than intended. Use targeted edits on the two lines.
