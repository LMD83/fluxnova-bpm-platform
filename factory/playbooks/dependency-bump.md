# Playbook: dependency-bump

Args: `<dependency> <target-version>` (e.g. `postgresql 42.7.4`)

## Request template
chore(deps): bump {{1}} to {{2}}. Find every pom/properties reference, update to {{2}}, build the affected modules, and read the release notes for breaking changes. Report licence changes.

## Triage hints
type=chore; flags R-DEPS (always escalates for human approval, by design: supply-chain review); reviewers: security, code.

## Done when
All references updated, `test.module` green for affected modules, no new transitive licence problems noted in build.md.
