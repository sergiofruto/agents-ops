"""Which jobs are due, run one at a time. Missed jobs (sleep, Mac off) run once on startup."""
import faulthandler
import logging
import sqlite3
import sys
from datetime import datetime, timedelta
from typing import Callable

import config

logger = logging.getLogger("scheduler")

STATUS_EVERY = timedelta(minutes=5)
SCAN_EVERY = timedelta(days=7)
DIGEST_HOUR = 7
ORDER = ("status", "digest", "scan")
# A failed job waits this long before it is tried again
RETRY_AFTER = {"status": STATUS_EVERY, "digest": timedelta(minutes=30), "scan": timedelta(hours=1)}
# A job still running after this long is hung: dump every thread's stack to the log and exit,
# so launchd (KeepAlive SuccessfulExit=false) restarts the agent
WATCHDOG_SECONDS = {"status": 180, "digest": 1800, "scan": 1800}


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


def _last(conn, table: str, job: str) -> datetime | None:
    row = conn.execute(f"SELECT * FROM {table} WHERE job=?", (job,)).fetchone()
    return datetime.fromisoformat(row[1]) if row else None


_TIME_COLUMN = {"job_runs": "last_run", "job_attempts": "attempted_at"}


def _record(conn, table: str, job: str, now: datetime) -> None:
    col = _TIME_COLUMN[table]
    conn.execute(f"INSERT INTO {table} VALUES (?, ?) ON CONFLICT(job) DO UPDATE SET {col}=excluded.{col}",
                 (job, now.isoformat()))
    conn.commit()


def _log_stream():
    for h in logging.getLogger().handlers:
        if isinstance(h, logging.FileHandler):
            return h.stream
    return sys.stderr


def run_due_jobs(conn: sqlite3.Connection, now: datetime) -> list[str]:
    ran = []
    for job in ORDER:
        last_ok, last_try = _last(conn, "job_runs", job), _last(conn, "job_attempts", job)
        if not due(job, last_ok, now):
            continue
        failed_recently = last_try and (last_ok is None or last_try > last_ok) and now - last_try < RETRY_AFTER[job]
        if failed_recently:
            continue
        logger.info("job %s starting", job)
        _record(conn, "job_attempts", job, now)
        faulthandler.dump_traceback_later(WATCHDOG_SECONDS[job], exit=True, file=_log_stream())
        try:
            JOBS[job](conn)
            _record(conn, "job_runs", job, now)
        except Exception:
            conn.rollback()
            logger.exception("job %s failed, retrying in %s", job, RETRY_AFTER[job])
        finally:
            faulthandler.cancel_dump_traceback_later()
        ran.append(job)
    return ran
