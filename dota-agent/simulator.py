import logging
from analyzer import DotaBetCandidate
import database

logger = logging.getLogger(__name__)


def place_dry_bet(candidate: DotaBetCandidate) -> bool:
    """
    Record a simulated Dota bet for `candidate`.

    Returns True if the bet was placed, False if skipped
    (e.g. market already has an open bet).
    """
    if database.is_market_open(candidate.market_id):
        logger.debug("Skipping market %s — already have open bet", candidate.market_id)
        return False

    virtual_amount   = round(candidate.kelly_stake, 2)
    potential_payout = virtual_amount / candidate.probability
    expected_value   = potential_payout * candidate.true_prob - virtual_amount

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
        team_a           = candidate.team_a,
        team_b           = candidate.team_b,
        tournament       = candidate.tournament,
        edge             = candidate.edge,
        true_prob        = candidate.true_prob,
        elo_prob         = candidate.elo_prob,
        form_a           = candidate.form_a,
        form_b           = candidate.form_b,
        h2h_winrate      = candidate.h2h_winrate,
        h2h_sample       = candidate.h2h_sample,
        league_tier      = candidate.league_tier,
        kelly_stake      = candidate.kelly_stake,
    )

    form_str = ""
    if candidate.form_a is not None and candidate.form_b is not None:
        form_str = f" | form={candidate.form_a:.0%}/{candidate.form_b:.0%}"
    h2h_str = ""
    if candidate.h2h_sample >= 3:
        h2h_str = f" | h2h={candidate.h2h_winrate:.0%}({candidate.h2h_sample})"

    logger.info(
        "[DRY RUN] Bet #%d | %s → %s | mkt=%.2f%% true=%.2f%% edge=%+.1f%% | "
        "score=%.3f | tier=%s | stake=$%.0f | payout=$%.2f | EV=$%.2f%s%s",
        bet_id,
        candidate.question[:55],
        candidate.outcome[:20],
        candidate.probability * 100,
        candidate.true_prob * 100,
        candidate.edge * 100,
        candidate.score,
        candidate.league_tier,
        virtual_amount,
        potential_payout,
        expected_value,
        form_str,
        h2h_str,
    )
    return True
