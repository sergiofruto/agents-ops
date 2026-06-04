"""
Polymarket Betting Agent — Orchestrator
========================================
Starts three background threads:
  • scan_thread  — fetch markets, score, simulate bets  (every SCAN_INTERVAL_MINUTES)
  • track_thread — poll open bets for resolution         (every TRACK_INTERVAL_MINUTES)
  • web_thread   — Flask dashboard                       (localhost:5000)

The main thread runs the Rich terminal dashboard (auto-refresh every second).
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
import fetcher
import analyzer
import simulator
import tracker
import reporter
from web.app import run as run_web

# ---------------------------------------------------------------------------
# Logging — pipe to file so it doesn't disturb the Rich live display
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger("main")

# ---------------------------------------------------------------------------
# Shared state (write from scan/track threads, read from dashboard)
# ---------------------------------------------------------------------------
_state_lock     = threading.Lock()
_last_scan_time: str | None = None
_next_scan_secs: int  = 0
_next_track_secs: int = 0


def _update_state(**kwargs):
    global _last_scan_time, _next_scan_secs, _next_track_secs
    with _state_lock:
        if "last_scan_time" in kwargs:
            _last_scan_time = kwargs["last_scan_time"]
        if "next_scan_secs" in kwargs:
            _next_scan_secs = kwargs["next_scan_secs"]
        if "next_track_secs" in kwargs:
            _next_track_secs = kwargs["next_track_secs"]


def _read_state() -> tuple[str | None, int, int]:
    with _state_lock:
        return _last_scan_time, _next_scan_secs, _next_track_secs


# ---------------------------------------------------------------------------
# Scan loop
# ---------------------------------------------------------------------------
def _run_btc_scan() -> None:
    """Read-only BTC scanner cycle: find, rank, snapshot. No bets placed."""
    import btc_scanner
    from pathlib import Path
    try:
        candidates = btc_scanner.find_btc_threshold_candidates(limit=config.BTC_TOP_N)
        out = Path(__file__).parent / "btc_candidates.json"
        btc_scanner.snapshot(candidates, out)
        top = candidates[0] if candidates else None
        logger.info(
            "BTC scan: %d candidates | top: %s | edge=%.1f%%",
            len(candidates),
            (top.question[:50] if top else "—"),
            ((top.edge or 0) * 100 if top else 0.0),
        )
    except Exception as exc:
        logger.error("BTC scan failed: %s", exc)


def _run_scan():
    logger.info("=== SCAN STARTED ===")
    try:
        markets = fetcher.fetch_active_markets(limit=500)
        logger.info("Fetched %d markets from Gamma API", len(markets))

        # Save price snapshots for stability scoring
        for market in markets:
            mkt_id = market.get("id", "")
            prices = []
            try:
                import json
                raw = market.get("outcomePrices", [])
                if isinstance(raw, str):
                    raw = json.loads(raw)
                prices = [float(p) for p in raw]
            except Exception:
                pass

            token_ids = []
            try:
                import json
                raw = market.get("clobTokenIds", [])
                if isinstance(raw, str):
                    raw = json.loads(raw)
                token_ids = [str(t) for t in raw]
            except Exception:
                pass

            for i, price in enumerate(prices):
                tid = token_ids[i] if i < len(token_ids) else ""
                database.save_price_snapshot(mkt_id, tid, price)

        # Score and filter
        candidates = analyzer.score_markets(markets)
        logger.info("Found %d candidate(s) above score threshold", len(candidates))

        placed = 0
        for candidate in candidates:
            if placed >= config.MAX_BETS_PER_SCAN:
                break
            # Enforce portfolio exposure limit before each bet
            live_bankroll = database.get_live_bankroll(config.VIRTUAL_BANKROLL)
            open_exposure = database.get_open_exposure()
            max_exposure  = (live_bankroll + open_exposure) * config.MAX_OPEN_EXPOSURE_PCT
            if open_exposure >= max_exposure:
                logger.info(
                    "Exposure limit reached ($%.0f / $%.0f max) — skipping remaining candidates",
                    open_exposure, max_exposure,
                )
                break
            if simulator.place_bet(candidate):
                placed += 1

        mode = "live" if not config.DRY_RUN else "dry-run"
        logger.info("Placed %d %s bet(s) this scan", placed, mode)

    except Exception as exc:
        logger.exception("Scan failed: %s", exc)

    _update_state(last_scan_time=datetime.utcnow().strftime("%H:%M:%S UTC"))
    logger.info("=== SCAN COMPLETE ===")


# ---------------------------------------------------------------------------
# Track loop
# ---------------------------------------------------------------------------
def _run_track():
    logger.info("--- TRACK CHECK ---")
    try:
        tracker.check_resolutions()
    except Exception as exc:
        logger.exception("Track failed: %s", exc)


# ---------------------------------------------------------------------------
# Scheduler thread helpers
# ---------------------------------------------------------------------------
def _scheduler_thread(job_fn, interval_minutes: int, countdown_key: str):
    """Run job_fn immediately, then on a fixed schedule."""
    job_fn()
    schedule.every(interval_minutes).minutes.do(job_fn)

    while True:
        next_run = schedule.next_run()
        if next_run:
            remaining = max(0, int((next_run - datetime.now()).total_seconds()))
            _update_state(**{countdown_key: remaining})
        schedule.run_pending()
        time.sleep(1)


# ---------------------------------------------------------------------------
# Live-mode credential validation — runs before threads start
# ---------------------------------------------------------------------------
def _validate_live_mode() -> None:
    """
    Verify all CLOB credentials are present and accepted by the exchange.
    Calls sys.exit(1) with a clear message on any failure so the agent
    never starts threads with broken credentials.
    """
    required = {
        "POLY_PRIVATE_KEY":    config.POLY_PRIVATE_KEY,
        "POLY_API_KEY":        config.POLY_API_KEY,
        "POLY_API_SECRET":     config.POLY_API_SECRET,
        "POLY_API_PASSPHRASE": config.POLY_API_PASSPHRASE,
    }
    missing = [name for name, val in required.items() if not val]
    if missing:
        logger.error(
            "LIVE MODE — missing credentials: %s\n"
            "  Run `python live_setup.py` to generate API keys, "
            "then set them in .env.",
            ", ".join(missing),
        )
        sys.exit(1)

    logger.info("LIVE MODE — verifying CLOB credentials…")
    try:
        from simulator import _get_clob_client
        client = _get_clob_client()
        # get_api_keys() requires valid L2 auth end-to-end:
        # private key → signature → API key/secret/passphrase validated server-side.
        client.get_api_keys()
        logger.info("LIVE MODE — credentials OK ✓")
    except Exception as exc:
        logger.error(
            "LIVE MODE — credential check failed: %s\n"
            "  Check POLY_PRIVATE_KEY / POLY_API_KEY / POLY_API_SECRET / "
            "POLY_API_PASSPHRASE in .env.\n"
            "  Re-run `python live_setup.py` if keys have expired.",
            exc,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Polymarket Agent")
    parser.add_argument(
        "--btc-scan",
        action="store_true",
        help="Run the BTC threshold scanner once (read-only), print + snapshot, exit.",
    )
    args = parser.parse_args()

    if args.btc_scan:
        import btc_scanner
        from pathlib import Path
        logger.info("Running BTC threshold scanner (one-shot, read-only)…")
        candidates = btc_scanner.find_btc_threshold_candidates(limit=config.BTC_TOP_N)
        out = Path(__file__).parent / "btc_candidates.json"
        btc_scanner.snapshot(candidates, out)
        print(f"\n{'rank':<4} {'edge':>6} {'score':>6} {'days':>4} {'kelly':>6}  question")
        print("-" * 92)
        for i, c in enumerate(candidates, 1):
            edge = (c.edge or 0) * 100
            days = c.days_to_expiry if c.days_to_expiry is not None else "—"
            print(f"{i:<4} {edge:5.1f}% {c.score:6.2f} {str(days):>4} ${c.kelly_stake:5.2f}  {c.question[:55]}")
        print(f"\n→ Snapshot written to {out} ({len(candidates)} candidates)")
        return

    mode = "LIVE" if not config.DRY_RUN else "DRY-RUN"
    logger.info("Polymarket Agent starting… [%s]", mode)
    database.init_db()
    logger.info("Database initialised at %s", config.DB_PATH)

    if not config.DRY_RUN:
        _validate_live_mode()

    # Scan thread
    scan_thread = threading.Thread(
        target=_scheduler_thread,
        args=(_run_scan, config.SCAN_INTERVAL_MINUTES, "next_scan_secs"),
        daemon=True,
        name="scan",
    )

    # Track thread — uses its own schedule instance via a wrapper
    track_schedule = schedule.Scheduler()

    def _track_scheduler():
        _run_track()
        track_schedule.every(config.TRACK_INTERVAL_MINUTES).minutes.do(_run_track)
        while True:
            next_run = track_schedule.next_run
            if next_run:
                remaining = max(0, int((next_run - datetime.now()).total_seconds()))
                _update_state(next_track_secs=remaining)
            track_schedule.run_pending()
            time.sleep(1)

    track_thread = threading.Thread(
        target=_track_scheduler,
        daemon=True,
        name="track",
    )

    # Flask web thread
    web_thread = threading.Thread(
        target=run_web,
        kwargs={"host": config.WEB_HOST, "port": config.WEB_PORT},
        daemon=True,
        name="web",
    )

    # BTC scanner thread — read-only, opt-in via BTC_SCANNER_ENABLED env
    btc_thread = None
    if config.BTC_SCANNER_ENABLED:
        btc_thread = threading.Thread(
            target=_scheduler_thread,
            args=(_run_btc_scan, config.BTC_SCAN_INTERVAL_MINUTES, "next_btc_scan_secs"),
            daemon=True,
            name="btc_scan",
        )

    scan_thread.start()
    track_thread.start()
    web_thread.start()
    if btc_thread:
        btc_thread.start()
        logger.info(
            "BTC scanner thread started (read-only, every %d min)",
            config.BTC_SCAN_INTERVAL_MINUTES,
        )

    logger.info(
        "All threads started. Web UI → http://localhost:%d  |  Logs → agent.log",
        config.WEB_PORT,
    )

    # Rich terminal dashboard — main thread
    try:
        with reporter.make_live() as live:
            while True:
                last_scan, next_scan, next_track = _read_state()
                live.update(
                    reporter.build_layout(
                        next_scan_secs=next_scan,
                        next_track_secs=next_track,
                        last_scan=last_scan,
                    )
                )
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down — goodbye.")
        print("\nAgent stopped.")


if __name__ == "__main__":
    main()
