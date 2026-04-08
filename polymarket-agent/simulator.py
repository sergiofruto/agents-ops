import logging
from typing import Optional
from analyzer import BetCandidate
import config
import database

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry-point — routes to dry-run or live based on DRY_RUN flag
# ---------------------------------------------------------------------------

def place_bet(candidate: BetCandidate) -> bool:
    """Place a bet — dry-run (DB only) or live (CLOB order) depending on config."""
    if config.DRY_RUN:
        return _place_dry_bet(candidate)
    return _place_live_bet(candidate)


# Keep old name as alias so any external callers don't break.
def place_dry_bet(candidate: BetCandidate) -> bool:
    return _place_dry_bet(candidate)


# ---------------------------------------------------------------------------
# Dry-run path
# ---------------------------------------------------------------------------

def _place_dry_bet(candidate: BetCandidate) -> bool:
    if database.is_market_open(candidate.market_id):
        logger.debug("Skipping market %s — already have open bet", candidate.market_id)
        return False

    # Cap stakes when there is no edge signal — unguided bets get a small fixed max
    raw_stake = candidate.kelly_stake
    if candidate.true_prob is None:
        raw_stake = min(raw_stake, config.MAX_NO_SIGNAL_BET_SIZE)

    virtual_amount   = round(raw_stake, 2)
    potential_payout = virtual_amount / candidate.probability
    expected_value   = potential_payout * candidate.probability - virtual_amount

    bet_id = database.save_bet(
        market_id        = candidate.market_id,
        condition_id     = candidate.condition_id,
        question         = candidate.question,
        outcome          = candidate.outcome,
        outcome_index    = candidate.outcome_index,
        token_id         = candidate.token_id,
        price_at_bet     = candidate.probability,
        virtual_amount   = virtual_amount,
        potential_payout = potential_payout,
        score            = candidate.score,
        edge             = candidate.edge,
        kelly_stake      = candidate.kelly_stake,
        edge_available   = candidate.true_prob is not None,
        true_prob        = candidate.true_prob,
        days_to_expiry   = candidate.days_to_expiry,
    )

    if not bet_id:
        logger.debug("Skipping market %s — duplicate insert blocked by DB constraint", candidate.market_id)
        return False

    edge_str = f" | edge={candidate.edge:+.1%}" if candidate.edge is not None else ""
    days_str = f" | exp={candidate.days_to_expiry}d" if candidate.days_to_expiry is not None else ""
    logger.info(
        "[DRY RUN] Placed bet #%d | %s → %s | p=%.2f%% | score=%.3f | "
        "stake=$%.0f | payout=$%.2f | EV=$%.2f%s%s",
        bet_id,
        candidate.question[:60],
        candidate.outcome,
        candidate.probability * 100,
        candidate.score,
        virtual_amount,
        potential_payout,
        expected_value,
        edge_str,
        days_str,
    )
    return True


# ---------------------------------------------------------------------------
# Live path — real CLOB order
# ---------------------------------------------------------------------------

def get_clob_client():
    """Build an L2-authenticated ClobClient. Raises on missing config."""
    return _get_clob_client()


def _get_clob_client():
    """Build an L2-authenticated ClobClient. Raises on missing config."""
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds

    missing = [
        name for name, val in [
            ("POLY_PRIVATE_KEY",    config.POLY_PRIVATE_KEY),
            ("POLY_API_KEY",        config.POLY_API_KEY),
            ("POLY_API_SECRET",     config.POLY_API_SECRET),
            ("POLY_API_PASSPHRASE", config.POLY_API_PASSPHRASE),
        ] if not val
    ]
    if missing:
        raise RuntimeError(
            f"Live mode requires these .env vars: {', '.join(missing)}. "
            "Run python live_setup.py to generate API credentials."
        )

    from eth_account import Account
    derived = Account.from_key(config.POLY_PRIVATE_KEY).address.lower()
    is_proxy = bool(config.POLY_ADDRESS) and config.POLY_ADDRESS.lower() != derived
    sig_type = 1 if is_proxy else 0

    creds = ApiCreds(
        api_key        = config.POLY_API_KEY,
        api_secret     = config.POLY_API_SECRET,
        api_passphrase = config.POLY_API_PASSPHRASE,
    )
    return ClobClient(
        host           = config.CLOB_BASE,
        chain_id       = config.POLY_CHAIN_ID,
        key            = config.POLY_PRIVATE_KEY,
        creds          = creds,
        signature_type = sig_type,
        funder         = config.POLY_ADDRESS if is_proxy else None,
    )


def round_to_tick(price: float, tick: float) -> float:
    """Round price to the nearest valid tick increment (public alias)."""
    return _round_to_tick(price, tick)


def _round_to_tick(price: float, tick: float) -> float:
    """Round price to the nearest valid tick increment."""
    rounded = round(round(price / tick) * tick, 10)
    return max(tick, min(1.0 - tick, rounded))


def _place_live_bet(candidate: BetCandidate) -> bool:
    if database.is_market_open(candidate.market_id):
        logger.debug("Skipping market %s — already have open bet", candidate.market_id)
        return False

    # Never place a real order without a confirmed edge signal
    if candidate.edge is None:
        logger.debug("Skipping market %s — no edge signal (live mode requires signal)", candidate.market_id)
        return False

    try:
        from py_clob_client.clob_types import OrderArgs, PartialCreateOrderOptions

        client   = _get_clob_client()
        token_id = candidate.token_id

        if not token_id:
            logger.warning("Live bet skipped — no token_id for market %s", candidate.market_id)
            return False

        # Market parameters
        tick_size_str = client.get_tick_size(token_id)   # e.g. '0.01'
        tick          = float(tick_size_str)
        neg_risk      = client.get_neg_risk(token_id)

        price = _round_to_tick(candidate.probability, tick)
        # size = number of outcome-token shares; USDC spent ≈ price * size
        size  = round(candidate.kelly_stake / price, 2)

        # Guard: CLOB rejects orders below its minimum size.
        # Check actual USDC spend after tick-rounding, not the pre-rounding Kelly stake.
        usdc_spend = round(price * size, 2)
        if usdc_spend < config.MIN_LIVE_ORDER_USDC:
            logger.info(
                "Live bet skipped — order too small ($%.2f < $%.2f min) | market %s",
                usdc_spend, config.MIN_LIVE_ORDER_USDC, candidate.market_id,
            )
            return False

        order_args = OrderArgs(
            token_id = token_id,
            price    = price,
            size     = size,
            side     = "BUY",
        )
        options = PartialCreateOrderOptions(
            tick_size = tick_size_str,
            neg_risk  = neg_risk,
        )

        resp     = client.create_and_post_order(order_args, options)
        order_id = resp.get("orderID") or resp.get("order_id", "")
        status   = resp.get("status", "unknown")

        bet_id = database.save_bet(
            market_id        = candidate.market_id,
            condition_id     = candidate.condition_id,
            question         = candidate.question,
            outcome          = candidate.outcome,
            outcome_index    = candidate.outcome_index,
            token_id         = token_id,
            price_at_bet     = price,
            virtual_amount   = usdc_spend,
            potential_payout = round(size, 2),
            score            = candidate.score,
            edge             = candidate.edge,
            kelly_stake      = candidate.kelly_stake,
            order_id         = order_id,
            edge_available   = candidate.true_prob is not None,
            true_prob        = candidate.true_prob,
            days_to_expiry   = candidate.days_to_expiry,
        )

        if not bet_id:
            logger.warning("Live order posted but DB insert blocked (duplicate) — market %s order %s", candidate.market_id, order_id)
            return False

        edge_str = f" | edge={candidate.edge:+.1%}" if candidate.edge is not None else ""
        logger.info(
            "[LIVE] Order posted | bet #%d | order=%s | status=%s | "
            "%s → %s | p=%.2f%% | size=%.2f shares | spent=$%.2f%s",
            bet_id, order_id, status,
            candidate.question[:55],
            candidate.outcome,
            price * 100,
            size,
            usdc_spend,
            edge_str,
        )
        return True

    except Exception as exc:
        logger.error("Live bet failed for market %s: %s", candidate.market_id, exc)
        return False
