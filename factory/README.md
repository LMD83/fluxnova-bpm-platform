# Software factory

An agentic pipeline inside this repo: a **foreman** (Claude Code skill) routes each job through specialised sub-agents, each job in its own git worktree, with markdown + JSON as the only state. Built generically from what the repo says about itself (Maven multi-module, Java 17, CI = `mvn verify -DskipITs=true`, `<type>(<scope>): <subject>` commits, FINOS CLA and licence headers).

Design criteria and where they live:

| Criterion | Where |
|---|---|
| 1 Workflow orchestration | `.claude/skills/factory/SKILL.md` (foreman), `factory/bin/factory.py` (legal transitions), `factory/foreman.bpmn` (the model, for the Fluxnova Modeler) |
| 2 Management UI | `factory/dashboard/` via `/factory dashboard` |
| 3 Intake | `factory/backlog.md`, `factory/adapters/{file,github,slack}.py` |
| 4 Execution isolation | git worktrees `.worktrees/<id>`, hooks `factory/bin/hook.py`, policy `isolation` switch |
| 5 Setup / customisation | `factory/policy.md`, `.claude/agents/*.md`, `factory/playbooks/*.md` |

## Pipeline

```
 intake ─ triage ─┬─ investigate ─ spec ─(plan_approval?)─ build ─┐
                  │                                               ▼
                  └─ mission: sub-jobs ──────────────────────▶ review (security ∥ code ∥ ux ∥ ui)
                     (each runs the full pipeline,                │ any FAIL           │ all PASS
                      merges into factory/<parent>)               ▼                    ▼
                                                     rework (round++ ≤ max) ──▶ review  decide (approver)
                                                     > max ─▶ needs-human                │
                                                                          ESCALATE+rule ─┤─ MERGE
                                                                                         ▼
                                                  needs-human ──(human)──▶  awaiting-approval ─ /factory approve ─▶ merged ─ watch ─ done
                                                                                                                       └─ /factory rollback
```

Rules of the road: sub-agents never pick the next phase; every agent result is JSON-validated before a transition; every agent reads the whole `jobs/<id>/` history; the foreman edits only `factory/**`; builders edit only their worktree; nothing is ever pushed.

## Setup (once)

1. Python 3 (stdlib only) and git. `gh` CLI only for the GitHub adapter and the CI check.
2. Commit these files (clean tree is a preflight check), then **restart Claude Code** so the skill, agents and hooks load.
3. Read `factory/policy.md`. Decide `preflight.main_green` (default `ci`: latest `build.yaml` run on `main` must be green; needs `gh`).

Build note: CONTRIBUTING.md says the Fluxnova parent POMs and `fluxnova-feel-scala` must be built or pulled from GitHub Packages first. If `mvn -pl <module> verify` does not run on your machine, builders return BLOCKED instead of claiming a pass. Fix the build environment once; the factory does not hide it.

## Run one job

```
/factory "Fix the dead master links in CONTRIBUTING.md"     # or: /factory next
/factory status
/factory dashboard                                           # http://127.0.0.1:8787
/factory approve <id>                                        # when status says awaiting-approval
```

Other commands: `plan`, `reject`, `rework`, `rollback`, `allow`, `intake`, `watch`, `playbook` (full table in SKILL.md). Ids can be abbreviated (`20261028-001`).

## Run three in parallel

Set `parallelism = 3` in policy.md, then `/factory next --all 3`. Each job gets `.worktrees/<id>` on `factory/<id>`; the 4th waits for a free slot (`FX phase` refuses). Reviews inside a job also run in parallel. Mind your machine: three Maven builds at once want RAM (CI uses `-Xmx8g`).

## Tune policy

Everything is in `factory/policy.md`: models per role, rework rounds, plan approval toggle, `merge.auto`, escalation rules (ID, description, path globs), protected paths, clean-tree exclusions, test/lint commands. Add a rule = add a table row; the approver can only escalate with an ID that exists there (the validator rejects anything else). `python3 factory/bin/factory.py rules-hit <id>` shows what a job's diff trips.

## Add an intake adapter

Create `factory/adapters/<name>.py` with `fetch() -> [{"title","body","ref","priority"}]` (`ref` must be unique and stable; it dedupes) and `report(job, event, text)`. Add `<name>` to the `choices` list of the `intake` command in `factory.py`. Write-back is off until policy `intake.writeback = on`. Contracts: GitHub = issues labelled `factory`; Slack = JSON files in `factory/inbox/slack/` (see the docstring in `slack.py`); file = `.md` in `factory/inbox/`.

## Add a playbook

Copy `factory/playbooks/dependency-bump.md`: **Args**, **Request template** (`{{1}}`, `{{2}}`), **Triage hints**, **Done when**. Run `/factory playbook <name> <args>`.

## Isolation interface (container / remote later)

Default is local worktrees. The seam is policy `isolation` + `isolation.cmd`: when not `worktree`, the foreman prefixes builder/reviewer shell commands with `isolation.cmd` (for example `docker run --rm -v "$PWD/.worktrees/<id>:/work" -w /work maven:3.9-eclipse-temurin-17` or `ssh sandbox`). Contract for any sandbox: it sees only the job's worktree (read-write for the builder, read-only for reviewers), has no credentials, and results come back as the same validated JSON. **This switch is documented, not implemented or tested.**

## Hooks (`.claude/settings.json`, `factory/bin/hook.py`)

Inert unless `factory/runtime/ACTIVE` exists (the foreman creates it while running; normal Claude Code use in this repo is unaffected). Active: blocks edits to the main checkout, blocks subagents from editing outside `jobs/<id>/` or (builder only) `.worktrees/<id>/`, blocks protected paths, blocks subagent `git push/merge/rebase/checkout/switch/reset --hard/tag/worktree/clean`. Logs tool activity to `factory/runtime/activity/<job>.jsonl` (shown in the dashboard). Limits: it cannot see inside arbitrary shell commands (a builder could still write with `sed -i` or a redirect); `factory.py audit <id>` and the `merge` command re-check protected paths on the actual diff, which is the backstop.

## Files

```
.claude/skills/factory/SKILL.md      foreman        .claude/agents/*.md   10 sub-agents
.claude/settings.json                hooks          factory/policy.md     all tunables (human-edited)
factory/backlog.md                   queue          factory/jobs/<id>/    request, triage, investigation, spec, build,
factory/playbooks/                   recurring                            reviews/, results/, decision, monitor, log.md, status.json
factory/adapters/ inbox/             intake         factory/dashboard/    UI          factory/bin/  factory.py, hook.py
```

Committed: policy, backlog, jobs, adapters, playbooks. Ignored: `.worktrees/`, `factory/runtime/`, `inbox/**/processed/`.
