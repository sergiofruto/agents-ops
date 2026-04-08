"""
The Analyst — Orchestrator
==========================
"Nothing rests; everything moves; everything vibrates." — The Kybalion

Three background threads:
  • intel_thread  — OSINT + infosec scans  (every INTEL_INTERVAL_MINUTES)
  • cosmic_thread — sky calculations        (every COSMIC_INTERVAL_MINUTES)
  • brief_thread  — synthesis + publish     (every BRIEF_INTERVAL_MINUTES)

Main thread runs the Rich terminal dashboard.
Press Ctrl-C to exit.
"""

import logging
import sys
import threading
import time
from datetime import datetime

import schedule

import config
import database
from intelligence import infosec, osint, cosmic
import synthesis
import reporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    handlers=[
        logging.FileHandler("analyst.log"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger("main")

# ---------------------------------------------------------------------------
# Shared countdown state
# ---------------------------------------------------------------------------
_lock            = threading.Lock()
_next_intel_secs:  int = 0
_next_cosmic_secs: int = 0
_next_brief_secs:  int = 0


def _set(**kwargs):
    global _next_intel_secs, _next_cosmic_secs, _next_brief_secs
    with _lock:
        if "intel"  in kwargs: _next_intel_secs  = kwargs["intel"]
        if "cosmic" in kwargs: _next_cosmic_secs = kwargs["cosmic"]
        if "brief"  in kwargs: _next_brief_secs  = kwargs["brief"]


def _get() -> tuple[int, int, int]:
    with _lock:
        return _next_intel_secs, _next_cosmic_secs, _next_brief_secs


# ---------------------------------------------------------------------------
# Job functions
# ---------------------------------------------------------------------------

def _run_intel():
    logger.info("=== INTEL CYCLE STARTED ===")
    try:
        osint.run_osint_scan()
        infosec.run_infosec_scan()
    except Exception as exc:
        logger.exception("Intel cycle failed: %s", exc)
    logger.info("=== INTEL CYCLE DONE ===")


def _run_cosmic():
    try:
        cosmic.run_cosmic_scan()
    except Exception as exc:
        logger.exception("Cosmic scan failed: %s", exc)


def _run_brief():
    try:
        brief_id = synthesis.synthesise()
        if brief_id:
            logger.info("Brief #%d published", brief_id)
    except Exception as exc:
        logger.exception("Brief synthesis failed: %s", exc)


# ---------------------------------------------------------------------------
# Generic scheduler thread
# ---------------------------------------------------------------------------

def _scheduler_thread(job_fn, interval_minutes: int, countdown_key: str):
    job_fn()
    sched = schedule.Scheduler()
    sched.every(interval_minutes).minutes.do(job_fn)

    while True:
        next_run = sched.next_run
        if next_run:
            remaining = max(0, int((next_run - datetime.now()).total_seconds()))
            _set(**{countdown_key: remaining})
        sched.run_pending()
        time.sleep(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("The Analyst starting…")
    database.init_db()
    logger.info("Database initialised at %s", config.DB_PATH)

    threads = [
        threading.Thread(
            target=_scheduler_thread,
            args=(_run_intel, config.INTEL_INTERVAL_MINUTES, "intel"),
            daemon=True, name="intel",
        ),
        threading.Thread(
            target=_scheduler_thread,
            args=(_run_cosmic, config.COSMIC_INTERVAL_MINUTES, "cosmic"),
            daemon=True, name="cosmic",
        ),
        threading.Thread(
            target=_scheduler_thread,
            args=(_run_brief, config.BRIEF_INTERVAL_MINUTES, "brief"),
            daemon=True, name="brief",
        ),
    ]

    for t in threads:
        t.start()

    logger.info("All threads started. Logs → analyst.log")

    try:
        with reporter.make_live() as live:
            while True:
                intel, cos, brief = _get()
                live.update(reporter.build_layout(
                    next_intel_secs=intel,
                    next_cosmic_secs=cos,
                    next_brief_secs=brief,
                ))
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("The Analyst going dark. Goodbye.")
        print("\nThe Analyst stopped.")


if __name__ == "__main__":
    main()
