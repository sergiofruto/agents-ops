import sqlite3
from datetime import datetime, timedelta
from typing import Optional
import config


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS bets (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id        TEXT NOT NULL,
                condition_id     TEXT NOT NULL,
                question         TEXT NOT NULL,
                outcome          TEXT NOT NULL,
                outcome_index    INTEGER NOT NULL,
                token_id         TEXT NOT NULL,
                price_at_bet     REAL NOT NULL,
                virtual_amount   REAL NOT NULL,
                potential_payout REAL NOT NULL,
                score            REAL NOT NULL,
                timestamp        TEXT NOT NULL,
                status           TEXT NOT NULL DEFAULT 'open',
                result_price     REAL,
                team_a           TEXT,
                team_b           TEXT,
                tournament       TEXT,
                edge             REAL,
                true_prob        REAL,
                elo_prob         REAL,
                form_a           REAL,
                form_b           REAL,
                h2h_winrate      REAL,
                h2h_sample       INTEGER,
                league_tier      TEXT,
                kelly_stake      REAL DEFAULT 100
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id  TEXT NOT NULL,
                token_id   TEXT NOT NULL,
                price      REAL NOT NULL,
                timestamp  TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_bets_market_id
                ON bets(market_id);
            CREATE INDEX IF NOT EXISTS idx_bets_status
                ON bets(status);
            CREATE INDEX IF NOT EXISTS idx_price_history_market_ts
                ON price_history(market_id, timestamp);

            CREATE TABLE IF NOT EXISTS backtest_summary (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at             TEXT NOT NULL,
                days               INTEGER NOT NULL,
                n_teams            INTEGER NOT NULL,
                n_matches          INTEGER NOT NULL,
                elo_accuracy       REAL NOT NULL,
                model_accuracy     REAL NOT NULL,
                elo_brier          REAL NOT NULL,
                model_brier        REAL NOT NULL,
                baseline_brier     REAL NOT NULL,
                calibration_factor REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS backtest_matches (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_id    INTEGER NOT NULL,
                match_id       INTEGER NOT NULL,
                team_a         TEXT NOT NULL,
                team_b         TEXT NOT NULL,
                league         TEXT,
                start_time     INTEGER,
                elo_prob       REAL,
                raw_true_prob  REAL,
                true_prob      REAL,
                team_a_won     INTEGER NOT NULL,
                model_correct  INTEGER NOT NULL,
                FOREIGN KEY (backtest_id) REFERENCES backtest_summary(id)
            );

            CREATE INDEX IF NOT EXISTS idx_backtest_matches_run
                ON backtest_matches(backtest_id);
        """)

        # Auto-migration: add new columns if they don't exist yet
        new_columns = [
            ("team_a",      "TEXT"),
            ("team_b",      "TEXT"),
            ("tournament",  "TEXT"),
            ("edge",        "REAL"),
            ("true_prob",   "REAL"),
            ("elo_prob",    "REAL"),
            ("form_a",      "REAL"),
            ("form_b",      "REAL"),
            ("h2h_winrate", "REAL"),
            ("h2h_sample",  "INTEGER"),
            ("league_tier", "TEXT"),
            ("kelly_stake", "REAL DEFAULT 100"),
        ]
        for col, typedef in new_columns:
            try:
                conn.execute(f"ALTER TABLE bets ADD COLUMN {col} {typedef}")
            except sqlite3.OperationalError:
                pass  # column already exists


def save_bet(
    market_id: str,
    condition_id: str,
    question: str,
    outcome: str,
    outcome_index: int,
    token_id: str,
    price_at_bet: float,
    virtual_amount: float,
    potential_payout: float,
    score: float,
    team_a: Optional[str] = None,
    team_b: Optional[str] = None,
    tournament: Optional[str] = None,
    edge: Optional[float] = None,
    true_prob: Optional[float] = None,
    elo_prob: Optional[float] = None,
    form_a: Optional[float] = None,
    form_b: Optional[float] = None,
    h2h_winrate: Optional[float] = None,
    h2h_sample: Optional[int] = None,
    league_tier: Optional[str] = None,
    kelly_stake: float = 100.0,
) -> int:
    ts = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO bets
                (market_id, condition_id, question, outcome, outcome_index,
                 token_id, price_at_bet, virtual_amount, potential_payout,
                 score, timestamp, status,
                 team_a, team_b, tournament, edge, true_prob, elo_prob,
                 form_a, form_b, h2h_winrate, h2h_sample, league_tier, kelly_stake)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open',
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                market_id, condition_id, question, outcome, outcome_index,
                token_id, price_at_bet, virtual_amount, potential_payout,
                score, ts,
                team_a, team_b, tournament, edge, true_prob, elo_prob,
                form_a, form_b, h2h_winrate, h2h_sample, league_tier, kelly_stake,
            ),
        )
        return cur.lastrowid


def update_bet_result(bet_id: int, status: str, result_price: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE bets SET status=?, result_price=? WHERE id=?",
            (status, result_price, bet_id),
        )


def get_open_bets() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM bets WHERE status='open' ORDER BY timestamp DESC"
        ).fetchall()


def get_all_bets() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM bets ORDER BY timestamp DESC"
        ).fetchall()


def is_market_open(market_id: str) -> bool:
    """Return True if we already hold an open bet for this market."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM bets WHERE market_id=? AND status='open'",
            (market_id,),
        ).fetchone()
        return row is not None


def save_price_snapshot(market_id: str, token_id: str, price: float) -> None:
    ts = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO price_history (market_id, token_id, price, timestamp) VALUES (?, ?, ?, ?)",
            (market_id, token_id, price, ts),
        )


def prune_price_history(keep_hours: int = 6) -> int:
    """Delete price_history rows older than `keep_hours`. Returns rows deleted."""
    cutoff = (datetime.utcnow() - timedelta(hours=keep_hours)).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM price_history WHERE timestamp < ?", (cutoff,)
        )
        return cur.rowcount


def get_price_history(market_id: str, hours: int = 2) -> list[float]:
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT price FROM price_history WHERE market_id=? AND timestamp>=? ORDER BY timestamp",
            (market_id, cutoff),
        ).fetchall()
    return [r["price"] for r in rows]


def get_stats() -> dict:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM bets").fetchone()[0]
        won   = conn.execute("SELECT COUNT(*) FROM bets WHERE status='won'").fetchone()[0]
        lost  = conn.execute("SELECT COUNT(*) FROM bets WHERE status='lost'").fetchone()[0]
        open_ = conn.execute("SELECT COUNT(*) FROM bets WHERE status='open'").fetchone()[0]

        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN status='won'  THEN potential_payout - virtual_amount ELSE 0 END), 0)
              - COALESCE(SUM(CASE WHEN status='lost' THEN virtual_amount                   ELSE 0 END), 0)
                AS pnl,
                COALESCE(SUM(CASE WHEN status IN ('won','lost') THEN virtual_amount ELSE 0 END), 0) AS total_wagered
            FROM bets
            """
        ).fetchone()
        pnl           = row["pnl"]
        total_wagered = row["total_wagered"]

    resolved = won + lost
    win_rate = (won / resolved * 100) if resolved > 0 else 0.0
    roi      = (pnl / total_wagered * 100) if total_wagered > 0 else 0.0

    return {
        "total": total,
        "open": open_,
        "won": won,
        "lost": lost,
        "resolved": resolved,
        "win_rate": round(win_rate, 1),
        "pnl": round(pnl, 2),
        "roi": round(roi, 1),
        "total_wagered": round(total_wagered, 2),
    }


# ---------------------------------------------------------------------------
# Backtest helpers
# ---------------------------------------------------------------------------

def save_backtest_run(
    days: int,
    n_teams: int,
    n_matches: int,
    elo_accuracy: float,
    model_accuracy: float,
    elo_brier: float,
    model_brier: float,
    baseline_brier: float,
    calibration_factor: float,
    matches: list[dict],
) -> int:
    """Persist a backtest run and its per-match records. Returns the run id."""
    run_at = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO backtest_summary
                (run_at, days, n_teams, n_matches, elo_accuracy, model_accuracy,
                 elo_brier, model_brier, baseline_brier, calibration_factor)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (run_at, days, n_teams, n_matches, elo_accuracy, model_accuracy,
             elo_brier, model_brier, baseline_brier, calibration_factor),
        )
        run_id = cur.lastrowid

        conn.executemany(
            """
            INSERT INTO backtest_matches
                (backtest_id, match_id, team_a, team_b, league, start_time,
                 elo_prob, raw_true_prob, true_prob, team_a_won, model_correct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (run_id, m["match_id"], m["team_a"], m["team_b"], m.get("league"),
                 m.get("start_time"), m["elo_prob"], m.get("raw_true_prob"),
                 m["true_prob"], m["team_a_won"], m["model_correct"])
                for m in matches
            ],
        )
    return run_id


def get_latest_backtest() -> Optional[sqlite3.Row]:
    """Return the most recent backtest_summary row, or None."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM backtest_summary ORDER BY id DESC LIMIT 1"
        ).fetchone()


def get_backtest_matches(backtest_id: int, limit: int = 50) -> list[sqlite3.Row]:
    """Return recent matches for a backtest run, newest first."""
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT * FROM backtest_matches
            WHERE backtest_id = ?
            ORDER BY start_time DESC
            LIMIT ?
            """,
            (backtest_id, limit),
        ).fetchall()
