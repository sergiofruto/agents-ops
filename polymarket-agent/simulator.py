import logging
from analyzer import BetCandidate
import config
import database

logger = logging.getLogger(__name__)


def place_dry_bet(candidate: BetCandidate) -> bool:
    """
    Record a simulated bet for `candidate`.

    Returns True if the bet was placed, False if it was skipped
    (e.g. market already has an open bet).
    """
    if database.is_market_open(candidate.market_id):
        logger.debug("Skipping market %s — already have open bet", candidate.market_id)
        return False

    virtual_amount   = round(candidate.kelly_stake, 2)
    # Payout if the outcome wins (settles at $1)
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
    )

    edge_str = f" | edge={candidate.edge:+.1%}" if candidate.edge is not None else ""
    logger.info(
        "[DRY RUN] Placed bet #%d | %s → %s | p=%.2f%% | score=%.3f | "
        "stake=$%.0f | payout=$%.2f | EV=$%.2f%s",
        bet_id,
        candidate.question[:60],
        candidate.outcome,
        candidate.probability * 100,
        candidate.score,
        virtual_amount,
        potential_payout,
        expected_value,
        edge_str,
    )
    return True
