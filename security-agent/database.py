"""SQLite schema and connection. Every row here is already redacted."""
import sqlite3

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT NOT NULL DEFAULT 'running',   -- running | done
    overview    TEXT
);
CREATE TABLE IF NOT EXISTS findings (
    scan_id     INTEGER NOT NULL,
    key         TEXT NOT NULL,
    category    TEXT NOT NULL,
    severity    TEXT NOT NULL,
    title       TEXT NOT NULL,
    evidence    TEXT NOT NULL,
    explanation TEXT NOT NULL,
    fix_json    TEXT NOT NULL,
    is_new      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_findings_scan ON findings(scan_id);
CREATE TABLE IF NOT EXISTS scan_checks (
    scan_id      INTEGER NOT NULL,
    category     TEXT NOT NULL,
    passed_json  TEXT NOT NULL,
    skipped_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS status_checks (
    service    TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    state      TEXT NOT NULL,
    official   TEXT,
    probe_ok   INTEGER,
    probe_ms   INTEGER,
    incident   TEXT
);
CREATE INDEX IF NOT EXISTS idx_status_service ON status_checks(service, checked_at);
CREATE TABLE IF NOT EXISTS digests (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    day      TEXT NOT NULL,
    built_at TEXT NOT NULL,
    used_ai  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS digest_entries (
    digest_id    INTEGER NOT NULL,
    rank         INTEGER NOT NULL,
    title        TEXT NOT NULL,
    summary      TEXT,
    who          TEXT,
    action       TEXT,
    affects_json TEXT NOT NULL DEFAULT '[]',
    sources_json TEXT NOT NULL DEFAULT '[]',
    kev          INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS seen_items (
    url        TEXT PRIMARY KEY,
    first_seen TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS job_runs (
    job      TEXT PRIMARY KEY,
    last_run TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_usage (
    day           TEXT NOT NULL,
    job           TEXT NOT NULL,
    model         TEXT NOT NULL,
    input_tokens  INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd      REAL NOT NULL
);
-- What Solaris syncs to Turso: counts and one title, never evidence or paths.
DROP VIEW IF EXISTS solaris_summary;
CREATE VIEW solaris_summary AS
WITH last_scan AS (SELECT id, finished_at FROM scans WHERE status = 'done' ORDER BY id DESC LIMIT 1),
     f AS (SELECT severity, title, rowid FROM findings WHERE scan_id = (SELECT id FROM last_scan)),
     latest_status AS (
         SELECT s.state FROM status_checks s
         WHERE s.checked_at = (SELECT MAX(checked_at) FROM status_checks WHERE service = s.service))
SELECT 1 AS id,
       (SELECT finished_at FROM last_scan) AS last_scan_at,
       (SELECT COUNT(*) FROM f WHERE severity = 'high') AS high,
       (SELECT COUNT(*) FROM f WHERE severity = 'medium') AS medium,
       (SELECT COUNT(*) FROM f WHERE severity = 'low') AS low,
       (SELECT COUNT(*) FROM f WHERE severity = 'info') AS info,
       (SELECT title FROM f ORDER BY CASE severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1
                                                   WHEN 'low' THEN 2 ELSE 3 END, rowid LIMIT 1) AS worst_title,
       (SELECT COUNT(*) FROM latest_status WHERE state IN ('degraded', 'down')) AS providers_not_up,
       (SELECT COUNT(*) FROM digest_entries
         WHERE digest_id = (SELECT MAX(id) FROM digests) AND affects_json NOT IN ('[]', '')) AS digest_affecting,
       strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime') AS updated_at;
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
