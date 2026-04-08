"""
Good Morning routine for Solaris.

- Reports overnight activity (bets placed/resolved since midnight UTC)
- Checks whether each agent process is running
- Can start an agent in background
- Detects whether dota backtest was run today
- Can trigger dota backtest in background
"""

import os
import subprocess
import sqlite3
import sys
from datetime import datetime, date

import config


# ── Agent process detection ───────────────────────────────────────────────

def _is_running(script_fragment: str) -> bool:
    try:
        r = subprocess.run(
            ["pgrep", "-f", script_fragment],
            capture_output=True, text=True,
        )
        return r.returncode == 0
    except Exception:
        return False


def get_agent_status() -> dict:
    """Return running status for each agent."""
    return {
        "polymarket": _is_running("polymarket-agent/main.py"),
        "dota":       _is_running("dota-agent/main.py"),
    }


# ── Agent launcher ────────────────────────────────────────────────────────

_AGENT_DIRS = {
    "polymarket": os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../polymarket-agent")
    ),
    "dota": os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../dota-agent")
    ),
}


def start_agent(name: str) -> dict:
    if name not in _AGENT_DIRS:
        return {"ok": False, "error": "Unknown agent"}
    cwd = _AGENT_DIRS[name]
    try:
        # Open a real Terminal window so the agent gets a proper TTY (Rich dashboard needs it)
        script = f'tell application "Terminal" to do script "cd {cwd} && {sys.executable} main.py"'
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if result.returncode != 0:
            # Fallback: headless with log file
            log_path = os.path.join(cwd, "agent.log")
            subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=cwd,
                stdout=open(log_path, "a"),
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Dota backtest ─────────────────────────────────────────────────────────

def backtest_run_today() -> bool:
    """Return True if a backtest_summary row was created today (UTC)."""
    if not os.path.exists(config.DOTA_DB):
        return False
    today = date.today().isoformat()  # "YYYY-MM-DD"
    try:
        conn = sqlite3.connect(f"file:{config.DOTA_DB}?mode=ro", uri=True)
        row = conn.execute(
            "SELECT run_at FROM backtest_summary ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return bool(row and row[0][:10] == today)
    except Exception:
        return False


def run_dota_backtest() -> dict:
    """Spawn dota backtest in the background."""
    cwd = _AGENT_DIRS["dota"]
    try:
        subprocess.Popen(
            [sys.executable, "backtest.py"],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Overnight summary ─────────────────────────────────────────────────────

def _overnight_stats(db_path: str) -> dict:
    if not os.path.exists(db_path):
        return {"available": False}
    midnight = (
        datetime.utcnow()
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .isoformat()
    )
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row

        new_bets = conn.execute(
            "SELECT COUNT(*) FROM bets WHERE timestamp >= ?", (midnight,)
        ).fetchone()[0]
        won = conn.execute(
            "SELECT COUNT(*) FROM bets WHERE status='won'  AND timestamp >= ?", (midnight,)
        ).fetchone()[0]
        lost = conn.execute(
            "SELECT COUNT(*) FROM bets WHERE status='lost' AND timestamp >= ?", (midnight,)
        ).fetchone()[0]

        # P&L since midnight
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN status='won'  THEN potential_payout - virtual_amount ELSE 0 END), 0)
              - COALESCE(SUM(CASE WHEN status='lost' THEN virtual_amount ELSE 0 END), 0) AS pnl
            FROM bets WHERE timestamp >= ?
            """,
            (midnight,),
        ).fetchone()
        conn.close()

        return {
            "available":  True,
            "new_bets":   new_bets,
            "won":        won,
            "lost":       lost,
            "pnl":        round(row["pnl"], 2),
        }
    except Exception:
        return {"available": False}


def get_overnight_summary() -> dict:
    return {
        "polymarket": _overnight_stats(config.POLYMARKET_DB),
        "dota":       _overnight_stats(config.DOTA_DB),
    }


# ── Full morning report ───────────────────────────────────────────────────

def morning_report() -> dict:
    agent_status    = get_agent_status()
    overnight       = get_overnight_summary()
    backtest_today  = backtest_run_today()
    tasks = []

    if not agent_status["polymarket"]:
        tasks.append({"agent": "polymarket", "action": "start", "label": "Start Polymarket agent"})
    if not agent_status["dota"]:
        tasks.append({"agent": "dota", "action": "start", "label": "Start Dota 2 agent"})
    if not backtest_today:
        tasks.append({"agent": "dota", "action": "backtest", "label": "Run Dota backtest (not run today)"})

    return {
        "date":            datetime.utcnow().strftime("%A, %B %-d"),
        "agent_status":    agent_status,
        "overnight":       overnight,
        "backtest_today":  backtest_today,
        "tasks":           tasks,
    }
