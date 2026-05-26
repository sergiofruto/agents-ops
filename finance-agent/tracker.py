"""
Bill tracker — monitors recurring fixed expenses, surfaces due-soon alerts,
and checks for excess ARS exposure.
"""

import calendar
import logging
from datetime import date
from typing import Optional

import database

logger = logging.getLogger("tracker")

# Max ARS to hold in USD equivalent — anything above is dead money losing to inflation
ARS_FLOAT_LIMIT_USD = 300.0


def _days_until_due(due_day: int) -> int:
    """
    Return days until the next occurrence of due_day, using proper calendar math.
    Handles 28/29/30/31-day months correctly — no more += 31 hacks.
    """
    today = date.today()
    last_this = calendar.monthrange(today.year, today.month)[1]
    this_month = today.replace(day=min(due_day, last_this))
    if this_month >= today:
        return (this_month - today).days
    # Already passed this month → next month
    if today.month == 12:
        nm = today.replace(year=today.year + 1, month=1, day=1)
    else:
        nm = today.replace(month=today.month + 1, day=1)
    last_next = calendar.monthrange(nm.year, nm.month)[1]
    return (nm.replace(day=min(due_day, last_next)) - today).days


def check_bills() -> list[dict]:
    """
    Check for bills due in the next 7 days.
    Logs warnings and returns list of due-soon bill dicts.
    """
    due = database.get_due_soon(days=7)
    alerts = []

    for bill in due:
        days_until = _days_until_due(bill["due_day"])

        last_paid = bill["last_paid_date"] or "never"
        alert = {
            "id":          bill["id"],
            "name":        bill["name"],
            "amount_usd":  bill["amount_usd"],
            "due_day":     bill["due_day"],
            "days_until":  days_until,
            "last_paid":   last_paid,
            "category":    bill["category"],
        }
        alerts.append(alert)

        if days_until == 0:
            logger.warning("BILL DUE TODAY: %s — $%.0f", bill["name"], bill["amount_usd"])
        elif days_until <= 3:
            logger.warning(
                "Bill due in %d day(s): %s — $%.0f",
                days_until, bill["name"], bill["amount_usd"],
            )
        else:
            logger.info(
                "Bill coming up in %d days: %s — $%.0f",
                days_until, bill["name"], bill["amount_usd"],
            )

    return alerts


def check_ars_exposure() -> Optional[dict]:
    """
    Check if the ARS balance in Santander exceeds the safe float threshold.
    Strategy: hold only ~1 month of local expenses in ARS (~$300 USD equiv).
    Anything above that should be converted to USD immediately.

    Returns an alert dict if over threshold, None if OK.
    """
    nw = database.get_latest_net_worth()
    if not nw:
        return None

    santander_ars  = float(nw["santander_ars"] or 0)
    funds_ars      = float(nw["santander_funds_ars"] if "santander_funds_ars" in nw.keys() else 0)
    ars_rate       = float(nw["ars_usd_rate"] or 0)

    if ars_rate <= 0:
        logger.warning(
            "ARS exposure check skipped — snapshot has no ARS/USD rate. "
            "Run 'python main.py snapshot' to save a new snapshot with the current rate."
        )
        return None

    total_ars_usd = (santander_ars + funds_ars) / ars_rate
    ars_in_usd    = total_ars_usd  # alias for reporting
    excess_usd    = total_ars_usd - ARS_FLOAT_LIMIT_USD

    if excess_usd > 0:
        logger.warning(
            "⚠  ARS EXPOSURE ALERT | ARS %.0f = $%.0f USD | "
            "Safe float: $%.0f USD | Excess: $%.0f USD | "
            "Convert excess to USD (Wallbit) ASAP — ARS loses ~20-30%% annually",
            santander_ars, ars_in_usd, ARS_FLOAT_LIMIT_USD, excess_usd,
        )
        return {
            "santander_ars":    santander_ars,
            "ars_in_usd":       round(ars_in_usd, 2),
            "ars_rate":         ars_rate,
            "safe_limit_usd":   ARS_FLOAT_LIMIT_USD,
            "excess_usd":       round(excess_usd, 2),
            "snapshot_date":    nw["date"],
        }

    logger.info(
        "ARS exposure OK: ARS %.0f = $%.0f USD (limit $%.0f)",
        santander_ars, ars_in_usd, ARS_FLOAT_LIMIT_USD,
    )
    return None


def get_bills_summary() -> dict:
    """Return monthly bill summary for dashboard."""
    bills = database.get_all_bills()
    total = database.get_monthly_fixed_total()
    due_soon = database.get_due_soon(days=7)

    return {
        "total_monthly_usd": total,
        "bill_count":        len(bills),
        "due_soon_count":    len(due_soon),
        "bills":             [dict(b) for b in bills],
        "due_soon":          [dict(b) for b in due_soon],
    }
