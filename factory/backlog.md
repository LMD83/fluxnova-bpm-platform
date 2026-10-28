# Backlog

Prioritised queue (P0 highest). Format is parsed by `factory/bin/factory.py`:
`- [ ] B-nnn | P<n> | <title> | src=<ref>` then indented detail lines. `[ ]` open, `[~]` in progress (`job=` added), `[x]` merged.
Add items by hand, with `/factory intake github|slack|file`, or let `/factory` create jobs directly.

- [~] B-001 | P2 | Fix dead `tree/master/settings` links in CONTRIBUTING.md | src=seed | job=20261028-001-fix-dead-tree-master-settings
  CONTRIBUTING.md lines 307 and 399 link to `.../fluxnova-bpm-platform/tree/master/settings`, but the default branch is `main`
  (the `settings/` folder exists). Fix both links. Docs only. Do not touch the "Needs To Be Reviewed" markers; those are the maintainers' notes.
- [ ] B-002 | P3 | Remove empty tracked `errors.txt` from the repo root | src=seed
  `errors.txt` is a zero-byte file tracked at the repository root. Check nothing references it (scripts, workflows, docs, poms); if nothing does, delete it.
- [ ] B-003 | P3 | Consolidate duplicate Renovate configs | src=seed
  `.github/renovate.json` (220 B) and `.github/renovate.json5` (1.8 KB) both exist. Renovate reads only one by precedence. Determine which one is effective, and remove or merge the other.
  Expected to touch `.github/**` (policy rules R-INFRA, protected paths), so it should escalate to a human.
