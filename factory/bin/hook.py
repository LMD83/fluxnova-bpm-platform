#!/usr/bin/env python3
"""Claude Code hooks for the factory. Inert unless factory/runtime/ACTIVE exists (the foreman creates it).

  hook.py guard   PreToolUse  : block edits outside the allowed zones; block risky git from subagents
  hook.py log     PostToolUse : append tool activity to factory/runtime/activity/<job>.jsonl

Zones (agent_id present = a subagent; absent = the foreman / main session):
  foreman   -> factory/** only
  subagent  -> factory/jobs/<id>/**  and  .worktrees/<id>/** (minus protected paths)
Nothing may touch the main checkout's source tree while the factory is active.
"""
import json, os, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import factory as fx  # noqa: E402

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SUBAGENT_GIT_DENY = re.compile(r"\bgit\s+(push|merge(?!-base)|rebase|checkout|switch|reset\s+--hard|tag|worktree|branch\s+-[dD]|clean)\b")

def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": "factory: " + reason}}))
    sys.exit(0)

def job_of(path_or_cwd):
    m = re.search(r"/(?:\.worktrees|factory/jobs)/(\d{8}-\d{3}-[a-z0-9-]*[a-z0-9])", str(path_or_cwd))
    return m.group(1) if m else None

def guard(d):
    tool, ti = d.get("tool_name"), d.get("tool_input", {})
    sub = bool(d.get("agent_id"))
    if tool == "Bash":
        if sub and SUBAGENT_GIT_DENY.search(ti.get("command", "")):
            deny("subagents may not run push/merge/rebase/checkout/switch/reset --hard/tag/worktree/clean. The foreman owns git topology.")
        return
    if tool not in EDIT_TOOLS:
        return
    raw = ti.get("file_path") or ti.get("notebook_path") or ""
    p = Path(raw).resolve()
    try:
        rel = p.relative_to(fx.ROOT)
    except ValueError:
        deny(f"{p} is outside the repository")
    parts = rel.parts
    if parts[:2] == ("factory", "jobs") or parts[:2] == ("factory", "runtime"):
        return
    if parts[:1] == ("factory",):
        if sub:
            deny("subagents may not edit factory state outside factory/jobs/<id>/")
        if rel.as_posix() in ("factory/policy.md",):
            deny("policy.md is human-edited only")
        return
    if parts[:1] == (".worktrees",) and len(parts) > 2:
        if not sub:
            deny("the foreman does not edit job worktrees; spawn the builder")
        if d.get("agent_type") not in (None, "builder"):
            deny(f"only the builder may edit a worktree; {d.get('agent_type')} is read-only on source")
        jid = parts[1]
        inner = Path(*parts[2:]).as_posix()
        try:
            unlocked = fx.load(jid)["allowed_protected"]
        except SystemExit:
            unlocked = []
        hit = fx.matches(inner, fx.protected())
        if hit and not fx.matches(inner, unlocked):
            deny(f"protected path ({hit[0]}). Return BLOCKED; a human can run /factory allow {jid} '{hit[0]}'.")
        cwd_job = job_of(d.get("cwd", ""))
        if cwd_job and cwd_job != jid:
            deny(f"cwd is job {cwd_job} but edit targets job {jid}")
        return
    deny(f"edit to {rel.as_posix()} in the main checkout is blocked while the factory is active. Work happens in .worktrees/<job>/.")

def log(d):
    ti = d.get("tool_input", {})
    path = ti.get("file_path") or ti.get("notebook_path")
    job = job_of(path or "") or job_of(d.get("cwd", "")) or (job_of(ti.get("command", "")))
    entry = {"ts": time.strftime("%H:%M:%S"), "agent_id": d.get("agent_id"), "agent_type": d.get("agent_type"),
             "tool": d.get("tool_name"), "path": path, "cmd": (ti.get("command") or "")[:160] or None, "job": job}
    f = fx.RUNTIME / "activity" / f"{job or '_unassigned'}.jsonl"
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a") as fh:
        fh.write(json.dumps(entry) + "\n")

def main():
    if not (fx.RUNTIME / "ACTIVE").exists():
        return
    d = json.load(sys.stdin)
    (guard if sys.argv[1] == "guard" else log)(d)

if __name__ == "__main__":
    main()
