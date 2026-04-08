"""
database.py — SQLite persistence for The Analyst
=================================================
Tables:
  briefs         — synthesised intelligence briefs
  intel_signals  — raw signals from OSINT / infosec / cosmic scans
  cves           — tracked CVE records
"""

from __future__ import annotations

import sqlite3
import json
from datetime import datetime
from typing import Any

import config


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS briefs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at  TEXT    NOT NULL,
            title       TEXT    NOT NULL,
            threat_level TEXT   NOT NULL,   -- LOW / MEDIUM / HIGH / CRITICAL
            summary     TEXT    NOT NULL,
            cyber_body  TEXT    NOT NULL,
            cosmic_body TEXT    NOT NULL,
            synthesis   TEXT    NOT NULL,
            opening_quote TEXT  NOT NULL,
            hermetic_principle TEXT NOT NULL,
            raw_signals TEXT    NOT NULL    -- JSON list of signal ids
        );

        CREATE TABLE IF NOT EXISTS intel_signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            collected_at TEXT   NOT NULL,
            source      TEXT    NOT NULL,   -- nvd / cisa / otx / opensky / marine / aws / cosmic
            signal_type TEXT    NOT NULL,   -- network / geopolitical / cosmic / social / infosec
            severity    TEXT    NOT NULL,   -- INFO / LOW / MEDIUM / HIGH / CRITICAL
            title       TEXT    NOT NULL,
            body        TEXT    NOT NULL,
            raw_json    TEXT,               -- original API payload (JSON)
            used_in_brief INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS cves (
            cve_id      TEXT    PRIMARY KEY,
            published   TEXT    NOT NULL,
            severity    TEXT    NOT NULL,
            cvss        REAL,
            description TEXT    NOT NULL,
            cisa_kev    INTEGER DEFAULT 0,  -- 1 if in CISA KEV
            aws_related INTEGER DEFAULT 0,
            first_seen  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cosmic_snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            captured_at TEXT    NOT NULL,
            planet_positions TEXT NOT NULL, -- JSON
            active_aspects   TEXT NOT NULL, -- JSON
            moon_phase       TEXT NOT NULL,
            mercury_retrograde INTEGER NOT NULL,
            dominant_themes  TEXT NOT NULL  -- JSON list of strings
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT    NOT NULL,
            role        TEXT    NOT NULL,   -- user / assistant
            content     TEXT    NOT NULL,
            created_at  TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id, created_at);
        """)


# ---------------------------------------------------------------------------
# Signal helpers
# ---------------------------------------------------------------------------

def save_signal(
    source: str,
    signal_type: str,
    severity: str,
    title: str,
    body: str,
    raw_json: Any = None,
) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO intel_signals
               (collected_at, source, signal_type, severity, title, body, raw_json)
               VALUES (?,?,?,?,?,?,?)""",
            (
                datetime.utcnow().isoformat(),
                source,
                signal_type,
                severity,
                title,
                body,
                json.dumps(raw_json) if raw_json is not None else None,
            ),
        )
        return cur.lastrowid


def get_unused_signals(limit: int = 50) -> list[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute(
            """SELECT * FROM intel_signals
               WHERE used_in_brief = 0
               ORDER BY
                 CASE severity
                   WHEN 'CRITICAL' THEN 1
                   WHEN 'HIGH'     THEN 2
                   WHEN 'MEDIUM'   THEN 3
                   WHEN 'LOW'      THEN 4
                   ELSE            5
                 END,
                 collected_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()


def mark_signals_used(ids: list[int]) -> None:
    if not ids:
        return
    placeholders = ",".join("?" * len(ids))
    with _conn() as conn:
        conn.execute(
            f"UPDATE intel_signals SET used_in_brief = 1 WHERE id IN ({placeholders})",
            ids,
        )


# ---------------------------------------------------------------------------
# CVE helpers
# ---------------------------------------------------------------------------

def upsert_cve(
    cve_id: str,
    published: str,
    severity: str,
    cvss: float | None,
    description: str,
    cisa_kev: bool = False,
    aws_related: bool = False,
) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT INTO cves
               (cve_id, published, severity, cvss, description, cisa_kev, aws_related, first_seen)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(cve_id) DO UPDATE SET
                 severity    = excluded.severity,
                 cvss        = excluded.cvss,
                 cisa_kev    = excluded.cisa_kev,
                 aws_related = excluded.aws_related""",
            (
                cve_id, published, severity, cvss, description,
                int(cisa_kev), int(aws_related),
                datetime.utcnow().isoformat(),
            ),
        )


def get_recent_cves(limit: int = 20, only_kev: bool = False) -> list[sqlite3.Row]:
    with _conn() as conn:
        q = "SELECT * FROM cves"
        if only_kev:
            q += " WHERE cisa_kev = 1"
        q += " ORDER BY published DESC LIMIT ?"
        return conn.execute(q, (limit,)).fetchall()


# ---------------------------------------------------------------------------
# Cosmic snapshot helpers
# ---------------------------------------------------------------------------

def save_cosmic_snapshot(
    planet_positions: dict,
    active_aspects: list,
    moon_phase: str,
    mercury_retrograde: bool,
    dominant_themes: list[str],
) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO cosmic_snapshots
               (captured_at, planet_positions, active_aspects, moon_phase,
                mercury_retrograde, dominant_themes)
               VALUES (?,?,?,?,?,?)""",
            (
                datetime.utcnow().isoformat(),
                json.dumps(planet_positions),
                json.dumps(active_aspects),
                moon_phase,
                int(mercury_retrograde),
                json.dumps(dominant_themes),
            ),
        )
        return cur.lastrowid


def get_latest_cosmic() -> sqlite3.Row | None:
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM cosmic_snapshots ORDER BY captured_at DESC LIMIT 1"
        ).fetchone()


# ---------------------------------------------------------------------------
# Brief helpers
# ---------------------------------------------------------------------------

def save_brief(
    title: str,
    threat_level: str,
    summary: str,
    cyber_body: str,
    cosmic_body: str,
    synthesis: str,
    opening_quote: str,
    hermetic_principle: str,
    signal_ids: list[int],
) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO briefs
               (created_at, title, threat_level, summary, cyber_body, cosmic_body,
                synthesis, opening_quote, hermetic_principle, raw_signals)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                datetime.utcnow().isoformat(),
                title, threat_level, summary, cyber_body, cosmic_body,
                synthesis, opening_quote, hermetic_principle,
                json.dumps(signal_ids),
            ),
        )
        return cur.lastrowid


def get_recent_briefs(limit: int = 10) -> list[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM briefs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()


def get_brief(brief_id: int) -> sqlite3.Row | None:
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM briefs WHERE id = ?", (brief_id,)
        ).fetchone()


# ---------------------------------------------------------------------------
# Conversation helpers
# ---------------------------------------------------------------------------

def save_message(session_id: str, role: str, content: str) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO conversations (session_id, role, content, created_at)
               VALUES (?,?,?,?)""",
            (session_id, role, content, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def get_conversation(session_id: str, limit: int = 40) -> list[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute(
            """SELECT role, content, created_at FROM conversations
               WHERE session_id = ?
               ORDER BY created_at ASC
               LIMIT ?""",
            (session_id, limit),
        ).fetchall()


def list_sessions(limit: int = 20) -> list[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute(
            """SELECT session_id,
                      MIN(created_at) AS started_at,
                      COUNT(*) AS message_count,
                      MAX(created_at) AS last_at
               FROM conversations
               GROUP BY session_id
               ORDER BY last_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()


def delete_session(session_id: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def get_stats() -> dict:
    with _conn() as conn:
        total_signals = conn.execute("SELECT COUNT(*) FROM intel_signals").fetchone()[0]
        high_signals  = conn.execute(
            "SELECT COUNT(*) FROM intel_signals WHERE severity IN ('HIGH','CRITICAL')"
        ).fetchone()[0]
        total_briefs  = conn.execute("SELECT COUNT(*) FROM briefs").fetchone()[0]
        total_cves    = conn.execute("SELECT COUNT(*) FROM cves").fetchone()[0]
        kev_cves      = conn.execute("SELECT COUNT(*) FROM cves WHERE cisa_kev=1").fetchone()[0]
        return {
            "total_signals": total_signals,
            "high_signals":  high_signals,
            "total_briefs":  total_briefs,
            "total_cves":    total_cves,
            "kev_cves":      kev_cves,
        }
