"""What this Mac and Sergio's projects use, so news that touches them floats to the top."""
import json
import os
import re
from pathlib import Path

import config
from checks import shell

ALIASES = {"next": "next.js", "node": "node.js"}
# Names that are also everyday words in security news ("edge devices", "a black market", "the drive")
STOP = {"rich", "schedule", "requests", "ephem", "dotenv", "types", "edge", "drive", "docs", "sheets", "slides",
        "black", "express", "cursor", "affinity", "autopilot", "fractional", "cors", "husky", "claude", "excel"}
KEEP_SHORT = {"aws"}
VENDOR_PREFIXES = ("google ", "microsoft ", "adobe ", "mozilla ", "apple ")
MAX_DEPTH = 3


def _deps(path: Path) -> set[str]:
    try:
        if path.name == "package.json":
            data = json.loads(path.read_text())
            return set(data.get("dependencies", {})) | set(data.get("devDependencies", {}))
        names = set()
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "-")):
                names.add(re.split(r"[<>=!~\[;\s]", line)[0])
        return names
    except (OSError, ValueError):
        return set()


def collect_inventory(projects_root: Path, apps_dir: Path = Path("/Applications"), run=shell.run) -> set[str]:
    terms = {"macos", "safari"} | {p["name"].lower() for p in config.PROVIDERS}
    if apps_dir.is_dir():
        for app in apps_dir.glob("*.app"):
            name = app.stem.lower()
            terms.add(name)
            for prefix in VENDOR_PREFIXES:
                if name.startswith(prefix):
                    terms.add(name[len(prefix):])
    if projects_root.is_dir():
        base = len(projects_root.parts)
        for dirpath, dirnames, filenames in os.walk(projects_root):
            depth = len(Path(dirpath).parts) - base
            dirnames[:] = [] if depth >= MAX_DEPTH else [d for d in dirnames if d not in ("node_modules", ".git", ".next", "venv", ".venv")]
            for f in ("package.json", "requirements.txt"):
                if f in filenames:
                    terms |= {d.lower() for d in _deps(Path(dirpath) / f)}
    terms = {ALIASES.get(t, t) for t in terms}
    return {t for t in terms if t and t not in STOP and not t.startswith((".", "git+", "-"))
            and (len(t) >= 4 or t in KEEP_SHORT)}


def affects(text: str, terms: set[str]) -> list[str]:
    low = text.lower()
    return sorted(t for t in terms if re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", low))
