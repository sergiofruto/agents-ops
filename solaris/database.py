import sqlite3
from datetime import datetime
import config


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.SOLARIS_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                company     TEXT NOT NULL,
                role        TEXT NOT NULL,
                url         TEXT,
                salary_min  INTEGER,
                salary_max  INTEGER,
                location    TEXT DEFAULT 'Remote',
                status      TEXT DEFAULT 'bookmarked',
                applied_at  TEXT,
                next_action TEXT,
                notes       TEXT,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS interviews (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id       INTEGER NOT NULL REFERENCES jobs(id),
                stage        TEXT NOT NULL,
                scheduled_at TEXT,
                notes        TEXT,
                outcome      TEXT DEFAULT 'pending'
            );
        """)


def get_all_jobs() -> list:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT j.*,
                   COUNT(i.id) AS interview_count
            FROM jobs j
            LEFT JOIN interviews i ON i.job_id = j.id
            GROUP BY j.id
            ORDER BY j.updated_at DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_job(job_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return dict(row) if row else None


def add_job(company: str, role: str, url: str = None, salary_min: int = None,
            salary_max: int = None, location: str = "Remote",
            status: str = "bookmarked") -> int:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO jobs (company, role, url, salary_min, salary_max,
               location, status, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (company, role, url, salary_min, salary_max, location, status, now),
        )
        return cur.lastrowid


def update_job(job_id: int, **kwargs) -> bool:
    allowed = {"company", "role", "url", "salary_min", "salary_max", "location",
               "status", "applied_at", "next_action", "notes"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    fields["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k}=?" for k in fields)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE jobs SET {set_clause} WHERE id=?",
            (*fields.values(), job_id),
        )
    return True


def delete_job(job_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM interviews WHERE job_id=?", (job_id,))
        conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))


def add_interview(job_id: int, stage: str, scheduled_at: str = None,
                  notes: str = None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO interviews (job_id, stage, scheduled_at, notes)
               VALUES (?, ?, ?, ?)""",
            (job_id, stage, scheduled_at, notes),
        )
        return cur.lastrowid


def get_interviews(job_id: int) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM interviews WHERE job_id=? ORDER BY id",
            (job_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_interview(interview_id: int, **kwargs) -> bool:
    allowed = {"stage", "scheduled_at", "notes", "outcome"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    set_clause = ", ".join(f"{k}=?" for k in fields)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE interviews SET {set_clause} WHERE id=?",
            (*fields.values(), interview_id),
        )
    return True


def pipeline_counts() -> dict:
    statuses = ["bookmarked", "applied", "phone", "technical", "final", "offer", "rejected"]
    with get_connection() as conn:
        counts = {}
        for s in statuses:
            n = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE status=?", (s,)
            ).fetchone()[0]
            counts[s] = n
    return counts
