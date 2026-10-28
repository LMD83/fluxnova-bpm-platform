# Factory policy

Human-editable. The foreman, hooks and `factory/bin/factory.py` all read this file.
Only the ` ```policy ` block and the rule/protected tables are parsed. Everything else is commentary.

## Settings

```policy
# --- repo facts (detected from CONTRIBUTING.md, TESTING.md, .github/actions) ---
base_branch            = main
branch_prefix          = factory/
ci_workflow            = build.yaml
commit_style           = <type>(<scope>): <subject>     # CONTRIBUTING.md; scope = maven module, e.g. engine, engine-rest, webapps

# --- commands. {modules} = comma-separated maven modules from spec.md ---
test.module            = mvn -B -e verify -DskipITs=true -pl {modules}
test.full              = mvn -B -e verify -DskipITs=true
lint                   = mvn -B -q -Plicense-header-check validate -pl {modules}   # licence-header check from CONTRIBUTING.md; no other linter exists

# --- preflight ---
preflight.main_green   = ci          # ci | command | skip.  ci = latest GitHub Actions run of ci_workflow on base must be success
preflight.main_cmd     =             # used when main_green = command
parallelism            = 2           # max jobs in build/review/rework at once

# --- loop control ---
max_rework_rounds      = 2
plan_approval          = false       # true = pause after spec for /factory plan <id> approval
merge.auto             = false       # false = a human runs /factory approve. true = foreman merges on approver MERGE
merge.mode             = local       # local = git merge --no-ff into base, never pushes. (pull-request mode: see README, not enabled)
escalate.max_diff_lines = 800        # rule R-SIZE

# --- reviewers that always run (triage may add ux, ui) ---
reviewers.always       = security,code

# --- clean-tree exclusions (git pathspecs relative to repo root) ---
clean_tree.exclude     = factory, .worktrees

# --- execution isolation ---
isolation              = worktree    # worktree | container | remote  (container/remote: see factory/README.md "Isolation interface")
isolation.cmd          =             # when container/remote: command prefix the foreman puts in front of builder/reviewer shell commands

# --- intake write-back (comments on issues / Slack posts). OFF until you turn it on ---
intake.writeback       = off         # off | on

# --- models per role (aliases: opus | sonnet | haiku | fable). Foreman passes these on every Agent call ---
model.foreman              = opus
model.triage               = sonnet
model.investigator         = opus
model.spec-writer          = opus
model.builder              = opus
model.reviewer-security    = opus
model.reviewer-code        = opus
model.reviewer-ux          = sonnet
model.reviewer-ui          = sonnet
model.approver             = opus
model.monitor              = sonnet
```

## Escalation rules

The approver may only ESCALATE by citing one of these IDs. "To be safe" is not a rule.
`Path globs` are a mechanical aid (`factory.py rules-hit <id>`); a rule also fires if the change *semantically* does what the description says.

| ID | Description | Path globs |
|---|---|---|
| R-PAY | Touches payment, billing or money-movement logic | `**/payment*/**`, `**/billing*/**` |
| R-AUTH | Changes authentication, authorisation, identity, permissions, tokens or password handling | `engine/src/main/java/**/impl/identity/**`, `engine/src/main/java/**/impl/cmd/*Authorization*`, `engine/src/main/java/**/AuthorizationService.java`, `engine-rest/**/security/**`, `webapps/**/auth*/**`, `**/*Authentication*Filter*` |
| R-MIG | Database schema, SQL scripts, Liquibase, upgrade/migrator logic | `engine/src/main/resources/org/finos/fluxnova/bpm/engine/db/**`, `**/*.sql`, `database/**`, `migrator/**` |
| R-INFRA | CI, build pipeline, container images, release or deployment configuration | `.github/**`, `Dockerfile`, `Jenkinsfile`, `docker-script.sh`, `settings.xml`, `distro/**`, `RELEASE.md` |
| R-CACHE | Cache keys, cache invalidation or eviction behaviour | `**/cache/**`, `**/*Cache*.java` |
| R-API | Public engine API or REST contract changes (new/removed/changed method on a public interface, REST DTO, OpenAPI) | `engine/src/main/java/org/finos/fluxnova/bpm/engine/*.java`, `engine-rest/engine-rest/src/main/java/**/dto/**`, `engine-rest/engine-rest-openapi/**`, `model-api/**` |
| R-DEPS | Adds, removes or bumps a dependency, parent/BOM, or lockfile (licence and supply-chain impact) | `**/pom.xml`, `bom/**`, `parent/**`, `internal-dependencies/**`, `**/package.json`, `**/package-lock.json` |
| R-LICENCE | Licence headers, LICENSE, NOTICE, CLA/contribution-legal wording, governance or security policy documents | `LICENSE*`, `NOTICE`, `GOVERNANCE.md`, `SECURITY.md` |
| R-FACTORY | Changes the factory itself (agents, skill, hooks, policy) | `.claude/**`, `factory/bin/**`, `factory/policy.md` |
| R-SIZE | Diff larger than `escalate.max_diff_lines` | |

## Protected paths

Builders cannot edit these (hook-enforced). A job that needs one goes `needs-human`; a human can unlock a single glob for a single job with `/factory allow <id> <glob>`.

| Glob |
|---|
| `.github/workflows/**` |
| `.github/CODEOWNERS` |
| `LICENSE*` |
| `NOTICE` |
| `GOVERNANCE.md` |
| `SECURITY.md` |
| `Jenkinsfile` |
| `.claude/**` |
| `factory/bin/**` |
| `factory/policy.md` |
