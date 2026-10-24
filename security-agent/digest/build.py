"""Turn fetched items into the day's digest. Claude groups and writes; code decides what's true."""
import json
import logging
import re
import sqlite3
from datetime import datetime

import config
from analyst import Claude, text_of
from digest.inventory import affects
from digest.sources import Item
from digest.validate import confirmable, pre_cluster

logger = logging.getLogger("digest.build")

SYSTEM = """You prepare a daily security digest for one software engineer.
You get clusters of news items as JSON. Merge clusters that are about the same event, and write
one entry per event. Use only the information in the items: no outside facts, no guessing.
Tone: calm and specific. No hype words (no "massive", "critical threat", "urgent", "alarming").
Never use em dashes.
Reply with JSON only, no other text:
{"groups": [{"item_ids": ["..."], "title": "...", "summary": "2-3 sentences: what happened",
"who": "who is affected", "action": "what to do, or No action needed"}]}"""


def _parse(text: str) -> list[dict] | None:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        groups = json.loads(text)["groups"]
    except (ValueError, KeyError, TypeError):
        return None
    return groups if isinstance(groups, list) else None


def _ask(claude: Claude, clusters: list[list[Item]]) -> list[dict] | None:
    payload = [{"cluster_id": n, "items": [{"id": i.id, "source": i.source, "title": i.title, "text": i.text[:600]}
                                           for i in cl]} for n, cl in enumerate(clusters)]
    resp = claude.ask("digest", model=config.DIGEST_MODEL, system=SYSTEM, max_tokens=8000,
                      messages=[{"role": "user", "content": json.dumps(payload)}])
    return _parse(text_of(resp)) if resp else None


def _plain_entry(items: list[Item]) -> dict:
    lead = next((i for i in items if i.kind == "primary"), items[0])
    return {"items": items, "title": lead.title, "summary": None, "who": None, "action": None}


def build_digest(conn: sqlite3.Connection, items: list[Item], claude: Claude | None, terms: set[str],
                 *, now: datetime | None = None) -> int:
    now = now or datetime.now()
    clusters = pre_cluster(items)
    groups = _ask(claude, clusters) if (claude and clusters) else None
    entries: list[dict] = []
    used: set[str] = set()
    if groups is not None:
        by_id = {i.id: i for i in items}
        for g in groups:
            if not isinstance(g, dict):
                continue
            members = []
            for iid in g.get("item_ids") or []:
                if iid in by_id and iid not in used:
                    used.add(iid)
                    members.append(by_id[iid])
            if members:
                entries.append({"items": members, "title": str(g.get("title") or members[0].title),
                                "summary": g.get("summary"), "who": g.get("who"), "action": g.get("action")})
    for cl in clusters:
        rest = [i for i in cl if i.id not in used]
        if rest:
            entries.append(_plain_entry(rest))

    kept = []
    for e in entries:
        if not confirmable(e["items"]):
            continue
        e["affects"] = affects(" ".join(f"{i.title} {i.text}" for i in e["items"]), terms)
        e["kev"] = any(i.kev for i in e["items"])
        kept.append(e)
    kept.sort(key=lambda e: (not e["affects"], not e["kev"], -len(e["items"])))
    kept = kept[:config.DIGEST_MAX_ENTRIES]

    cur = conn.execute("INSERT INTO digests (day, built_at, used_ai) VALUES (?,?,?)",
                       (now.date().isoformat(), now.isoformat(), int(groups is not None)))
    did = cur.lastrowid
    for rank, e in enumerate(kept):
        sources = [{"source": i.source, "url": i.url, "title": i.title} for i in e["items"]]
        conn.execute("INSERT INTO digest_entries VALUES (?,?,?,?,?,?,?,?,?)",
                     (did, rank, e["title"], e["summary"], e["who"], e["action"],
                      json.dumps(e["affects"]), json.dumps(sources), int(e["kev"])))
    conn.executemany("INSERT OR IGNORE INTO seen_items VALUES (?, ?)", [(i.url, now.isoformat()) for i in items])
    conn.commit()
    return did


def latest_digest(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute("SELECT * FROM digests ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return None
    entries = []
    for r in conn.execute("SELECT * FROM digest_entries WHERE digest_id=? ORDER BY rank", (row["id"],)):
        e = dict(r)
        e["affects"] = json.loads(e.pop("affects_json"))
        e["sources"] = json.loads(e.pop("sources_json"))
        entries.append(e)
    return {**dict(row), "entries": entries}
