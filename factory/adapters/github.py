"""Intake adapter: GitHub issues labelled `factory`. Needs the `gh` CLI, authenticated, run from this repo.

Interface (every adapter):
  fetch()  -> [{"title", "body", "ref" (unique, stable), "priority" (optional)}]
  report(job: dict (status.json), event: str, text: str)   # called by `factory.py notify`, only if policy intake.writeback = on
"""
import json, re, subprocess

LABEL = "factory"

def _gh(*args):
    try:
        r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise SystemExit("gh CLI not found: install and `gh auth login`, or use the file adapter")
    if r.returncode:
        raise SystemExit("gh failed: " + r.stderr.strip())
    return r.stdout

def fetch():
    issues = json.loads(_gh("issue", "list", "--label", LABEL, "--state", "open", "--json", "number,title,body", "--limit", "50"))
    return [{"title": i["title"], "body": i["body"] or "", "ref": f"github#{i['number']}", "priority": "P2"} for i in issues]

def report(job, event, text=""):
    m = re.match(r"github#(\d+)$", job["source"]["ref"])
    if not m:
        return
    n, body = m[1], {
        "planned": f"Factory job `{job['id']}` has a spec ready.",
        "needs-human": f"Factory job `{job['id']}` needs a human: {job['needs_human']}",
        "merged": f"Factory job `{job['id']}` merged into `{job['base']}` at {job['merge_commit']}.",
    }.get(event, text or event)
    _gh("issue", "comment", n, "--body", body)
    if event == "merged":
        _gh("issue", "close", n, "--reason", "completed")
