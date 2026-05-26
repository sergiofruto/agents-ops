"""
SQLite database layer for finance-agent.

Tables:
  expenses        — parsed bank transactions, categorized
  bills           — recurring fixed expenses with due dates
  net_worth       — manual snapshots of all accounts
  goals           — savings goals (house purchase)
  monthly_reports — Claude strategy synthesis per month
"""

import calendar
import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional
import config


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS expenses (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                date          TEXT NOT NULL,
                description   TEXT NOT NULL,
                amount_ars    REAL,
                amount_usd    REAL,
                category      TEXT NOT NULL DEFAULT 'other',
                source        TEXT NOT NULL DEFAULT 'santander',
                raw_text      TEXT,
                imported_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bills (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT NOT NULL UNIQUE,
                amount_usd     REAL NOT NULL,
                due_day        INTEGER NOT NULL DEFAULT 0,
                category       TEXT NOT NULL,
                active         INTEGER NOT NULL DEFAULT 1,
                last_paid_date TEXT
            );

            CREATE TABLE IF NOT EXISTS net_worth (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                date            TEXT NOT NULL UNIQUE,
                wallbit_usd     REAL NOT NULL DEFAULT 0,
                santander_ars   REAL NOT NULL DEFAULT 0,
                santander_usd   REAL NOT NULL DEFAULT 0,
                ibkr_usd        REAL NOT NULL DEFAULT 0,
                polymarket_usd  REAL NOT NULL DEFAULT 0,
                other_usd       REAL NOT NULL DEFAULT 0,
                total_usd       REAL NOT NULL DEFAULT 0,
                ars_usd_rate    REAL,
                notes           TEXT
            );

            CREATE TABLE IF NOT EXISTS goals (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                name                 TEXT NOT NULL,
                target_usd           REAL NOT NULL,
                monthly_contribution REAL NOT NULL DEFAULT 3000,
                created_at           TEXT NOT NULL,
                notes                TEXT
            );

            CREATE TABLE IF NOT EXISTS monthly_reports (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                month         TEXT NOT NULL UNIQUE,
                income_usd    REAL,
                expenses_usd  REAL,
                savings_usd   REAL,
                savings_rate  REAL,
                net_worth_usd REAL,
                strategy_text TEXT,
                created_at    TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_expenses_date
                ON expenses(date);
            CREATE INDEX IF NOT EXISTS idx_expenses_category
                ON expenses(category);
            CREATE INDEX IF NOT EXISTS idx_net_worth_date
                ON net_worth(date);
        """)

    _seed_initial_data()


def _seed_initial_data() -> None:
    """Seed bills and house goal if not already present."""
    with get_connection() as conn:
        # Seed bills
        for name, amount, due_day, category in config.KNOWN_BILLS:
            conn.execute(
                """INSERT OR IGNORE INTO bills (name, amount_usd, due_day, category)
                   VALUES (?, ?, ?, ?)""",
                (name, amount, due_day, category),
            )

        # Seed house goal
        existing = conn.execute("SELECT COUNT(*) FROM goals").fetchone()[0]
        if existing == 0:
            conn.execute(
                """INSERT INTO goals (name, target_usd, monthly_contribution, created_at, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    "Casa con patio — Argentina",
                    config.GOAL_TARGET,
                    config.MONTHLY_SAVINGS_TARGET,
                    datetime.utcnow().isoformat(),
                    "La Plata area or Grand La Plata. Budget $100k. Timeline ~28 months.",
                ),
            )


# ── Expenses ──────────────────────────────────────────────────────────────────

def save_expense(
    date: str,
    description: str,
    amount_ars: Optional[float],
    amount_usd: Optional[float],
    category: str,
    source: str = "santander",
    raw_text: Optional[str] = None,
) -> bool:
    """Insert expense. Returns False if duplicate (same date+description+amount)."""
    imported_at = datetime.utcnow().isoformat()
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT 1 FROM expenses WHERE date=? AND description=? AND amount_ars=?",
            (date, description, amount_ars),
        ).fetchone()
        if existing:
            return False
        conn.execute(
            """INSERT INTO expenses (date, description, amount_ars, amount_usd, category,
               source, raw_text, imported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (date, description, amount_ars, amount_usd, category, source, raw_text, imported_at),
        )
        return True


def get_expenses_by_month(month: str) -> list[sqlite3.Row]:
    """month = 'YYYY-MM'"""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM expenses WHERE date LIKE ? ORDER BY date DESC",
            (f"{month}%",),
        ).fetchall()


def get_expenses_summary(month: str) -> dict:
    """Returns total by category for a given month."""
    rows = get_expenses_by_month(month)
    summary: dict[str, float] = {}
    for row in rows:
        cat = row["category"]
        amt = row["amount_usd"] or 0.0
        summary[cat] = summary.get(cat, 0.0) + amt
    return dict(sorted(summary.items(), key=lambda x: x[1], reverse=True))


# ── Bills ─────────────────────────────────────────────────────────────────────

def get_all_bills() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM bills WHERE active=1 ORDER BY due_day"
        ).fetchall()


def get_due_soon(days: int = 7) -> list[sqlite3.Row]:
    """Bills due within next N days (only bills with a fixed due_day).
    Uses proper calendar arithmetic — handles 28/30/31-day months correctly.
    """
    today = date.today()
    cutoff = today + timedelta(days=days)

    with get_connection() as conn:
        all_bills = conn.execute(
            "SELECT * FROM bills WHERE active=1 AND due_day > 0 ORDER BY due_day"
        ).fetchall()

    result = []
    for bill in all_bills:
        due_day = bill["due_day"]
        # Clamp to actual last day of current month (e.g. day 31 in April → 30)
        last_this = calendar.monthrange(today.year, today.month)[1]
        this_month_due = today.replace(day=min(due_day, last_this))
        if today <= this_month_due <= cutoff:
            result.append(bill)
            continue
        # Due day already passed — check next month
        if today.month == 12:
            nm = today.replace(year=today.year + 1, month=1, day=1)
        else:
            nm = today.replace(month=today.month + 1, day=1)
        last_next = calendar.monthrange(nm.year, nm.month)[1]
        next_month_due = nm.replace(day=min(due_day, last_next))
        if next_month_due <= cutoff:
            result.append(bill)

    return result


def mark_bill_paid(bill_id: int) -> None:
    today = date.today().isoformat()
    with get_connection() as conn:
        conn.execute(
            "UPDATE bills SET last_paid_date=? WHERE id=?",
            (today, bill_id),
        )


def get_monthly_fixed_total() -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount_usd), 0) FROM bills WHERE active=1"
        ).fetchone()
        return float(row[0])


# ── Net Worth ─────────────────────────────────────────────────────────────────

def add_net_worth_snapshot(
    wallbit_usd: float,
    santander_ars: float,
    santander_usd: float,
    ibkr_usd: float,
    polymarket_usd: float,
    other_usd: float = 0.0,
    ars_usd_rate: Optional[float] = None,
    notes: Optional[str] = None,
) -> float:
    """Insert or replace today's net worth snapshot. Returns total_usd."""
    ars_in_usd = (santander_ars / ars_usd_rate) if ars_usd_rate and santander_ars else 0.0
    total = wallbit_usd + santander_usd + ars_in_usd + ibkr_usd + polymarket_usd + other_usd
    today = date.today().isoformat()
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO net_worth
               (date, wallbit_usd, santander_ars, santander_usd, ibkr_usd,
                polymarket_usd, other_usd, total_usd, ars_usd_rate, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (today, wallbit_usd, santander_ars, santander_usd, ibkr_usd,
             polymarket_usd, other_usd, total, ars_usd_rate, notes),
        )
    return total


def get_latest_net_worth() -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM net_worth ORDER BY date DESC LIMIT 1"
        ).fetchone()


def get_net_worth_history(limit: int = 30) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM net_worth ORDER BY date DESC LIMIT ?",
            (limit,),
        ).fetchall()


# ── Goals ─────────────────────────────────────────────────────────────────────

def get_goal() -> Optional[sqlite3.Row]:
    """Returns the primary (first) goal."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM goals ORDER BY id LIMIT 1"
        ).fetchone()


def get_goal_progress() -> dict:
    """
    Returns progress dict toward the house goal.
    Projected date calculated at monthly_contribution rate and at 7% invested rate.
    """
    goal = get_goal()
    nw   = get_latest_net_worth()

    target  = goal["target_usd"] if goal else config.GOAL_TARGET
    current = float(nw["total_usd"]) if nw else 0.0
    monthly = goal["monthly_contribution"] if goal else config.MONTHLY_SAVINGS_TARGET
    gap     = max(target - current, 0)

    # Simple projection: months at flat savings rate
    months_flat = int(gap / monthly) if monthly > 0 else 999

    # Projected with 7% annual return (0.5833% monthly)
    r = config.INVESTMENT_RETURN_RATE / 12
    if r > 0 and monthly > 0:
        # n = log(1 + gap*r/monthly) / log(1+r)  — derived from FV formula
        import math
        try:
            months_invested = int(math.log(1 + gap * r / monthly) / math.log(1 + r))
        except (ValueError, ZeroDivisionError):
            months_invested = months_flat
    else:
        months_invested = months_flat

    from datetime import date
    from dateutil.relativedelta import relativedelta
    try:
        projected_flat     = (date.today() + relativedelta(months=months_flat)).strftime("%B %Y")
        projected_invested = (date.today() + relativedelta(months=months_invested)).strftime("%B %Y")
    except Exception:
        projected_flat     = f"~{months_flat} months"
        projected_invested = f"~{months_invested} months"

    return {
        "target":              target,
        "current":             current,
        "gap":                 gap,
        "progress_pct":        round(current / target * 100, 1) if target > 0 else 0,
        "months_flat":         months_flat,
        "months_invested":     months_invested,
        "projected_flat":      projected_flat,
        "projected_invested":  projected_invested,
        "monthly_contribution": monthly,
    }


# ── Monthly Reports ───────────────────────────────────────────────────────────

def save_monthly_report(
    month: str,
    income_usd: float,
    expenses_usd: float,
    savings_usd: float,
    net_worth_usd: float,
    strategy_text: str,
) -> None:
    savings_rate = savings_usd / income_usd if income_usd > 0 else 0.0
    created_at = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO monthly_reports
               (month, income_usd, expenses_usd, savings_usd, savings_rate,
                net_worth_usd, strategy_text, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (month, income_usd, expenses_usd, savings_usd, savings_rate,
             net_worth_usd, strategy_text, created_at),
        )


def get_latest_report() -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM monthly_reports ORDER BY month DESC LIMIT 1"
        ).fetchone()
