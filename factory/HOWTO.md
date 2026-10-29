# How to set up the software factory in any repo

For: Mac Studio (zsh). Windows laptop: run the same commands in WSL or Git Bash. Time: about 20 minutes for the first repo, 5 for the next.

What you end up with: type `/factory "do X"` in Claude Code and a foreman routes X through triage, investigate, spec, build, reviews, rework, approve. You approve the merge. Nothing is pushed or deployed by the factory.

## Step 0. Prerequisites

```bash
git --version
python3 --version        # 3.9 or newer; stdlib only, nothing to pip install
claude --version         # Claude Code CLI
brew install gh          # optional: GitHub intake and the "main is green" check
gh auth login            # optional
```

## Step 1. Get the factory source

One clone, reused for every repo you install into:

```bash
git clone -b claude/loving-cannon-jj9gmg https://github.com/LMD83/fluxnova-bpm-platform ~/src/factory-source
```

(When this branch is merged somewhere permanent, point at that instead.)

## Step 2. Install it into your target repo

```bash
SRC=~/src/factory-source
cd ~/path/to/your-repo
git checkout -b factory-setup

mkdir -p .claude/skills
cp -R "$SRC/.claude/agents" .claude/
cp -R "$SRC/.claude/skills/factory" .claude/skills/

# hooks: only copy if you have no .claude/settings.json yet, otherwise merge the "hooks" block by hand
[ -f .claude/settings.json ] && echo "MERGE hooks by hand from $SRC/.claude/settings.json" || cp "$SRC/.claude/settings.json" .claude/

rsync -a --exclude 'jobs/*' --exclude runtime --exclude backlog.md --exclude '*.png' --exclude __pycache__ "$SRC/factory/" factory/
mkdir -p factory/jobs && touch factory/jobs/.gitkeep
printf '# Backlog\n\n' > factory/backlog.md

printf '\n# software factory\n.worktrees/\nfactory/runtime/\nfactory/inbox/processed/\nfactory/inbox/slack/processed/\n!/factory/bin/\n__pycache__/\n' >> .gitignore
```

The `!/factory/bin/` line matters: many repos ignore any folder called `bin`, which would silently drop the factory's scripts from git.

## Step 3. Edit `factory/policy.md` (the only file you must change)

Open it. Everything the factory does is driven from here. Change these before the first run:

| Key / table | Set it to |
|---|---|
| `base_branch` | your main branch (`main`) |
| `setup` | install step for a fresh worktree, e.g. `npm ci` (delete the key if none) |
| `test.module`, `test.full` | your test command, e.g. `npm test` (`{modules}` is optional) |
| `lint` | e.g. `npm run lint && npx tsc --noEmit && npm run build` |
| `ci_workflow` / `preflight.main_green` | your CI file name, or `skip` if there is none, or `command` plus `preflight.main_cmd` |
| `plan_approval` | `true` if you want to read the spec before anything is built |
| `merge.mode` | `local` (factory merges locally after you approve) or `never` (you merge by hand; use for repos where Claude must not merge) |
| `parallelism` | jobs at once (2 is safe) |
| Escalation rules table | one row per thing a human must always see: auth, secrets, migrations, payments, deps, infra. The globs are guesses until you tune them |
| Protected paths table | files builders can never edit: `AGENTS.md`, `.env*`, CI workflows, deploy config |
| `model.*` | opus or sonnet per role; sonnet everywhere is cheaper |

Rule of thumb: when unsure, add a rule. Escalating costs you a click; a missed escalation costs more.

## Step 4. Smoke-test the scripts (no Claude needed)

```bash
python3 factory/bin/factory.py backlog          # prints nothing yet, no error
python3 factory/bin/factory.py preflight        # shows which checks pass/fail
python3 factory/bin/factory.py status           # prints nothing yet, no error
```

`preflight` fails on a dirty tree. Commit first (Step 5). It also needs to be on `base_branch`, so run it from there.

## Step 5. Commit it and restart Claude Code

```bash
git add -A && git commit -m "feat(factory): add software factory"
git checkout main && git merge factory-setup      # or open a PR; the factory needs to exist on your base branch
claude                                            # start a NEW session in the repo root
```

Starting a new session is what loads the skill, agents and hooks. Check:
- type `/factory` and see it in the menu
- `/agents` lists triage, investigator, spec-writer, builder, four reviewers, approver, monitor
- Claude Code may ask you to trust the project hooks. Say yes.

## Step 6. Seed the backlog

Edit `factory/backlog.md`. One line per item, details indented:

```
- [ ] B-001 | P2 | Short title | src=manual
  What to do, where, and what NOT to touch. Include how you will know it worked.
```

`P0` is highest. Small, concrete, testable items work best. Or skip the backlog and use `/factory "..."` directly.

## Step 7. Run your first job

```
/factory next                       # takes the top backlog item
/factory "Add tests for the eligibility check"
/factory status
/factory dashboard                  # open http://127.0.0.1:8787
```

What happens, in order, and what you do:

| Phase | Who | You |
|---|---|---|
| preflight | foreman | nothing; it stops and tells you if the tree is dirty or main is red |
| triage, investigate, spec | agents | nothing (or `/factory plan <id>` to approve the spec if `plan_approval = true`) |
| build | builder in `.worktrees/<id>` | nothing |
| review | security + code (+ ux/ui if relevant) in parallel | nothing |
| rework | builder again, up to `max_rework_rounds` | nothing |
| decide | approver | nothing |
| `awaiting-approval` | | **review the diff, then `/factory approve <id>`** |
| `needs-human` | | read the cited rule ID, then approve, `/factory rework <id> "notes"`, or `/factory reject <id> "why"` |

Review the change yourself before approving:

```bash
git diff <base>...factory/<job-id>      # or open .worktrees/<job-id>
```

With `merge.mode = never`, `/factory approve` refuses and prints the `git merge` for you to run. Pushing is always yours.

## Step 8. After merging

```
/factory watch <id>        # monitor checks CI since the merge
/factory rollback <id>     # reverts the merge commit; asks you first
```

Each merge leaves a tag `factory/pre-<id>` as the checkpoint.

## Step 9. Going further

- **Parallel:** set `parallelism = 3`, then `/factory next --all 3`. Each job gets its own worktree. Mind RAM.
- **Big requests:** triage may split a large request into a mission of sub-jobs that merge into a parent branch, reviewed once as a whole.
- **Playbooks:** copy `factory/playbooks/dependency-bump.md`, edit, run `/factory playbook <name> <args>`.
- **GitHub issues:** label an issue `factory`, run `/factory intake github`. Write-back (comments, closing) stays off until `intake.writeback = on`.
- **Slack or files:** see `factory/adapters/slack.py` and `file.py` docstrings. Drop `.md` files in `factory/inbox/` and run `/factory intake file`.
- **Add a reviewer or rule:** a new `.claude/agents/<name>.md` plus a table row. Rules are only valid if their ID exists in `policy.md`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `/factory` not in the menu | You did not start a new session after installing, or `.claude/skills/factory/SKILL.md` is missing |
| `preflight`: clean tree fails | Commit or stash. Changes under `factory/` are ignored, everything else counts |
| `preflight`: checked out on base fails | `git checkout <base_branch>` in the main checkout |
| `preflight`: base green UNKNOWN | `gh` not installed or no CI run found. Fix `gh auth login`, set `preflight.main_green = skip`, or ask the foreman to proceed with `--allow-unknown` |
| Builder returns BLOCKED on tests | The build cannot run in the worktree. Fix `setup`/`test.module`, or the dependency problem. The factory will not fake a pass |
| Edit blocked by hook | A protected path or the main checkout. Intended. `/factory allow <id> '<glob>'` unlocks one path for one job |
| Job stuck in `needs-human` | `python3 factory/bin/factory.py status <id>` shows the reason and rule |
| `no worktree slot free` | Another job is building. Raise `parallelism` or wait |
| `merge: main checkout must be on '<base>'` | `git checkout <base>` in the main checkout, then approve again |
| Scripts missing from git | Your repo ignores `bin/`. Add `!/factory/bin/` to `.gitignore` |
| Hooks seem to do nothing | By design they only act while `factory/runtime/ACTIVE` exists (the foreman creates it). Normal Claude Code use is untouched |

## Limits worth knowing

- The hook cannot see inside arbitrary shell commands. A builder could still write a file with `sed -i`. The merge step re-checks the real diff against protected paths.
- Container or remote isolation is documented in `factory/README.md` but not implemented.
- Costs: opus on five roles is the heavy part. Switch `model.*` to sonnet in policy to cut usage.
- The agents trust the files they read. Do not point the factory at untrusted input without reading each spec first (`plan_approval = true`).

## Rebuilding it from scratch instead of copying

Give Claude Code the "software factory" prompt in a fresh repo and ask for the dry run. Lessons from the first build, worth adding to the prompt so you do not hit the same bugs:

1. Hooks must be inert unless the factory is running, or they will block normal editing.
2. Allow `git merge-base` for sub-agents (a regex for "merge" blocks it).
3. Result parsing: try the whole JSON first, not the last `{`.
4. A repo-wide `.gitignore` entry for `bin` will hide `factory/bin/`.
5. Fresh worktrees need an install step (`setup`).
6. Offer a `merge.mode = never` switch for repos where the factory must not merge.
7. Job ids must be matched with a strict pattern, not "anything up to the next slash".
