"""
Position tracker — polls open positions and applies stop-loss / take-profit.
"""

import logging

import fetcher
import database
import config

logger = logging.getLogger("tracker")


def check_positions() -> None:
    """Check all open positions against current price and close if triggered."""
    positions = database.get_open_positions()
    if not positions:
        logger.info("No open positions to track")
        return

    logger.info("Tracking %d open position(s)", len(positions))

    for pos in positions:
        symbol     = pos["symbol"]
        asset_type = pos["asset_type"]
        direction  = pos["direction"]

        price = fetcher.get_current_price(symbol, asset_type)
        if price is None:
            logger.warning("Could not fetch price for %s — skipping", symbol)
            continue

        database.update_position_price(pos["id"], price)

        stop_loss   = pos["stop_loss"]
        take_profit = pos["take_profit"]

        if direction == "BUY":
            hit_sl = price <= stop_loss
            hit_tp = price >= take_profit
        else:
            hit_sl = price >= stop_loss
            hit_tp = price <= take_profit

        if hit_tp:
            database.close_position(pos["id"], price)
            pnl_pct = abs(price - pos["entry_price"]) / pos["entry_price"] * 100
            logger.info(
                "[PAPER] TAKE PROFIT %s @ $%.4f (+%.1f%%) | id=%d",
                symbol, price, pnl_pct, pos["id"],
            )
        elif hit_sl:
            database.close_position(pos["id"], price)
            pnl_pct = abs(price - pos["entry_price"]) / pos["entry_price"] * 100
            logger.info(
                "[PAPER] STOP LOSS %s @ $%.4f (-%.1f%%) | id=%d",
                symbol, price, pnl_pct, pos["id"],
            )
        else:
            pnl_pct = (
                (price - pos["entry_price"]) / pos["entry_price"] * 100
                if direction == "BUY"
                else (pos["entry_price"] - price) / pos["entry_price"] * 100
            )
            logger.info(
                "  %s %s: $%.4f → $%.4f (%+.1f%%)",
                direction, symbol, pos["entry_price"], price, pnl_pct,
            )
