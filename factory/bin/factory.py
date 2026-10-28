#!/usr/bin/env python3
"""Factory helper. Stdlib only. The foreman (Claude) decides; this script enforces.

Owns: job state + legal phase transitions, output schema validation, preflight,
worktrees, merge/rollback, rule matching, backlog, intake, dashboard.
Run `python3 factory/bin/factory.py -h`.
"""
import argparse, importlib.util, json, re, subprocess, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
F = ROOT / "factory"
JOBS = F / "jobs"
RUNTIME = F / "runtime"
ACTIVE_PHASES = {"build", "review", "rework"}

TRANSITIONS = {
    "intake": ["triage"],
    "triage": ["investigate", "mission", "needs-human"],
    "mission": ["review", "needs-human"],
    "investigate": ["spec", "needs-human"],
    "spec": ["plan-approval", "build", "needs-human"],
    "plan-approval": ["build", "spec", "rejected"],
    "build": ["review", "needs-human"],
    "review": ["rework", "decide", "needs-human"],
    "rework": ["review", "needs-human"],
    "decide": ["awaiting-approval", "needs-human"],
    "awaiting-approval": ["merged", "rework", "rejected", "needs-human"],
    "needs-human": ["triage", "investigate", "spec", "build", "review", "rework", "merged", "rejected"],
    "merged": ["watch", "done", "rolled-back"],
    "watch": ["done", "rolled-back"],
    "done": [], "rejected": [], "rolled-back": [],
}

# ---------------------------------------------------------------- policy

def policy_text():
    return (F / "policy.md").read_text()

def policy():
    m = re.search(r"```policy\n(.*?)```", policy_text(), re.S)
    d = {}
    for line in m.group(1).splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d

def plist(v):
    return [x.strip() for x in v.split(",") if x.strip()]

def table(section):
    """Rows of the markdown table under '## <section>' as lists of cells."""
    m = re.search(r"## %s\n(.*?)(?=\n## |\Z)" % re.escape(section), policy_text(), re.S)
    rows = []
    for line in m.group(1).splitlines():
        if line.startswith("|") and not re.match(r"^\|[\s\-|]+\|$", line):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows[1:]  # drop header

def globs(cell):
    return re.findall(r"`([^`]+)`", cell)

def rules():
    return {r[0]: (r[1], globs(r[2]) if len(r) > 2 else []) for r in table("Escalation rules")}

def protected():
    return [g for r in table("Protected paths") for g in globs(r[0])]

def glob_re(g):
    out, i = "", 0
    while i < len(g):
        if g[i:i + 3] == "**/":
            out += "(?:.*/)?"; i += 3
        elif g[i:i + 2] == "**":
            out += ".*"; i += 2
        elif g[i] == "*":
            out += "[^/]*"; i += 1
        elif g[i] == "?":
            out += "[^/]"; i += 1
        else:
            out += re.escape(g[i]); i += 1
    return re.compile("^" + out + "$")

def matches(path, globlist):
    return [g for g in globlist if glob_re(g).match(path) or glob_re(g.rstrip("/") + "/**").match(path)]

# ---------------------------------------------------------------- helpers

def sh(args, cwd=ROOT, check=True, timeout=600):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode:
        sys.exit(f"command failed: {' '.join(args)}\n{r.stdout}{r.stderr}")
    return r

def git(*args, cwd=ROOT, check=True):
    return sh(["git", *args], cwd=cwd, check=check).stdout.strip()

def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")

def out(obj):
    print(json.dumps(obj, indent=2))

def resolve(jid):
    ids = sorted(p.name for p in JOBS.iterdir() if (p / "status.json").exists()) if JOBS.exists() else []
    if jid in ids:
        return jid
    hits = [i for i in ids if i.startswith(jid) or jid in i]
    if len(hits) != 1:
        sys.exit(f"job '{jid}' {'ambiguous: ' + ', '.join(hits) if hits else 'not found'}")
    return hits[0]

def load(jid):
    return json.loads((JOBS / resolve(jid) / "status.json").read_text())

def save(s):
    s["updated"] = now()
    (JOBS / s["id"] / "status.json").write_text(json.dumps(s, indent=2) + "\n")

def log(jid, msg):
    with open(JOBS / jid / "log.md", "a") as f:
        f.write(f"- `{now()}` {msg}\n")

def worktree_path(s):
    return ROOT / s["worktree"]

# ---------------------------------------------------------------- jobs

def cmd_new(a):
    p = policy()
    text = a.text if a.text is not None else ("" if a.backlog or sys.stdin.isatty() else sys.stdin.read())
    bl = None
    if a.backlog:
        a.source = "backlog" if a.source == "text" else a.source
        bl = next((b for b in read_backlog() if b["id"] == a.backlog), None)
        if not bl:
            sys.exit(f"backlog item {a.backlog} not found")
        a.title = a.title or bl["title"]
        text = text or "\n".join(bl["body"]) or bl["title"]
    day = time.strftime("%Y%m%d")
    n = 1 + len(list(JOBS.glob(day + "-*")))
    slug = re.sub(r"[^a-z0-9]+", "-", a.title.lower()).strip("-")[:30].strip("-")
    jid = f"{day}-{n:03d}-{slug}"
    base = a.base or p["base_branch"]
    if a.parent:
        parent = load(a.parent)
        base = parent["branch"]
        parent["children"].append(jid)
        save(parent)
    s = {"id": jid, "title": a.title, "type": None, "size": None, "phase": "intake", "round": 0,
         "base": base, "branch": p["branch_prefix"] + jid, "worktree": f".worktrees/{jid}",
         "parent": parent["id"] if a.parent else None, "children": [], "reviewers": [], "reviews": {},
         "decision": None, "rule": None, "needs_human": None, "merge_commit": None, "checkpoint_tag": None,
         "allowed_protected": [], "source": {"kind": a.source, "ref": a.ref or (a.backlog or "")},
         "created": now(), "updated": now(), "history": []}
    (JOBS / jid / "reviews").mkdir(parents=True)
    (JOBS / jid / "results").mkdir()
    (JOBS / jid / "request.md").write_text(f"# {a.title}\n\nsource: {a.source} {s['source']['ref']}\n\n{text.strip()}\n")
    save(s)
    log(jid, "created (intake)")
    if bl:
        update_backlog(a.backlog, mark="~", job=jid)
    print(jid)

def cmd_phase(a):
    s, p = load(a.id), policy()
    to = a.to
    if to not in TRANSITIONS.get(s["phase"], []):
        sys.exit(f"illegal transition {s['phase']} -> {to}. allowed: {TRANSITIONS.get(s['phase'])}")
    if to == "rework":
        if not a.human:
            s["round"] += 1
        if s["round"] > int(p["max_rework_rounds"]):
            s["needs_human"] = {"reason": f"max rework rounds ({p['max_rework_rounds']}) exceeded. {a.note or ''}".strip(), "rule": "MAX-ROUNDS"}
            s["history"].append({"ts": now(), "from": s["phase"], "to": "needs-human", "note": s["needs_human"]["reason"]})
            s["phase"] = "needs-human"
            save(s); log(s["id"], "needs-human: " + s["needs_human"]["reason"])
            sys.exit("max rework rounds exceeded -> needs-human")
    if to in ("build", "review", "rework") and s["phase"] not in ACTIVE_PHASES:
        active = [j for j in all_jobs() if j["phase"] in ACTIVE_PHASES and j["id"] != s["id"]]
        if len(active) >= int(p["parallelism"]):
            sys.exit(f"no worktree slot free ({len(active)}/{p['parallelism']} active)")
    if to == "review":
        s["reviews"] = {}
    if to != "needs-human":
        s["needs_human"] = None
    if to == "needs-human":
        s["needs_human"] = {"reason": a.note or "unspecified", "rule": a.rule}
    s["history"].append({"ts": now(), "from": s["phase"], "to": to, "note": a.note or ""})
    s["phase"] = to
    save(s)
    log(s["id"], f"{s['history'][-1]['from']} -> {to}" + (f" ({a.note})" if a.note else "") + (f" [{a.rule}]" if a.rule else ""))
    print(f"{s['id']}: {to} (round {s['round']})")

def cmd_set(a):
    s = load(a.id)
    for kv in a.pairs:
        k, v = kv.split("=", 1)
        try:
            v = json.loads(v)
        except ValueError:
            pass
        d = s
        *path, last = k.split(".")
        for part in path:
            d = d.setdefault(part, {})
        d[last] = v
    save(s)
    log(s["id"], "set " + " ".join(a.pairs))

def cmd_status(a):
    if a.id:
        out(load(a.id)); return
    for s in all_jobs():
        rv = " ".join(f"{k[0]}:{v}" for k, v in s["reviews"].items())
        print(f"{s['id']:<46} {s['phase']:<18} r{s['round']} {rv}")

def all_jobs():
    return sorted((json.loads(p.read_text()) for p in JOBS.glob("*/status.json")), key=lambda s: s["created"])

def cmd_allow(a):
    s = load(a.id)
    s["allowed_protected"].append(a.glob); save(s)
    log(s["id"], f"human unlocked protected glob {a.glob}")

# ---------------------------------------------------------------- validation

ROLE_REVIEW = {"verdict": ("enum", "PASS", "FAIL", "N/A"), "blocking": "list", "nits": "list", "summary": "str"}
SCHEMAS = {
    "triage": {"type": ("enum", "bug", "feature", "chore"), "size": ("enum", "S", "M", "L"), "risk_flags": "list",
               "split": "bool", "subtasks": "list", "reviewers": "list", "summary": "str"},
    "investigator": {"affected_modules": "list", "constraints": "list", "open_questions": "list", "summary": "str"},
    "spec-writer": {"goal": "str", "scope": "list", "non_goals": "list", "acceptance_criteria": "list",
                    "affected_files": "list", "modules": "list", "risk_flags": "list"},
    "builder": {"status": ("enum", "DONE", "BLOCKED"), "commits": "list", "files_changed": "list", "tests": "dict", "notes": "str"},
    "reviewer-security": ROLE_REVIEW, "reviewer-code": ROLE_REVIEW, "reviewer-ux": ROLE_REVIEW, "reviewer-ui": ROLE_REVIEW,
    "approver": {"decision": ("enum", "MERGE", "ESCALATE"), "rule": "any", "reasons": "list"},
    "monitor": {"recommendation": ("enum", "KEEP", "ROLLBACK"), "checks": "list", "summary": "str"},
}
KINDS = {"list": list, "str": str, "bool": bool, "dict": dict}

def extract_json(text):
    blocks = re.findall(r"```json\s*(.*?)```", text, re.S)
    cands = blocks[-1:] + [text.strip(), text[text.find("{"):text.rfind("}") + 1]]
    for cand in cands:
        try:
            return json.loads(cand)
        except ValueError:
            continue
    sys.exit("INVALID: no parseable JSON result")

def check(role, o):
    errs = []
    for k, t in SCHEMAS[role].items():
        if k not in o:
            errs.append(f"missing '{k}'"); continue
        if t == "any":
            continue
        if isinstance(t, tuple):
            if o[k] not in t[1:]:
                errs.append(f"'{k}' must be one of {t[1:]}")
        elif not isinstance(o[k], KINDS[t]):
            errs.append(f"'{k}' must be {t}")
    if errs:
        return errs
    if role == "triage":
        if not set(o["reviewers"]) <= {"security", "code", "ux", "ui"}:
            errs.append("reviewers must be subset of security,code,ux,ui")
        for r in plist(policy()["reviewers.always"]):
            if r not in o["reviewers"]:
                errs.append(f"reviewers must include '{r}' (policy reviewers.always)")
        if o["split"] and (len(o["subtasks"]) < 2 or not all({"title", "description"} <= set(x) for x in o["subtasks"])):
            errs.append("split=true needs >=2 subtasks each with title+description")
    elif role == "spec-writer":
        if not o["acceptance_criteria"]: errs.append("acceptance_criteria empty")
        if not o["modules"]: errs.append("modules empty (needed for test command)")
    elif role == "builder":
        t = o["tests"]
        if o["status"] == "DONE" and not (t.get("result") == "PASS" and t.get("command") and t.get("evidence")):
            errs.append("DONE requires tests.{command,result:PASS,evidence}")
        if o["status"] == "BLOCKED" and not o.get("blocked_reason"):
            errs.append("BLOCKED requires blocked_reason")
    elif role.startswith("reviewer-"):
        if o["verdict"] == "FAIL" and not o["blocking"]: errs.append("FAIL requires >=1 blocking issue")
        if o["verdict"] != "FAIL" and o["blocking"]: errs.append("blocking issues present but verdict is not FAIL")
        if not all(isinstance(b, dict) and b.get("issue") for b in o["blocking"]): errs.append("each blocking item needs 'issue'")
    elif role == "approver":
        if o["decision"] == "ESCALATE" and o["rule"] not in rules():
            errs.append(f"ESCALATE must cite a rule ID from policy.md {sorted(rules())}; got {o['rule']!r}")
        if o["decision"] == "MERGE" and o["rule"] is not None:
            errs.append("MERGE must have rule=null")
    return errs

def cmd_validate(a):
    text = Path(a.file).read_text() if a.file else sys.stdin.read()
    o = extract_json(text)
    errs = check(a.role, o)
    if errs:
        print("INVALID:\n- " + "\n- ".join(errs)); sys.exit(1)
    print("OK")

# ---------------------------------------------------------------- git: preflight, worktrees, rules, merge

def diff_files(s):
    return git("diff", "--name-only", f"{s['base']}...{s['branch']}").splitlines()

def cmd_preflight(a):
    p, checks = policy(), []
    base = a.base or p["base_branch"]
    excl = [f":(exclude){x}" for x in plist(p["clean_tree.exclude"])]
    dirty = git("status", "--porcelain", "--", ".", *excl)
    checks.append({"check": "clean tree (excl. " + ",".join(plist(p["clean_tree.exclude"])) + ")", "ok": not dirty, "detail": dirty[:400]})
    cur = git("rev-parse", "--abbrev-ref", "HEAD")
    checks.append({"check": f"checked out on base '{base}'", "ok": cur == base, "detail": cur})
    mode = p["preflight.main_green"]
    if mode == "skip":
        checks.append({"check": "base green", "ok": True, "detail": "skipped by policy"})
    elif mode == "command":
        r = subprocess.run(p["preflight.main_cmd"], shell=True, cwd=ROOT)
        checks.append({"check": "base green (command)", "ok": r.returncode == 0, "detail": f"exit {r.returncode}"})
    else:
        r = sh(["gh", "run", "list", "--branch", base, "--workflow", p["ci_workflow"], "--limit", "1", "--json", "conclusion,status"], check=False) if shutil_which("gh") else None
        runs = json.loads(r.stdout or "[]") if r is not None and not r.returncode else []
        if not runs:
            checks.append({"check": "base green (ci)", "ok": bool(a.allow_unknown), "detail": "UNKNOWN: gh missing/failed or no CI run found for base" + (" - allowed by --allow-unknown" if a.allow_unknown else "")})
        else:
            checks.append({"check": "base green (ci)", "ok": runs[0].get("conclusion") == "success", "detail": json.dumps(runs[:1])})
    active = [j["id"] for j in all_jobs() if j["phase"] in ACTIVE_PHASES]
    checks.append({"check": "worktree slot free", "ok": len(active) < int(p["parallelism"]), "detail": f"{len(active)}/{p['parallelism']} active"})
    ok = all(c["ok"] for c in checks)
    out({"ok": ok, "checks": checks})
    sys.exit(0 if ok else 1)

def shutil_which(x):
    import shutil
    return shutil.which(x)

def cmd_worktree(a):
    s = load(a.id)
    wt = worktree_path(s)
    if a.action == "add":
        if wt.exists():
            sys.exit(f"{wt} exists; one job per worktree")
        git("worktree", "add", "-b", s["branch"], s["worktree"], s["base"])
        log(s["id"], f"worktree {s['worktree']} on {s['branch']} from {s['base']}")
    else:
        git("worktree", "remove", "--force", s["worktree"])
        log(s["id"], "worktree removed")
    print("ok")

def cmd_rules_hit(a):
    s, p = load(a.id), policy()
    files = diff_files(s)
    hits = {}
    for rid, (desc, gl) in rules().items():
        m = sorted({f for f in files if matches(f, gl)})
        if m:
            hits[rid] = m
    stat = git("diff", "--shortstat", f"{s['base']}...{s['branch']}")
    nums = [int(x) for x in re.findall(r"(\d+) (?:insertion|deletion)", stat)]
    if sum(nums) > int(p["escalate.max_diff_lines"]):
        hits["R-SIZE"] = [stat]
    prot = {f: matches(f, protected()) for f in files if matches(f, protected())}
    out({"files": files, "rules_hit": hits, "protected_touched": prot, "diff": stat})

def cmd_audit(a):
    """Detect cross-job writes using the activity log (best effort)."""
    s = load(a.id)
    findings = []
    for f in files_changed_protected(s):
        findings.append(f"protected path changed: {f}")
    seen = {}
    for lf in (RUNTIME / "activity").glob("*.jsonl"):
        for line in lf.read_text().splitlines():
            e = json.loads(line)
            m = re.match(r"\d{8}-\d{3}-[a-z0-9-]*[a-z0-9]", e.get("job") or "")
            if e.get("agent_id") and m:
                seen.setdefault(e["agent_id"], set()).add(m[0])
    for ag, jobs in seen.items():
        if len(jobs) > 1:
            findings.append(f"agent {ag} touched multiple jobs: {sorted(jobs)}")
    out({"job": s["id"], "ok": not findings, "findings": findings})

def files_changed_protected(s):
    unlocked = s["allowed_protected"]
    return [f for f in diff_files(s) if matches(f, protected()) and not matches(f, unlocked)]

def cmd_commit_state(a):
    git("add", "-A", "factory")
    if not git("diff", "--cached", "--name-only", "--", "factory"):
        print("nothing to commit"); return
    git("commit", "-m", f"chore(factory): {a.message}", "--", "factory")
    print("committed")

def cmd_merge(a):
    s = load(a.id)
    if policy().get("merge.mode") == "never":
        sys.exit(f"merge disabled by policy (merge.mode = never). Review and merge yourself:\n  git merge --no-ff {s['branch']}\n(worktree: {s['worktree']})")
    if s["phase"] not in ("awaiting-approval", "needs-human"):
        sys.exit(f"cannot merge from phase {s['phase']}")
    bad = files_changed_protected(s)
    if bad:
        sys.exit(f"protected paths changed without unlock: {bad}")
    child = s["base"].startswith(policy()["branch_prefix"])
    cwd = ROOT / ".worktrees" / s["base"][len(policy()["branch_prefix"]):] if child else ROOT
    if not child:
        if git("rev-parse", "--abbrev-ref", "HEAD") != s["base"]:
            sys.exit(f"main checkout must be on '{s['base']}'")
        tag = "factory/pre-" + s["id"]
        git("tag", tag); s["checkpoint_tag"] = tag
    if git("status", "--porcelain", "--", ".", ":(exclude)factory", cwd=cwd):
        sys.exit("target tree not clean")
    r = sh(["git", "merge", "--no-ff", "-m", a.message + f"\n\nFactory-Job: {s['id']}", s["branch"]], cwd=cwd, check=False)
    if r.returncode:
        sh(["git", "merge", "--abort"], cwd=cwd, check=False)
        sys.exit("merge conflict -> aborted. send job to needs-human.\n" + r.stdout)
    s["merge_commit"] = git("rev-parse", "HEAD", cwd=cwd)
    s["history"].append({"ts": now(), "from": s["phase"], "to": "merged", "note": s["merge_commit"]})
    s["phase"] = "merged"; s["needs_human"] = None
    save(s); log(s["id"], f"merged into {s['base']} @ {s['merge_commit'][:10]} (tag {s['checkpoint_tag']})")
    if (ROOT / s["worktree"]).exists():
        git("worktree", "remove", "--force", s["worktree"])
    if s["source"]["ref"].startswith("B-"):
        update_backlog(s["source"]["ref"], mark="x", job=s["id"])
    print(s["merge_commit"])

def cmd_rollback(a):
    s = load(a.id)
    if s["phase"] not in ("merged", "watch", "done") or not s["merge_commit"]:
        sys.exit("job has no merge to roll back")
    if git("rev-parse", "--abbrev-ref", "HEAD") != s["base"]:
        sys.exit(f"main checkout must be on '{s['base']}'")
    git("revert", "-m", "1", "--no-edit", s["merge_commit"])
    s["history"].append({"ts": now(), "from": s["phase"], "to": "rolled-back", "note": a.reason or ""})
    s["phase"] = "rolled-back"; save(s)
    log(s["id"], f"rolled back (revert of {s['merge_commit'][:10]}): {a.reason or ''}")
    print("reverted. create a follow-up job with `factory.py new`.")

# ---------------------------------------------------------------- backlog

BL = F / "backlog.md"
BL_RE = re.compile(r"^- \[([ ~x])\] (B-\d+) \| (P\d) \| (.+?)(?: \| src=(\S+))?(?: \| job=(\S+))?$")

def read_backlog():
    items = []
    for line in BL.read_text().splitlines():
        m = BL_RE.match(line)
        if m:
            items.append({"mark": m[1], "id": m[2], "prio": m[3], "title": m[4], "src": m[5], "job": m[6], "body": []})
        elif line.startswith("  ") and items:
            items[-1]["body"].append(line.strip())
    return items

def update_backlog(bid, mark, job):
    lines = BL.read_text().splitlines()
    for i, line in enumerate(lines):
        m = BL_RE.match(line)
        if m and m[2] == bid:
            lines[i] = f"- [{mark}] {m[2]} | {m[3]} | {m[4]}" + (f" | src={m[5]}" if m[5] else "") + f" | job={job}"
    BL.write_text("\n".join(lines) + "\n")

def cmd_backlog(a):
    items = [b for b in read_backlog() if b["mark"] == " "]
    items.sort(key=lambda b: (b["prio"], b["id"]))
    for b in items[: a.n]:
        print(f"{b['id']} {b['prio']} {b['title']}")

def cmd_intake(a):
    spec = importlib.util.spec_from_file_location(a.adapter, F / "adapters" / f"{a.adapter}.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    existing = {b["src"] for b in read_backlog() if b["src"]}
    nums = [int(b["id"][2:]) for b in read_backlog()] or [0]
    added = []
    for it in mod.fetch():
        if it["ref"] in existing:
            continue
        nums.append(nums[-1] + 1)
        bid = f"B-{nums[-1]:03d}"
        block = f"- [ ] {bid} | {it.get('priority', 'P2')} | {it['title']} | src={it['ref']}\n" + "".join(f"  {l}\n" for l in it["body"].splitlines())
        added.append(bid + " " + it["title"])
        if not a.dry:
            with open(BL, "a") as f:
                f.write(block)
    print("\n".join(added) or "nothing new")

def cmd_notify(a):
    s = load(a.id)
    if policy()["intake.writeback"] != "on":
        print("writeback off (policy intake.writeback)"); return
    kind = s["source"]["kind"]
    if not (F / "adapters" / f"{kind}.py").exists():
        return
    spec = importlib.util.spec_from_file_location(kind, F / "adapters" / f"{kind}.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.report(s, a.event, a.text or "")

# ---------------------------------------------------------------- dashboard

def board():
    jobs = all_jobs()
    for s in jobs:
        d = JOBS / s["id"]
        s["files"] = sorted(str(p.relative_to(d)) for p in d.rglob("*") if p.is_file())
    return jobs

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, body, ctype="application/json", code=200):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path)
        if u.path == "/":
            return self.send((F / "dashboard" / "index.html").read_bytes(), "text/html; charset=utf-8")
        if u.path == "/api/jobs":
            return self.send(json.dumps(board()))
        if u.path == "/api/file":
            q = parse_qs(u.query); jid = q.get("job", [""])[0]; rel = q.get("path", [""])[0]
            f = (JOBS / jid / rel).resolve()
            if (JOBS / jid).resolve() not in f.parents or not f.is_file():
                return self.send("not found", "text/plain", 404)
            return self.send(f.read_text(errors="replace"), "text/plain; charset=utf-8")
        if u.path == "/api/activity":
            f = RUNTIME / "activity" / (parse_qs(u.query).get("job", [""])[0] + ".jsonl")
            return self.send("\n".join(f.read_text().splitlines()[-60:]) if f.exists() else "", "text/plain; charset=utf-8")
        self.send("not found", "text/plain", 404)

def cmd_dashboard(a):
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"factory dashboard on http://127.0.0.1:{a.port}  (Ctrl-C to stop)", flush=True)
    srv.serve_forever()

# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    def add(name, fn, *args, **kw):
        p = sp.add_parser(name, **kw); p.set_defaults(fn=fn)
        for spec in args:
            names, opts = (spec if isinstance(spec, tuple) else (spec, {}))
            p.add_argument(*([names] if isinstance(names, str) else names), **opts)
        return p
    add("new", cmd_new, ("title", {"nargs": "?"}), ("--text", {}), ("--source", {"default": "text"}), ("--ref", {}),
        ("--parent", {}), ("--backlog", {}), ("--base", {}))
    add("phase", cmd_phase, "id", "to", ("--note", {}), ("--rule", {}), ("--human", {"action": "store_true"}))
    add("set", cmd_set, "id", ("pairs", {"nargs": "+"}))
    add("status", cmd_status, ("id", {"nargs": "?"}))
    add("allow", cmd_allow, "id", "glob")
    add("validate", cmd_validate, ("role", {"choices": sorted(SCHEMAS)}), ("file", {"nargs": "?"}))
    add("preflight", cmd_preflight, ("--base", {}), ("--allow-unknown", {"action": "store_true"}))
    add("worktree", cmd_worktree, ("action", {"choices": ["add", "remove"]}), "id")
    add("rules-hit", cmd_rules_hit, "id")
    add("audit", cmd_audit, "id")
    add("commit-state", cmd_commit_state, "message")
    add("merge", cmd_merge, "id", "message")
    add("rollback", cmd_rollback, "id", ("--reason", {}))
    add("backlog", cmd_backlog, ("n", {"nargs": "?", "type": int, "default": 1}))
    add("intake", cmd_intake, ("adapter", {"choices": ["github", "slack", "file"]}), ("--dry", {"action": "store_true"}))
    add("notify", cmd_notify, "id", "event", ("--text", {}))
    add("dashboard", cmd_dashboard, ("--port", {"type": int, "default": 8787}))
    a = ap.parse_args()
    a.fn(a)

if __name__ == "__main__":
    main()
