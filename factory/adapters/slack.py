"""Intake adapter: Slack. Contract, not a bot.

IN : something you run (Slack Workflow Builder webhook step, Zapier, a Slack MCP, a 20-line receiver) writes one JSON file per message to
     factory/inbox/slack/<ts>.json  with  {"text": "...", "user": "U123", "channel": "C123", "ts": "1700000000.000100", "permalink": "https://..."}.
     First line of `text` = title; the rest = body.
OUT: if env SLACK_WEBHOOK_URL (an Incoming Webhook) is set and policy intake.writeback = on, `report` posts status lines there.
"""
import json, os, shutil, urllib.request
from pathlib import Path

INBOX = Path(__file__).resolve().parents[1] / "inbox" / "slack"

def fetch():
    items = []
    for f in sorted(INBOX.glob("*.json")):
        m = json.loads(f.read_text())
        first, _, rest = m["text"].partition("\n")
        items.append({"title": first.strip(), "body": (rest + "\n" + m.get("permalink", "")).strip(), "ref": f"slack:{m['ts']}", "priority": "P2"})
        (INBOX / "processed").mkdir(exist_ok=True)
        shutil.move(str(f), INBOX / "processed" / f.name)
    return items

def report(job, event, text=""):
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        return
    msg = {"text": f"factory `{job['id']}` {event}" + (f": {job['needs_human']['reason']}" if event == "needs-human" and job.get("needs_human") else "")}
    urllib.request.urlopen(urllib.request.Request(url, json.dumps(msg).encode(), {"Content-Type": "application/json"}), timeout=15)
