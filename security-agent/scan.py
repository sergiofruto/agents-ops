"""Run the Mac checks one at a time and store what they found."""
import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

import config
from checks.basics import check_basics
from checks.performance import check_performance
from checks.persistence import check_persistence
from checks.ports import check_ports
from checks.secrets import scan_secrets
from models import SEVERITY_ORDER, CheckResult

logger = logging.getLogger("scan")

DEFAULT_CHECKS: list[tuple[str, Callable[[], CheckResult]]] = [
    ("performance", check_performance),
    ("ports", check_ports),
    ("secrets", lambda: scan_secrets(config.PROJECTS_ROOT, Path.home())),
    ("basics", check_basics),
    ("malware", check_persistence),
]

SCAN_LOCK = threading.Lock()


class ScanInProgress(Exception):
    pass


def _previous_keys(conn: sqlite3.Connection, scan_id: int) -> set[str] | None:
    prev = conn.execute("SELECT id FROM scans WHERE status='done' AND id < ? ORDER BY id DESC LIMIT 1",
                        (scan_id,)).fetchone()
    if not prev:
        return None
    return {r[0] for r in conn.execute("SELECT key FROM findings WHERE scan_id=?", (prev[0],))}


def run_scan(conn: sqlite3.Connection, checks=DEFAULT_CHECKS, *, now=datetime.now,
             on_done: Callable[[int], None] | None = None) -> int:
    if not SCAN_LOCK.acquire(blocking=False):
        raise ScanInProgress()
    try:
        cur = conn.execute("INSERT INTO scans (started_at, status) VALUES (?, 'running')", (now().isoformat(),))
        scan_id = cur.lastrowid
        conn.commit()
        previous = _previous_keys(conn, scan_id)
        for name, check in checks:
            try:
                result = check()
            except Exception as exc:
                logger.warning("check %s failed: %s", name, type(exc).__name__)
                result = CheckResult(name, skipped=[f"{name}: couldn't check ({type(exc).__name__})"])
            for f in result.findings:
                conn.execute(
                    "INSERT INTO findings VALUES (?,?,?,?,?,?,?,?,?)",
                    (scan_id, f.key, f.category, f.severity, f.title, f.evidence, f.explanation,
                     json.dumps(f.fix), int(previous is None or f.key not in previous)))
            conn.execute("INSERT INTO scan_checks VALUES (?,?,?,?)",
                         (scan_id, result.category, json.dumps(result.passed), json.dumps(result.skipped)))
            conn.commit()
        conn.execute("UPDATE scans SET status='done', finished_at=? WHERE id=?", (now().isoformat(), scan_id))
        conn.commit()
    finally:
        SCAN_LOCK.release()
    if on_done:
        try:
            on_done(scan_id)
        except Exception:
            logger.exception("post-scan step failed")
    return scan_id


def latest_scan(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute("SELECT * FROM scans WHERE status='done' ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return None
    findings = []
    for r in conn.execute("SELECT * FROM findings WHERE scan_id=?", (row["id"],)):
        f = dict(r)
        f["fix"] = json.loads(f.pop("fix_json"))
        findings.append(f)
    findings.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], f["category"], f["key"]))
    passed, skipped = [], []
    for r in conn.execute("SELECT passed_json, skipped_json FROM scan_checks WHERE scan_id=?", (row["id"],)):
        passed += json.loads(r[0])
        skipped += json.loads(r[1])
    counts = {s: 0 for s in SEVERITY_ORDER}
    for f in findings:
        counts[f["severity"]] += 1
    return {**dict(row), "findings": findings, "passed": passed, "skipped": skipped, "counts": counts}
