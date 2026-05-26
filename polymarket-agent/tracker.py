import json
import logging
import config
import database
import fetcher
from simulator import get_clob_client, round_to_tick

logger = logging.getLogger(__name__)


def _sell_position(bet, current_price: float) -> bool:
    """
    Place a market-price SELL order on the CLOB to exit a live position.
    Returns True if the order was accepted, False on any failure.
    """
    try:
        from py_clob_client_v2.clob_types import OrderArgs, CreateOrderOptions as PartialCreateOrderOptions

        client   = get_clob_client()
        token_id = bet["token_id"]

        if not token_id:
            logger.warning("Cannot sell bet #%d — no token_id stored", bet["id"])
            return False

        tick_size_str = client.get_tick_size(token_id)
        tick          = float(tick_size_str)
        neg_risk      = client.get_neg_risk(token_id)

        price = round_to_tick(current_price, tick)
        # potential_payout holds the number of shares bought (USDC received if we win)
        size  = round(float(bet["potential_payout"]), 2)

        order_args = OrderArgs(
            token_id = token_id,
            price    = price,
            size     = size,
            side     = "SELL",
        )
        options = PartialCreateOrderOptions(
            tick_size = tick_size_str,
            neg_risk  = neg_risk,
        )

        resp     = client.create_and_post_order(order_args, options)
        order_id = resp.get("orderID") or resp.get("order_id", "")
        status   = resp.get("status", "unknown")

        logger.info(
            "[LIVE] Sell order posted | bet #%d | order=%s | status=%s | "
            "token=%s | price=%.3f | size=%.2f shares",
            bet["id"], order_id, status, token_id, price, size,
        )
        return True

    except Exception as exc:
        logger.error(
            "[LIVE] Sell order FAILED for bet #%d — manual intervention required: %s",
            bet["id"], exc,
        )
        return False


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


def check_pending_fills() -> None:
    """
    Re-poll the CLOB for each pending_fill bet to confirm match or void.
    No-op in dry-run mode.
    """
    if config.DRY_RUN:
        return

    pending = database.get_pending_fill_bets()
    if not pending:
        return

    logger.info("Checking %d pending-fill order(s)…", len(pending))

    try:
        client = get_clob_client()
    except Exception as exc:
        logger.error("Cannot check pending fills — CLOB client error: %s", exc)
        return

    for bet in pending:
        order_id = bet["order_id"]
        if not order_id:
            logger.warning("Bet #%d has no order_id — voiding", bet["id"])
            database.update_bet_result(bet["id"], "void", 0.0)
            continue

        try:
            order         = client.get_order(order_id)
            size_matched  = float(order.get("size_matched",  0) or 0)
            original_size = float(order.get("original_size", 0) or 0)
            order_status  = (order.get("status") or "").lower()

            fill_pct = size_matched / original_size if original_size > 0 else 0

            if fill_pct >= 0.95:
                database.update_fill_status(bet["id"], "filled")
                logger.info(
                    "Bet #%d fill confirmed (%.0f%% matched) | order=%s",
                    bet["id"], fill_pct * 100, order_id,
                )
            elif order_status in ("canceled", "cancelled", "expired"):
                database.update_bet_result(bet["id"], "void", 0.0)
                database.update_fill_status(bet["id"], "canceled")
                logger.warning(
                    "Bet #%d order %s — voided | order=%s",
                    bet["id"], order_status, order_id,
                )
            else:
                logger.warning(
                    "Bet #%d still unmatched (%.0f%% filled, status=%s) | order=%s",
                    bet["id"], fill_pct * 100, order_status, order_id,
                )

        except Exception as exc:
            logger.warning("Error checking fill for bet #%d: %s", bet["id"], exc)


def check_resolutions() -> None:
    """
    Poll all open bets and update any that have resolved.
    A winning outcome settles at price ≈ 1.0, losing at ≈ 0.0.
    Also prunes price_history rows older than 7 days.
    """
    check_pending_fills()

    deleted = database.prune_price_history(days=3)
    if deleted:
        logger.info("Pruned %d stale price_history row(s)", deleted)

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


def _check_exit_triggers(bet, outcome_prices: list[float]) -> None:
    """Log stop-loss / take-profit alerts for live markets. Dry-run auto-closes."""
    if not outcome_prices:
        return

    idx = bet["outcome_index"]
    if idx >= len(outcome_prices):
        return

    current_price = outcome_prices[idx]
    entry_price   = bet["price_at_bet"]
    move          = current_price - entry_price  # positive = moved in our favour

    trigger = None
    if move <= -config.STOP_LOSS_PPTS:
        trigger = "STOP-LOSS"
    elif move >= config.TAKE_PROFIT_PPTS:
        trigger = "TAKE-PROFIT"

    if not trigger:
        return

    direction = f"{move:+.1%}"
    logger.warning(
        "⚠  %s triggered | bet #%d | %s → %s | entry=%.2f  now=%.2f (%s) | stake=$%.0f",
        trigger, bet["id"], bet["question"][:50], bet["outcome"],
        entry_price, current_price, direction, bet["virtual_amount"],
    )

    if config.DRY_RUN:
        # Auto-close the position in dry-run — record at current price
        status = "won" if trigger == "TAKE-PROFIT" else "lost"
        database.update_bet_result(bet["id"], status, current_price)
        logger.info(
            "  → [DRY RUN] Position auto-closed as '%s' at price %.2f",
            status, current_price,
        )
    else:
        # Live: place a real sell order then close the DB record
        sold = _sell_position(bet, current_price)
        if sold:
            status = "won" if trigger == "TAKE-PROFIT" else "lost"
            database.update_bet_result(bet["id"], status, current_price)
            logger.info(
                "  → [LIVE] Position closed as '%s' at price %.2f",
                status, current_price,
            )
        elif current_price >= 0.99:
            # Market effectively resolved at 1.0 — close in DB even if CLOB sell failed
            database.update_bet_result(bet["id"], "won", current_price)
            logger.warning(
                "  → [LIVE] Sell failed but price=%.3f ≈ 1.0 — closing bet #%d as won",
                current_price, bet["id"],
            )
        elif current_price <= 0.01:
            database.update_bet_result(bet["id"], "lost", current_price)
            logger.warning(
                "  → [LIVE] Sell failed but price=%.3f ≈ 0.0 — closing bet #%d as lost",
                current_price, bet["id"],
            )
        else:
            logger.error(
                "  → [LIVE] Sell order failed — bet #%d remains open, check agent.log",
                bet["id"],
            )


def _check_single(bet) -> None:
    detail = fetcher.fetch_market_detail(bet["market_id"])
    if not detail:
        return

    closed   = detail.get("closed", False)
    resolved = detail.get("resolved", False)

    outcome_prices = _parse_outcome_prices(detail)

    if not (closed or resolved):
        # Market still live — check stop-loss / take-profit
        _check_exit_triggers(bet, outcome_prices)
        return


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
