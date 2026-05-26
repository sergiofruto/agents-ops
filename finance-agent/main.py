"""
Finance Agent — Personal Financial Advisor
==========================================
Runs two background threads:
  • daily_thread  — morning check: bill alerts + goal progress log  (every 24h)
  • web_thread    — Flask API at localhost:5006

Main thread: Rich terminal dashboard.

CLI commands:
  python main.py                        — start dashboard
  python main.py import <pdf_path>      — import Santander PDF statement
  python main.py snapshot               — add net worth snapshot interactively
  python main.py bills                  — list all bills
  python main.py progress               — show goal progress

Press Ctrl-C to exit.
"""

import logging
import sys
import threading
import time
from datetime import datetime

import config
import database
import tracker
import goal as goal_tracker
import reporter
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


# ── Daily morning check ───────────────────────────────────────────────────────

def _run_daily_check():
    logger.info("=== DAILY CHECK ===")
    try:
        # Bill alerts
        alerts = tracker.check_bills()
        if not alerts:
            logger.info("No bills due in the next 7 days.")

        # ARS exposure check
        ars_alert = tracker.check_ars_exposure()
        if ars_alert:
            logger.warning(
                "ACTION NEEDED: Convert ARS %.0f ($%.0f USD) to USD — "
                "keep max $%.0f USD in ARS",
                ars_alert["santander_ars"],
                ars_alert["excess_usd"],
                ars_alert["safe_limit_usd"],
            )

        # Goal progress
        goal_tracker.log_progress()

    except Exception:
        logger.exception("Daily check failed")


def _daily_thread():
    """Run daily check at startup, then every 24 hours."""
    _run_daily_check()
    while True:
        time.sleep(86400)  # 24 hours
        _run_daily_check()


# ── CLI commands ──────────────────────────────────────────────────────────────

def cmd_import(pdf_path: str):
    """Import a Santander PDF statement."""
    import parser as stmt_parser
    logger.info("Importing: %s", pdf_path)
    imported, skipped = stmt_parser.import_statement(pdf_path)
    print(f"\n✓ Imported {imported} transactions, {skipped} skipped (duplicates)")
    print(f"  Run 'python main.py' to see updated dashboard.\n")


def cmd_snapshot():
    """Interactively add a net worth snapshot."""
    print("\n=== Net Worth Snapshot ===")
    print("Enter current balances (press Enter to use 0):\n")

    def ask(label: str, default: float = 0.0) -> float:
        raw = input(f"  {label} [${default:.0f}]: ").strip()
        if not raw:
            return default
        try:
            return float(raw.replace(",", ""))
        except ValueError:
            return default

    # Get latest for defaults
    nw = database.get_latest_net_worth()
    wallbit    = ask("Wallbit USD",      nw["wallbit_usd"]    if nw else 11000)
    sant_usd   = ask("Santander USD",    nw["santander_usd"]  if nw else 5500)
    sant_ars   = ask("Santander ARS",    nw["santander_ars"]  if nw else 385000)
    ibkr       = ask("IBKR USD",         nw["ibkr_usd"]       if nw else 500)
    poly       = ask("Polymarket USD",   nw["polymarket_usd"] if nw else 400)
    other      = ask("Other USD",        nw["other_usd"]      if nw else 0)
    notes      = input("  Notes (optional): ").strip() or None

    progress = goal_tracker.snapshot(
        wallbit_usd=wallbit,
        santander_ars=sant_ars,
        santander_usd=sant_usd,
        ibkr_usd=ibkr,
        polymarket_usd=poly,
        other_usd=other,
        notes=notes,
    )

    print(f"\n✓ Snapshot saved!")
    print(f"  Net worth:  ${progress['current']:,.0f}")
    print(f"  Goal:       ${progress['target']:,.0f}")
    print(f"  Progress:   {progress['progress_pct']:.1f}%")
    print(f"  Target:     {progress['projected_invested']} (invested @ 7%)")
    print()


def cmd_bills():
    """List all bills."""
    bills = database.get_all_bills()
    print("\n=== Monthly Bills ===")
    total = 0.0
    for b in bills:
        due = f"due day {b['due_day']}" if b["due_day"] > 0 else "variable"
        last = b["last_paid_date"] or "never"
        print(f"  #{b['id']} {b['name']:<20} ${b['amount_usd']:>6.0f}  ({due})  last paid: {last}")
        total += b["amount_usd"]
    print(f"  {'Total':<20} ${total:>6.0f}")
    print()


def cmd_progress():
    """Show goal progress."""
    p = database.get_goal_progress()
    print("\n=== Goal Progress ===")
    print(f"  Current net worth:  ${p['current']:,.0f}")
    print(f"  Target:             ${p['target']:,.0f}")
    print(f"  Gap:                ${p['gap']:,.0f}")
    print(f"  Progress:           {p['progress_pct']:.1f}%")
    print(f"  Months (flat):      {p['months_flat']} → {p['projected_flat']}")
    print(f"  Months (7% ETF):    {p['months_invested']} → {p['projected_invested']}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Handle CLI commands
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        database.init_db()
        if cmd == "import" and len(sys.argv) > 2:
            cmd_import(sys.argv[2])
        elif cmd == "snapshot":
            cmd_snapshot()
        elif cmd == "bills":
            cmd_bills()
        elif cmd == "progress":
            cmd_progress()
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python main.py [import <pdf>|snapshot|bills|progress]")
        return

    # Normal daemon mode
    logger.info("Finance Agent starting…")
    database.init_db()

    # Seed initial net worth snapshot if none exists
    if not database.get_latest_net_worth():
        logger.info("No net worth snapshot found — seeding initial values from roadmap context")
        goal_tracker.snapshot(
            wallbit_usd=11000,
            santander_ars=385020,
            santander_usd=5854,
            ibkr_usd=500,
            polymarket_usd=400,
            notes="Initial snapshot — May 2026",
        )

    daily_thread = threading.Thread(target=_daily_thread, daemon=True, name="daily")
    web_thread   = threading.Thread(
        target=run_web,
        kwargs={"host": config.WEB_HOST, "port": config.WEB_PORT},
        daemon=True, name="web",
    )

    daily_thread.start()
    web_thread.start()

    logger.info("Finance Agent running. Web → http://localhost:%d", config.WEB_PORT)

    try:
        with reporter.make_live() as live:
            while True:
                live.update(reporter.build_layout())
                time.sleep(5)
    except KeyboardInterrupt:
        p = database.get_goal_progress()
        print("\n=== FINANCE AGENT SHUTDOWN ===")
        print(f"Net worth:   ${p['current']:,.0f}")
        print(f"Goal:        ${p['target']:,.0f} ({p['progress_pct']:.1f}%)")
        print(f"Projected:   {p['projected_invested']}")
        print("==============================\n")


if __name__ == "__main__":
    main()
