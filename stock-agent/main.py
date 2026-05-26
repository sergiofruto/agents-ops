"""
Silicon Intel — Orchestrator
=============================
Background threads:
  • intel_thread  — fetch Twitter + infosec + semicon signals  (every INTEL_SCAN_INTERVAL_MINUTES)
  • brief_thread  — generate Claude Sonnet daily brief         (every BRIEF_INTERVAL_HOURS)
  • web_thread    — Flask dashboard                            (localhost:5005)

The main thread runs the Rich terminal dashboard.
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
import reporter
import synthesizer
from intelligence.infosec import fetch_all_infosec
from intelligence.mining import fetch_all_mining
from intelligence.semicon import fetch_all_semicon
from intelligence.twitter import fetch_new_tweets
from web.app import run as run_web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger("main")

# ── Shared state ──────────────────────────────────────────────────────────────
_state_lock = threading.Lock()
_state: dict = {
    "last_intel_time":  None,
    "last_brief_time":  None,
    "next_intel_secs":  0,
    "next_brief_secs":  0,
    "tweet_count":      0,
    "infosec_count":    0,
    "semicon_count":    0,
    "latest_brief":     "Waiting for first brief generation…",
    "seen_tweet_ids":   set(),
}


def _update_state(**kwargs):
    with _state_lock:
        _state.update(kwargs)


def _read_state() -> dict:
    with _state_lock:
        return dict(_state)


# ── Intelligence scan ─────────────────────────────────────────────────────────

def _run_intel_scan():
    logger.info("=== INTEL SCAN STARTED ===")
    try:
        seen_ids = _state["seen_tweet_ids"]

        tweets  = fetch_new_tweets(seen_ids=seen_ids)
        infosec = fetch_all_infosec()
        semicon = fetch_all_semicon()
        mining  = fetch_all_mining()

        # Update seen IDs to avoid re-processing on next cycle
        new_seen = seen_ids | {t["id"] for t in tweets}

        _update_state(
            last_intel_time=datetime.utcnow().strftime("%H:%M:%S UTC"),
            tweet_count=len(tweets),
            infosec_count=len(infosec),
            semicon_count=len(semicon),
            mining_count=len(mining),
            seen_tweet_ids=new_seen,
        )

        # Store signals for use by brief generator
        database.store_intel_signals(tweets, infosec, semicon + mining)

        logger.info(
            "=== INTEL SCAN COMPLETE — tweets=%d infosec=%d semicon=%d mining=%d ===",
            len(tweets), len(infosec), len(semicon), len(mining),
        )

    except Exception:
        logger.exception("Intel scan failed")


# ── Brief generation ──────────────────────────────────────────────────────────

def _run_brief_generation():
    logger.info("--- BRIEF GENERATION ---")
    try:
        tweets, infosec, semicon = database.get_recent_signals()
        brief = synthesizer.generate_brief(tweets, infosec, semicon, force=True)
        _update_state(
            latest_brief=brief,
            last_brief_time=datetime.utcnow().strftime("%H:%M:%S UTC"),
        )
        logger.info("Brief generated (%d chars)", len(brief))
    except Exception:
        logger.exception("Brief generation failed")


# ── Scheduler helper ──────────────────────────────────────────────────────────

def _scheduler_thread(job_fn, interval_minutes: int, countdown_key: str):
    job_fn()
    sched = schedule.Scheduler()
    sched.every(interval_minutes).minutes.do(job_fn)
    while True:
        next_run = sched.next_run
        if next_run:
            remaining = max(0, int((next_run - datetime.now()).total_seconds()))
            _update_state(**{countdown_key: remaining})
        sched.run_pending()
        time.sleep(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    logger.info("Silicon Intel starting…")
    logger.info("Semicon watchlist: %s", config.SEMICON_WATCHLIST)
    database.init_db()

    intel_thread = threading.Thread(
        target=_scheduler_thread,
        args=(_run_intel_scan, config.INTEL_SCAN_INTERVAL_MINUTES, "next_intel_secs"),
        daemon=True, name="intel",
    )

    brief_thread = threading.Thread(
        target=_scheduler_thread,
        args=(_run_brief_generation, config.BRIEF_INTERVAL_HOURS * 60, "next_brief_secs"),
        daemon=True, name="brief",
    )

    web_thread = threading.Thread(
        target=run_web,
        kwargs={"host": config.WEB_HOST, "port": config.WEB_PORT},
        daemon=True, name="web",
    )

    intel_thread.start()
    brief_thread.start()
    web_thread.start()

    logger.info("All threads started. Web → http://localhost:%d", config.WEB_PORT)

    try:
        with reporter.make_live() as live:
            while True:
                state = _read_state()
                live.update(reporter.build_layout(state=state))
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down.")
        state = _read_state()
        print("\n\n=== SHUTDOWN SUMMARY ===")
        print(f"Last intel scan:  {state.get('last_intel_time', 'N/A')}")
        print(f"Last brief:       {state.get('last_brief_time', 'N/A')}")
        print(f"Tweets seen:      {len(state.get('seen_tweet_ids', set()))}")
        print("========================\n")


if __name__ == "__main__":
    main()
