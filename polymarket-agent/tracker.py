import json
import logging
import database
import fetcher

logger = logging.getLogger(__name__)


def _parse_outcome_prices(detail: dict) -> list[float]:
    raw = detail.get("outcomePrices", [])
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    try:
        return [float(p) for p in raw]
    except Exception:
        return []


def check_resolutions() -> None:
    """
    Poll all open bets and update any that have resolved.
    A winning outcome settles at price ≈ 1.0, losing at ≈ 0.0.
    """
    open_bets = database.get_open_bets()
    if not open_bets:
        logger.debug("No open bets to track.")
        return

    logger.info("Checking resolution for %d open bet(s)…", len(open_bets))

    for bet in open_bets:
        try:
            _check_single(bet)
        except Exception as exc:
            logger.warning("Error checking bet #%d: %s", bet["id"], exc)


def _check_single(bet) -> None:
    detail = fetcher.fetch_market_detail(bet["condition_id"])
    if not detail:
        return

    closed   = detail.get("closed", False)
    resolved = detail.get("resolved", False)

    if not (closed or resolved):
        return  # Still live

    outcome_prices = _parse_outcome_prices(detail)
    if not outcome_prices:
        logger.warning("Bet #%d: market resolved but no outcomePrices found", bet["id"])
        return

    idx = bet["outcome_index"]
    if idx >= len(outcome_prices):
        logger.warning("Bet #%d: outcome_index %d out of range", bet["id"], idx)
        return

    result_price = outcome_prices[idx]

    # Winning outcome settles at 1 (allow small tolerance for float noise)
    if result_price >= 0.99:
        status = "won"
    elif result_price <= 0.01:
        status = "lost"
    else:
        # Partial settlement or void (e.g. multi-outcome)
        status = "void"

    database.update_bet_result(bet["id"], status, result_price)

    symbol = {"won": "✓ WON", "lost": "✗ LOST", "void": "~ VOID"}[status]
    logger.info(
        "Bet #%d resolved — %s | %s → %s | stake=$%.0f | result_price=%.4f",
        bet["id"],
        symbol,
        bet["question"][:50],
        bet["outcome"],
        bet["virtual_amount"],
        result_price,
    )
