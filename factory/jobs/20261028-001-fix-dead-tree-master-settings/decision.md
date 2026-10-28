# Decision: 20261028-001-fix-dead-tree-master-settings (round 0)

**Decision: MERGE**
**Rule: none**

## Evidence
- `factory.py rules-hit`: files `[CONTRIBUTING.md]`, `rules_hit: {}`, `protected_touched: {}`, diff `1 file changed, 2 insertions(+), 2 deletions(-)`.
- Reviews this round: security `PASS` (reviews/security-r0.md), code `PASS` (reviews/code-r0.md). Neither has blocking issues.
- Diff (`git diff claude/loving-cannon-jj9gmg...HEAD`, commit `91e5a72b`): only `CONTRIBUTING.md:307` and `:399` changed, from `tree/master/settings` to `tree/main/settings`. Both URLs stay on the same first-party repo. No "Needs To Be Reviewed" marker changed (count stays at 6).

## Semantic rule check
- R-LICENCE: `CONTRIBUTING.md` matches none of the rule's globs. Line 399 sits in the licence-header section, but the edit changes only a link's branch name. It does not change licence headers, CLA wording or contribution-legal wording, so the rule does not fire.
- R-INFRA: the edit changes a doc link that points to `settings/`. It does not change `settings.xml` or any build or CI configuration.
- R-SIZE: the diff is 4 lines, well under the 800-line limit.
- R-PAY, R-AUTH, R-MIG, R-CACHE, R-API, R-DEPS, R-FACTORY: not applicable. The change is docs only.

No protected path was touched. All reviews pass and no rule fires, so the decision is MERGE.

## Non-blocking follow-ups (from the reviews)
- `engine-rest/engine-rest-openapi/README.md:111-112` has dead `blob/master` links (B-004). Line 111 also needs a path fix.
- `CONTRIBUTING.md:307` has a dead third-party camunda wiki link.
