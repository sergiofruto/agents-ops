import sqlite3
from datetime import datetime, timedelta
from typing import Optional
import config


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # allows concurrent read+write between threads
    conn.execute("PRAGMA busy_timeout=5000")  # wait up to 5s instead of immediately raising
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS bets (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id     TEXT NOT NULL,
                condition_id  TEXT NOT NULL,
                question      TEXT NOT NULL,
                outcome       TEXT NOT NULL,
                outcome_index INTEGER NOT NULL,
                token_id      TEXT NOT NULL,
                price_at_bet  REAL NOT NULL,
                virtual_amount REAL NOT NULL,
                potential_payout REAL NOT NULL,
                score         REAL NOT NULL,
                timestamp     TEXT NOT NULL,
                status        TEXT NOT NULL DEFAULT 'open',
                result_price  REAL
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
            CREATE UNIQUE INDEX IF NOT EXISTS idx_bets_open_market
                ON bets(market_id) WHERE status='open';
        """)

        # Auto-migration: add new columns if they don't exist yet
        for col, typedef in [
            ("edge",            "REAL"),
            ("kelly_stake",     "REAL DEFAULT 100"),
            ("order_id",        "TEXT"),          # CLOB order ID (live mode only)
            ("edge_available",  "INTEGER DEFAULT 0"),  # 1 if true_prob was computed
            ("true_prob",       "REAL"),               # model-derived probability
            ("days_to_expiry",  "INTEGER"),             # days from bet placement to close
            ("fill_status",     "TEXT"),                # 'filled', 'pending_fill', NULL (dry-run)
            ("resolved_at",     "TEXT"),                # UTC ISO timestamp of resolution
        ]:
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
    edge: Optional[float] = None,
    kelly_stake: float = 100.0,
    order_id: Optional[str] = None,
    edge_available: bool = False,
    true_prob: Optional[float] = None,
    days_to_expiry: Optional[int] = None,
) -> int:
    ts = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO bets
                (market_id, condition_id, question, outcome, outcome_index,
                 token_id, price_at_bet, virtual_amount, potential_payout,
                 score, timestamp, status, edge, kelly_stake, order_id,
                 edge_available, true_prob, days_to_expiry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)
            """,
            (market_id, condition_id, question, outcome, outcome_index,
             token_id, price_at_bet, virtual_amount, potential_payout,
             score, ts, edge, kelly_stake, order_id,
             int(edge_available), true_prob, days_to_expiry),
        )
        return cur.lastrowid or 0  # 0 = INSERT was ignored (duplicate open market)


def update_bet_result(bet_id: int, status: str, result_price: float) -> None:
    resolved_at = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "UPDATE bets SET status=?, result_price=?, resolved_at=? WHERE id=?",
            (status, result_price, resolved_at, bet_id),
        )


def update_fill_status(bet_id: int, fill_status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE bets SET fill_status=? WHERE id=?",
            (fill_status, bet_id),
        )


def get_pending_fill_bets() -> list[sqlite3.Row]:
    """Return live bets whose CLOB order has not yet been confirmed as matched."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM bets WHERE fill_status='pending_fill' ORDER BY timestamp DESC"
        ).fetchall()


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


def is_market_on_cooldown(market_id: str, cooldown_days: int = 7) -> bool:
    """
    Return True if this market resolved within the last `cooldown_days` days.
    Uses resolved_at (not placement timestamp) so the cooldown window starts
    from when the outcome was confirmed, not when the bet was placed.
    Falls back to timestamp for legacy rows that predate the resolved_at column.
    """
    cutoff = (datetime.utcnow() - timedelta(days=cooldown_days)).isoformat()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM bets
            WHERE market_id=?
              AND status IN ('won', 'lost')
              AND COALESCE(resolved_at, timestamp) >= ?
            """,
            (market_id, cutoff),
        ).fetchone()
        return row is not None


def prune_price_history(days: int = 3) -> int:
    """Delete price_history rows older than `days`. Returns number of rows deleted."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM price_history WHERE timestamp < ?", (cutoff,)
        )
        return cur.rowcount


def save_price_snapshot(market_id: str, token_id: str, price: float) -> None:
    ts = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO price_history (market_id, token_id, price, timestamp) VALUES (?, ?, ?, ?)",
            (market_id, token_id, price, ts),
        )


def get_price_history(market_id: str, hours: int = 2) -> list[float]:
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT price FROM price_history WHERE market_id=? AND timestamp>=? ORDER BY timestamp",
            (market_id, cutoff),
        ).fetchall()
    return [r["price"] for r in rows]


def get_open_exposure() -> float:
    """Sum of virtual_amount for all open bets."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(virtual_amount), 0) FROM bets WHERE status='open'"
        ).fetchone()
        return float(row[0])


def get_live_bankroll(initial_bankroll: float) -> float:
    """
    Returns current bankroll = initial + realized P&L - open exposure.
    Never falls below 10% of initial to keep Kelly from collapsing to zero.
    """
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN status='won'  THEN potential_payout - virtual_amount ELSE 0 END), 0)
              - COALESCE(SUM(CASE WHEN status='lost' THEN virtual_amount                   ELSE 0 END), 0)
                AS realized_pnl,
                COALESCE(SUM(CASE WHEN status='open' THEN virtual_amount ELSE 0 END), 0)
                AS open_exposure
            FROM bets
            """
        ).fetchone()

    live = initial_bankroll + row["realized_pnl"] - row["open_exposure"]
    return max(live, initial_bankroll * 0.10)


def get_stats() -> dict:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM bets").fetchone()[0]
        won   = conn.execute("SELECT COUNT(*) FROM bets WHERE status='won'").fetchone()[0]
        lost  = conn.execute("SELECT COUNT(*) FROM bets WHERE status='lost'").fetchone()[0]
        open_ = conn.execute("SELECT COUNT(*) FROM bets WHERE status='open'").fetchone()[0]

        # P&L: won bets get payout - amount; lost bets lose amount
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
