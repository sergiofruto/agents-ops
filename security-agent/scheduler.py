"""Which jobs are due, run one at a time. Missed jobs (sleep, Mac off) run once on startup."""
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Callable

import config

logger = logging.getLogger("scheduler")

STATUS_EVERY = timedelta(minutes=5)
SCAN_EVERY = timedelta(days=7)
DIGEST_HOUR = 7
ORDER = ("status", "digest", "scan")


def due(job: str, last_run: datetime | None, now: datetime) -> bool:
    if job == "digest":
        return now.hour >= DIGEST_HOUR and (last_run is None or last_run.date() < now.date())
    every = STATUS_EVERY if job == "status" else SCAN_EVERY
    return last_run is None or now - last_run >= every


def _status(conn):
    from status.service import check_all
    check_all(conn)


def _digest(conn):
    from analyst import Claude
    from digest.build import build_digest
    from digest.inventory import collect_inventory
    from digest.sources import fetch_all
    build_digest(conn, fetch_all(conn), Claude.from_config(conn), collect_inventory(config.PROJECTS_ROOT))


def _scan(conn):
    from analyst import Claude, scan_overview
    from scan import ScanInProgress, run_scan
    try:
        run_scan(conn, on_done=lambda sid: scan_overview(conn, Claude.from_config(conn), sid))
    except ScanInProgress:
        logger.info("weekly scan skipped: a scan is already running")


JOBS: dict[str, Callable[[sqlite3.Connection], None]] = {"status": _status, "digest": _digest, "scan": _scan}


def _last_run(conn, job: str) -> datetime | None:
    row = conn.execute("SELECT last_run FROM job_runs WHERE job=?", (job,)).fetchone()
    return datetime.fromisoformat(row[0]) if row else None


def run_due_jobs(conn: sqlite3.Connection, now: datetime) -> list[str]:
    ran = []
    for job in ORDER:
        if not due(job, _last_run(conn, job), now):
            continue
        logger.info("job %s starting", job)
        try:
            JOBS[job](conn)
        except Exception:
            logger.exception("job %s failed", job)
        # Recorded even after a failure, so a broken job waits for its next slot instead of looping
        conn.execute("INSERT INTO job_runs VALUES (?, ?) ON CONFLICT(job) DO UPDATE SET last_run=excluded.last_run",
                     (job, now.isoformat()))
        conn.commit()
        ran.append(job)
    return ran
