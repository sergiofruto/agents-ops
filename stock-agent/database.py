"""
SQLite database for Silicon Intel.

Tables
------
positions     — legacy paper trading (kept for compat)
price_history — OHLCV snapshots per symbol
signals       — legacy trading signals
intel_signals — Twitter / infosec / semicon raw signals
"""

import json
import sqlite3
import logging
from datetime import datetime, timezone, timedelta

import config

logger = logging.getLogger("database")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS positions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol        TEXT    NOT NULL,
                asset_type    TEXT    NOT NULL,   -- 'stock' | 'crypto'
                direction     TEXT    NOT NULL,   -- 'BUY' | 'SELL'
                entry_price   REAL    NOT NULL,
                current_price REAL,
                quantity      REAL    NOT NULL,
                stake_usd     REAL    NOT NULL,
                stop_loss     REAL    NOT NULL,
                take_profit   REAL    NOT NULL,
                status        TEXT    NOT NULL DEFAULT 'open',  -- 'open' | 'closed'
                close_price   REAL,
                pnl_usd       REAL,
                pnl_pct       REAL,
                confidence    REAL,
                reasoning     TEXT,
                signals_json  TEXT,
                opened_at     TEXT    NOT NULL,
                closed_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol     TEXT NOT NULL,
                price      REAL NOT NULL,
                volume     REAL,
                recorded_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_price_history_symbol
                ON price_history (symbol, recorded_at);

            CREATE TABLE IF NOT EXISTS signals (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol       TEXT NOT NULL,
                asset_type   TEXT NOT NULL,
                direction    TEXT NOT NULL,
                confidence   REAL NOT NULL,
                rule_signals TEXT,
                reasoning    TEXT,
                acted        INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS intel_signals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source      TEXT NOT NULL,   -- 'twitter' | 'infosec' | 'semicon'
                signal_type TEXT NOT NULL,   -- 'tweet' | 'cve' | 'news' | 'price-mover'
                payload     TEXT NOT NULL,   -- JSON blob
                recorded_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_intel_signals_source
                ON intel_signals (source, recorded_at);
        """)
    logger.info("Database initialised at %s", config.DB_PATH)


# ── Positions ──────────────────────────────────────────────────────────────

def open_position(
    symbol: str,
    asset_type: str,
    direction: str,
    entry_price: float,
    quantity: float,
    stake_usd: float,
    stop_loss: float,
    take_profit: float,
    confidence: float,
    reasoning: str,
    signals_json: str,
) -> int:
    with _connect() as conn:
        cur = conn.execute("""
            INSERT INTO positions
                (symbol, asset_type, direction, entry_price, current_price,
                 quantity, stake_usd, stop_loss, take_profit,
                 confidence, reasoning, signals_json, opened_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            symbol, asset_type, direction, entry_price, entry_price,
            quantity, stake_usd, stop_loss, take_profit,
            confidence, reasoning, signals_json,
            datetime.now(timezone.utc).isoformat(),
        ))
        return cur.lastrowid


def get_open_positions() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM positions WHERE status = 'open' ORDER BY opened_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_position_price(position_id: int, current_price: float) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE positions SET current_price=? WHERE id=?",
            (current_price, position_id),
        )


def close_position(position_id: int, close_price: float) -> None:
    with _connect() as conn:
        pos = dict(conn.execute(
            "SELECT * FROM positions WHERE id=?", (position_id,)
        ).fetchone())

        if pos["direction"] == "BUY":
            pnl_pct = (close_price - pos["entry_price"]) / pos["entry_price"]
        else:
            pnl_pct = (pos["entry_price"] - close_price) / pos["entry_price"]

        pnl_usd = pnl_pct * pos["stake_usd"]

        conn.execute("""
            UPDATE positions
            SET status='closed', close_price=?, pnl_usd=?, pnl_pct=?,
                current_price=?, closed_at=?
            WHERE id=?
        """, (
            close_price, pnl_usd, pnl_pct,
            close_price, datetime.now(timezone.utc).isoformat(),
            position_id,
        ))


def is_symbol_open(symbol: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM positions WHERE symbol=? AND status='open' LIMIT 1",
            (symbol,),
        ).fetchone()
        return row is not None


def get_live_bankroll() -> float:
    """Virtual bankroll = initial − open stakes + realized PnL."""
    with _connect() as conn:
        open_stake = conn.execute(
            "SELECT COALESCE(SUM(stake_usd),0) FROM positions WHERE status='open'"
        ).fetchone()[0]
        realized_pnl = conn.execute(
            "SELECT COALESCE(SUM(pnl_usd),0) FROM positions WHERE status='closed'"
        ).fetchone()[0]
    return config.VIRTUAL_BANKROLL - open_stake + realized_pnl


def get_open_exposure() -> float:
    with _connect() as conn:
        return conn.execute(
            "SELECT COALESCE(SUM(stake_usd),0) FROM positions WHERE status='open'"
        ).fetchone()[0]


def get_stats() -> dict:
    with _connect() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        open_   = conn.execute("SELECT COUNT(*) FROM positions WHERE status='open'").fetchone()[0]
        closed  = conn.execute("SELECT COUNT(*) FROM positions WHERE status='closed'").fetchone()[0]
        won     = conn.execute("SELECT COUNT(*) FROM positions WHERE status='closed' AND pnl_usd > 0").fetchone()[0]
        pnl     = conn.execute("SELECT COALESCE(SUM(pnl_usd),0) FROM positions WHERE status='closed'").fetchone()[0]
    return {
        "total": total, "open": open_, "closed": closed,
        "won": won, "win_rate": round(won / closed, 3) if closed else 0.0,
        "realized_pnl": round(pnl, 2),
    }


# ── Price history ──────────────────────────────────────────────────────────

def save_price_snapshot(symbol: str, price: float, volume: float = 0) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO price_history (symbol, price, volume, recorded_at) VALUES (?,?,?,?)",
            (symbol, price, volume, datetime.now(timezone.utc).isoformat()),
        )


# ── Signals ───────────────────────────────────────────────────────────────

def save_signal(
    symbol: str, asset_type: str, direction: str,
    confidence: float, rule_signals: str, reasoning: str, acted: bool,
) -> None:
    with _connect() as conn:
        conn.execute("""
            INSERT INTO signals
                (symbol, asset_type, direction, confidence, rule_signals, reasoning, acted, created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            symbol, asset_type, direction, confidence,
            rule_signals, reasoning, int(acted),
            datetime.now(timezone.utc).isoformat(),
        ))


# ── Intel signals ─────────────────────────────────────────────────────────────

def store_intel_signals(
    tweets:  list[dict],
    infosec: list[dict],
    semicon: list[dict],
) -> None:
    """Persist raw intelligence signals to DB."""
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for t in tweets:
        rows.append(("twitter", "tweet", json.dumps(t), now))
    for s in infosec:
        rows.append(("infosec", s.get("source", "cve").lower(), json.dumps(s), now))
    for s in semicon:
        src = "price-mover" if s.get("source") == "price-mover" else "semicon"
        rows.append((src, s.get("source", "news").lower(), json.dumps(s), now))

    if not rows:
        return
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO intel_signals (source, signal_type, payload, recorded_at) VALUES (?,?,?,?)",
            rows,
        )


def get_recent_signals(hours: int = 24) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Retrieve intel signals from the last `hours` hours.
    Returns (tweets, infosec_signals, semicon_signals).
    Deduplicates by payload content using a hash.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT source, payload FROM intel_signals WHERE recorded_at >= ? ORDER BY recorded_at DESC",
            (cutoff,),
        ).fetchall()

    tweets, infosec, semicon = [], [], []
    seen: set[str] = set()

    for row in rows:
        source  = row["source"]
        payload = row["payload"]
        h = payload[:100]  # cheap dedup key
        if h in seen:
            continue
        seen.add(h)

        try:
            sig = json.loads(payload)
        except Exception:
            continue

        if source == "twitter":
            tweets.append(sig)
        elif source == "infosec":
            infosec.append(sig)
        else:
            semicon.append(sig)

    return tweets, infosec, semicon
