"""Intake adapter: markdown files dropped in factory/inbox/. First `# heading` = title, rest = body."""
import shutil
from pathlib import Path

INBOX = Path(__file__).resolve().parents[1] / "inbox"

def fetch():
    items = []
    for f in sorted(INBOX.glob("*.md")):
        lines = f.read_text().splitlines()
        title = lines[0].lstrip("# ").strip() if lines else f.stem
        items.append({"title": title, "body": "\n".join(lines[1:]).strip(), "ref": f"file:{f.name}", "priority": "P2"})
        done = INBOX / "processed"; done.mkdir(exist_ok=True)
        shutil.move(str(f), done / f.name)
    return items

def report(job, event, text=""):
    pass  # files have no write-back channel
