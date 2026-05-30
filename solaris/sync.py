"""
One-way uploader: local agent SQLite DBs -> Turso. Read-only on sources.
Excludes finance entirely. Run manually or via cron.
    python sync.py
"""
import logging
import os
import sqlite3
import sys

import config
from turso_client import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("solaris.sync")


def schema_statements() -> list[str]:
    here = os.path.dirname(__file__)
    with open(os.path.join(here, "turso", "schema.sql")) as f:
        return [s.strip() for s in f.read().split(";") if s.strip()]


def _upsert(table: str, cols: list[str]) -> str:
    placeholders = ", ".join("?" for _ in cols)
    updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c not in ("id",))
    # natural key is the first column (id / run_at / team_name)
    return (f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT({cols[0]}) DO UPDATE SET {updates}")


_POLY_COLS = ["id", "question", "outcome", "price_at_bet", "virtual_amount",
              "potential_payout", "score", "edge", "kelly_stake", "status",
              "timestamp", "order_id"]
_DOTA_COLS = ["id", "question", "outcome", "team_a", "team_b", "tournament",
              "league_tier", "price_at_bet", "virtual_amount", "potential_payout",
              "score", "edge", "true_prob", "elo_prob", "form_a", "form_b",
              "h2h_winrate", "h2h_sample", "kelly_stake", "status", "timestamp"]
_BACKTEST_COLS = ["run_at", "days", "n_teams", "n_matches", "model_accuracy",
                  "elo_accuracy", "model_brier", "elo_brier", "calibration_factor"]
_ELO_COLS = ["team_name", "elo", "snapshot_at"]
_JOB_COLS = ["id", "company", "role", "url", "salary_min", "salary_max", "location",
             "status", "applied_at", "next_action", "notes", "updated_at", "interview_count"]

UPSERTS = {
    "polymarket_bets": (_upsert("polymarket_bets", _POLY_COLS), _POLY_COLS),
    "dota_bets":       (_upsert("dota_bets", _DOTA_COLS), _DOTA_COLS),
    "dota_backtest":   (_upsert("dota_backtest", _BACKTEST_COLS), _BACKTEST_COLS),
    "dota_elo":        (_upsert("dota_elo", _ELO_COLS), _ELO_COLS),
    "jobs":            (_upsert("jobs", _JOB_COLS), _JOB_COLS),
}


def _open_ro(path: str) -> sqlite3.Connection | None:
    if not os.path.exists(path):
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(conn: sqlite3.Connection, query: str) -> list[dict]:
    return [dict(r) for r in conn.execute(query).fetchall()]


def _push(client, table: str, rows: list[dict]) -> int:
    sql, cols = UPSERTS[table]
    n = 0
    for r in rows:
        client.execute(sql, [r.get(c) for c in cols])
        n += 1
    return n


def sync() -> dict:
    client = get_client()
    summary = {}
    try:
        for stmt in schema_statements():
            client.execute(stmt)

        # Polymarket
        try:
            conn = _open_ro(config.POLYMARKET_DB)
            if conn:
                rows = _rows(conn, f"SELECT {', '.join(_POLY_COLS)} FROM bets")
                summary["polymarket_bets"] = _push(client, "polymarket_bets", rows)
                conn.close()
        except Exception as e:
            logger.error("polymarket sync failed: %s", e)

        # Dota bets + backtest + elo
        try:
            conn = _open_ro(config.DOTA_DB)
            if conn:
                summary["dota_bets"] = _push(client, "dota_bets",
                    _rows(conn, f"SELECT {', '.join(_DOTA_COLS)} FROM bets"))
                try:
                    summary["dota_backtest"] = _push(client, "dota_backtest",
                        _rows(conn, f"SELECT {', '.join(_BACKTEST_COLS)} FROM backtest_summary"))
                except sqlite3.OperationalError:
                    pass
                try:
                    latest = conn.execute("SELECT MAX(snapshot_at) FROM elo_snapshots").fetchone()[0]
                    if latest:
                        elo = _rows(conn, f"SELECT {', '.join(_ELO_COLS)} FROM elo_snapshots WHERE snapshot_at='{latest}'")
                        summary["dota_elo"] = _push(client, "dota_elo", elo)
                except sqlite3.OperationalError:
                    pass
                conn.close()
        except Exception as e:
            logger.error("dota sync failed: %s", e)

        # Jobs (solaris.db) with interview_count
        try:
            conn = _open_ro(config.SOLARIS_DB)
            if conn:
                jobs = _rows(conn, """
                    SELECT j.id, j.company, j.role, j.url, j.salary_min, j.salary_max,
                           j.location, j.status, j.applied_at, j.next_action, j.notes, j.updated_at,
                           (SELECT COUNT(*) FROM interviews i WHERE i.job_id=j.id) AS interview_count
                    FROM jobs j
                """)
                summary["jobs"] = _push(client, "jobs", jobs)
                conn.close()
        except Exception as e:
            logger.error("jobs sync failed: %s", e)
    finally:
        client.close()

    logger.info("Sync complete: %s", summary)
    return summary


if __name__ == "__main__":
    sync()
