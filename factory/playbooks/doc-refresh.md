# Playbook: doc-refresh

Args: `<file-or-glob>`

## Request template
docs: refresh {{1}}. Verify every command, path, link and version mentioned still matches the repo (default branch is `main`; build commands in CONTRIBUTING.md and TESTING.md). Fix what is wrong; do not rewrite style or touch maintainers' "Needs To Be Reviewed" markers.

## Triage hints
type=chore; size S unless many files; reviewers: security, code, ux.

## Done when
Each claim checked against the repo, listed in build.md with the evidence.
