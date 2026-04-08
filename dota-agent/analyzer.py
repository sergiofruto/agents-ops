import logging
from dataclasses import dataclass
from typing import Optional

import config
import database
import fetcher
import opendota

logger = logging.getLogger(__name__)


@dataclass
class DotaBetCandidate:
    market_id:     str
    condition_id:  str
    question:      str
    outcome:       str
    outcome_index: int
    token_id:      str
    probability:   float
    score:         float
    volume_24h:    float
    spread:        float
    team_a:        str
    team_b:        str
    tournament:    str
    edge:          float
    true_prob:     float
    elo_prob:      Optional[float] = None
    form_a:        Optional[float] = None
    form_b:        Optional[float] = None
    h2h_winrate:   Optional[float] = None
    h2h_sample:    int             = 0
    league_tier:   str             = "unknown"
    kelly_stake:   float           = 100.0


# ---------------------------------------------------------------------------
# Signal scorers
# ---------------------------------------------------------------------------

def _edge_score(edge: float) -> float:
    """Normalise edge against 20% ceiling."""
    return min(edge / 0.20, 1.0)


def _form_score(form_a: Optional[float]) -> float:
    """Linear from 40% win rate (→0) to 80% win rate (→1). Neutral when unknown."""
    if form_a is None:
        return 0.5
    return min(max((form_a - 0.40) / 0.40, 0.0), 1.0)


def _h2h_score(h2h_winrate: float, h2h_sample: int) -> float:
    """H2H win rate with confidence weighting; 0.5 when neutral."""
    if h2h_sample < 3:
        return 0.5  # insufficient data — neutral
    confidence = min(h2h_sample / 15, 1.0)
    return 0.5 + (h2h_winrate - 0.5) * confidence


def _tournament_score(tier: str) -> float:
    return {"premium": 1.0, "professional": 0.7, "amateur": 0.3}.get(tier, 0.5)


def _composite_score(
    edge: float,
    form_a: Optional[float],
    h2h_winrate: float,
    h2h_sample: int,
    league_tier: str,
) -> float:
    edge_s  = _edge_score(edge)
    form_s  = _form_score(form_a)
    h2h_s   = _h2h_score(h2h_winrate, h2h_sample)
    tour_s  = _tournament_score(league_tier)

    return (
        edge_s  * config.WEIGHT_EDGE       +
        form_s  * config.WEIGHT_FORM       +
        h2h_s   * config.WEIGHT_H2H        +
        tour_s  * config.WEIGHT_TOURNAMENT
    )


def _kelly_stake(true_prob: float, market_prob: float) -> float:
    """Half-Kelly stake; clamped to [MIN_BET_SIZE, MAX_BET_SIZE]."""
    b = (1.0 / market_prob) - 1.0  # decimal odds minus 1
    q = 1.0 - true_prob
    kelly_full = (true_prob * b - q) / b
    if kelly_full <= 0:
        return 0.0
    half_kelly_fraction = kelly_full * config.KELLY_FRACTION
    stake = half_kelly_fraction * config.VIRTUAL_BANKROLL
    return float(max(config.MIN_BET_SIZE, min(config.MAX_BET_SIZE, stake)))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_markets(markets: list[dict]) -> list[DotaBetCandidate]:
    """
    Score all Dota markets and return candidates above MIN_SCORE,
    sorted by composite score descending.
    """
    candidates: list[DotaBetCandidate] = []

    # Count how many are skipped purely because prices are outside the window
    # (i.e. market exists but is already resolved / not yet priced)
    outside_range = 0
    for market in markets:
        prices = fetcher.parse_outcome_prices(market)
        if prices and not any(config.MIN_PROBABILITY <= p <= config.MAX_PROBABILITY for p in prices):
            outside_range += 1

    if outside_range:
        logger.info(
            "%d Dota market(s) found but all prices outside [%.0f%%, %.0f%%] "
            "(likely already resolved or pre-game) — no bets placed",
            outside_range,
            config.MIN_PROBABILITY * 100,
            config.MAX_PROBABILITY * 100,
        )

    for market in markets:
        try:
            _score_single(market, candidates)
        except Exception as exc:
            logger.debug("Skipping market %s: %s", market.get("id", "?"), exc)

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def _score_single(market: dict, candidates: list[DotaBetCandidate]) -> None:
    market_id    = market.get("id", "")
    condition_id = market.get("conditionId", market.get("condition_id", ""))
    question     = market.get("question", "")

    if not market_id or not condition_id:
        return

    # Volume filter
    volume_24h = float(market.get("volume24hr", market.get("volume", 0)) or 0)
    if volume_24h < config.MIN_VOLUME_24H:
        return

    outcome_prices = fetcher.parse_outcome_prices(market)
    outcomes       = fetcher.parse_outcomes(market)
    token_ids      = fetcher.parse_clob_token_ids(market)

    if not outcome_prices or not outcomes:
        return

    # Find highest-probability outcome in the sweet spot (team_a win)
    best_idx: Optional[int] = None
    best_prob = 0.0
    for i, prob in enumerate(outcome_prices):
        if config.MIN_PROBABILITY <= prob <= config.MAX_PROBABILITY and prob > best_prob:
            best_prob = prob
            best_idx  = i

    if best_idx is None:
        return

    token_id = token_ids[best_idx] if best_idx < len(token_ids) else ""

    # Spread
    spread_raw = market.get("spread")
    if spread_raw is not None:
        spread = abs(float(spread_raw))
    else:
        best_bid = market.get("bestBid")
        best_ask = market.get("bestAsk")
        if best_bid is not None and best_ask is not None:
            spread = abs(float(best_ask) - float(best_bid))
        else:
            spread = 0.04  # neutral fallback

    if spread > config.MAX_SPREAD:
        return

    # Dedup
    if database.is_market_open(market_id):
        return

    # Parse teams
    teams = fetcher.parse_match_teams(market)
    if not teams:
        logger.debug("Could not parse teams from: %r", question)
        return
    team_a_name, team_b_name = teams

    # The winning outcome selected (best_idx 0 → team_a, idx 1 → team_b usually)
    # If team_b is favoured (best_idx == 1), swap perspective so team_a is always
    # the modelled team.
    outcome_name = outcomes[best_idx] if best_idx < len(outcomes) else f"Outcome {best_idx}"

    # Determine which team we're betting on from market outcome label
    # outcome label is typically the team name directly
    betting_on = outcome_name.strip()
    if best_idx == 0:
        model_team_a, model_team_b = team_a_name, team_b_name
    else:
        model_team_a, model_team_b = team_b_name, team_a_name

    # Compute true probability via OpenDota
    signals = opendota.compute_true_prob(model_team_a, model_team_b, market)
    if signals is None:
        return  # team resolution failed; skip

    true_prob   = signals["true_prob"]
    elo_prob    = signals["elo_prob"]
    form_a      = signals["form_a"]
    form_b      = signals["form_b"]
    h2h_winrate = signals["h2h_winrate"]
    h2h_sample  = signals["h2h_sample"]
    league_tier = signals["league_tier"]

    edge = true_prob - best_prob
    if edge < config.MIN_EDGE:
        return  # insufficient edge

    composite = _composite_score(edge, form_a, h2h_winrate, h2h_sample, league_tier)
    if composite < config.MIN_SCORE:
        return

    stake = _kelly_stake(true_prob, best_prob)
    if stake <= 0:
        stake = float(config.VIRTUAL_BET_SIZE)

    # Derive tournament name from market tags or question
    tournament = market.get("groupItemTitle", market.get("category", "Unknown"))

    candidates.append(DotaBetCandidate(
        market_id    = market_id,
        condition_id = condition_id,
        question     = question,
        outcome      = outcome_name,
        outcome_index = best_idx,
        token_id     = token_id,
        probability  = best_prob,
        score        = round(composite, 4),
        volume_24h   = volume_24h,
        spread       = spread,
        team_a       = model_team_a,
        team_b       = model_team_b,
        tournament   = str(tournament) if tournament else "Unknown",
        edge         = round(edge, 4),
        true_prob    = true_prob,
        elo_prob     = elo_prob,
        form_a       = form_a,
        form_b       = form_b,
        h2h_winrate  = h2h_winrate,
        h2h_sample   = h2h_sample,
        league_tier  = league_tier,
        kelly_stake  = round(stake, 2),
    ))
