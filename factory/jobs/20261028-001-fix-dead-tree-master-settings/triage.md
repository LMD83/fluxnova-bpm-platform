# Triage: 20261028-001-fix-dead-tree-master-settings

- type: chore (docs-only link fix)
- size: S (one file, two single-line URL edits, <5 lines changed)

## Findings
CONTRIBUTING.md lines 307 and 399 contain `https://github.com/finos/fluxnova-bpm-platform/tree/master/settings`. The `settings/` folder exists at the repo root. Change `tree/master` to `tree/main` (policy `base_branch = main`) in both. Leave the "Needs To Be Reviewed" markers alone.

## Risk flags
None. CONTRIBUTING.md is not covered by any R-* glob. R-LICENCE covers only LICENSE*, NOTICE, GOVERNANCE.md and SECURITY.md, and CONTRIBUTING.md is none of those. It is a contribution guide, but the change is a URL branch name, not legal wording. Not a protected path.

## Reviewers
security, code (always). No ux or ui: a link-target fix with no user-facing flow, new text or frontend change.

## Split
No. The work is small and has one piece.

## Note for next phases
Lint (`license-header-check`) and `test.module` do not apply to docs. The builder should verify only that no other `tree/master` links were changed, and that the diff is exactly two lines.
