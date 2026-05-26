"""
Goal tracker — house purchase progress and net worth management.
"""

import logging
from datetime import date
from typing import Optional

import database
import parser as stmt_parser

logger = logging.getLogger("goal")


def snapshot(
    wallbit_usd: float,
    santander_ars: float,
    santander_usd: float,
    ibkr_usd: float,
    polymarket_usd: float,
    other_usd: float = 0.0,
    notes: Optional[str] = None,
) -> dict:
    """
    Save today's net worth snapshot and return progress toward goal.
    ARS/USD rate auto-fetched from BCRA if not configured.
    """
    ars_rate = stmt_parser.get_ars_usd_rate()

    total = database.add_net_worth_snapshot(
        wallbit_usd=wallbit_usd,
        santander_ars=santander_ars,
        santander_usd=santander_usd,
        ibkr_usd=ibkr_usd,
        polymarket_usd=polymarket_usd,
        other_usd=other_usd,
        ars_usd_rate=ars_rate,
        notes=notes,
    )

    progress = database.get_goal_progress()
    logger.info(
        "Net worth snapshot saved: $%.0f / $%.0f (%.1f%%) — %d months to goal",
        total,
        progress["target"],
        progress["progress_pct"],
        progress["months_flat"],
    )
    return progress


def get_progress() -> dict:
    """Return current goal progress without saving a snapshot."""
    return database.get_goal_progress()


def log_progress() -> None:
    """Log current goal progress to console."""
    p = get_progress()
    nw = database.get_latest_net_worth()
    if nw:
        logger.info(
            "Net worth: $%.0f | Goal: $%.0f | Progress: %.1f%% | "
            "Months remaining: %d (flat) / %d (invested) | "
            "Projected: %s",
            p["current"],
            p["target"],
            p["progress_pct"],
            p["months_flat"],
            p["months_invested"],
            p["projected_invested"],
        )
    else:
        logger.info("No net worth snapshot yet. Run goal.snapshot() to add one.")
