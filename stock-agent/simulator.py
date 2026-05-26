"""
Paper trading simulator.

place_trade() receives a TradeSignal and:
  1. Checks portfolio exposure limits
  2. Sizes the position (Kelly-inspired, capped at MAX_POSITION_PCT)
  3. Inserts a paper position into the DB
"""

import json
import logging
import math

import config
import database
from analyzer import TradeSignal

logger = logging.getLogger("simulator")


def _kelly_size(confidence: float, win_pct: float = 0.55) -> float:
    """
    Simplified Kelly fraction.
    f = (p*(b+1) - 1) / b  where b = take_profit / stop_loss ratio
    Capped at MAX_POSITION_PCT.
    """
    b = config.TAKE_PROFIT_PCT / config.STOP_LOSS_PCT
    f = (confidence * (b + 1) - 1) / b
    f = max(0.01, min(f, config.MAX_POSITION_PCT))
    return round(f, 4)


def place_trade(signal: TradeSignal) -> bool:
    """
    Place a paper trade for the given signal.
    Returns True if placed, False if skipped.
    """
    # Don't double-up on same symbol
    if database.is_symbol_open(signal.symbol):
        logger.info("Already have open position in %s — skipping", signal.symbol)
        return False

    # Portfolio limits
    open_positions = database.get_open_positions()
    if len(open_positions) >= config.MAX_OPEN_POSITIONS:
        logger.info("Max open positions (%d) reached — skipping", config.MAX_OPEN_POSITIONS)
        return False

    live_bankroll = database.get_live_bankroll()
    open_exposure = database.get_open_exposure()
    max_exposure  = (live_bankroll + open_exposure) * 0.80
    if open_exposure >= max_exposure:
        logger.info(
            "Exposure limit reached ($%.0f / $%.0f max) — skipping",
            open_exposure, max_exposure,
        )
        return False

    # Position sizing
    fraction  = _kelly_size(signal.confidence)
    stake_usd = round(live_bankroll * fraction, 2)
    stake_usd = min(stake_usd, live_bankroll * config.MAX_POSITION_PCT)
    stake_usd = max(stake_usd, 10.0)  # min $10

    price    = signal.entry_price
    quantity = stake_usd / price

    # Stop-loss / take-profit levels
    if signal.direction == "BUY":
        stop_loss   = round(price * (1 - config.STOP_LOSS_PCT), 6)
        take_profit = round(price * (1 + config.TAKE_PROFIT_PCT), 6)
    else:  # SELL / short
        stop_loss   = round(price * (1 + config.STOP_LOSS_PCT), 6)
        take_profit = round(price * (1 - config.TAKE_PROFIT_PCT), 6)

    position_id = database.open_position(
        symbol=signal.symbol,
        asset_type=signal.asset_type,
        direction=signal.direction,
        entry_price=price,
        quantity=quantity,
        stake_usd=stake_usd,
        stop_loss=stop_loss,
        take_profit=take_profit,
        confidence=signal.confidence,
        reasoning=signal.reasoning,
        signals_json=json.dumps(signal.rule_signals),
    )

    logger.info(
        "[PAPER] %s %s @ $%.4f | stake=$%.2f | SL=$%.4f | TP=$%.4f | id=%d",
        signal.direction, signal.symbol, price,
        stake_usd, stop_loss, take_profit, position_id,
    )
    return True
