import logging
import math
import statistics
from dataclasses import dataclass, field
from typing import Optional

import config
import database
from signals import compute_edge, kelly_stake as _calc_kelly, _infer_category

logger = logging.getLogger(__name__)


@dataclass
class BetCandidate:
    market_id: str
    condition_id: str
    question: str
    outcome: str
    outcome_index: int
    token_id: str
    probability: float
    score: float
    volume_24h: float
    spread: float
    edge:        Optional[float] = None
    true_prob:   Optional[float] = None
    kelly_stake: float           = 100.0


# ---------------------------------------------------------------------------
# Individual signal scorers
# ---------------------------------------------------------------------------

def _probability_score(prob: float) -> float:
    """
    Sweet-spot scoring: peak at 0.83, falls to 0 at edges MIN_PROBABILITY and MAX_PROBABILITY.
    Triangle shape — rewards the high-confidence-but-not-certain sweet spot.
    """
    if prob < config.MIN_PROBABILITY or prob > config.MAX_PROBABILITY:
        return 0.0
    peak = 0.83
    if prob <= peak:
        # Rising leg: MIN → 0, peak → 1
        return (prob - config.MIN_PROBABILITY) / (peak - config.MIN_PROBABILITY)
    else:
        # Falling leg: peak → 1, MAX → 0
        return (config.MAX_PROBABILITY - prob) / (config.MAX_PROBABILITY - peak)


def _volume_score(volume_24h: float) -> float:
    """Log-scale normalised against $500K ceiling."""
    if volume_24h <= 0:
        return 0.0
    ceiling = math.log10(500_000)
    return min(math.log10(max(volume_24h, 1)) / ceiling, 1.0)


def _stability_score(market_id: str) -> float:
    """
    1 - std_dev of last-2h prices.
    Returns 0.5 (neutral) when there is insufficient history.
    """
    prices = database.get_price_history(market_id, hours=2)
    if len(prices) < 3:
        return 0.5
    std = statistics.stdev(prices)
    return max(0.0, 1.0 - std)


def _spread_score(spread: float) -> float:
    """Linear: 0% spread → 1.0, 10% spread → 0.0."""
    return max(0.0, 1.0 - spread / 0.10)


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def _composite_score(
    prob: float,
    volume_24h: float,
    market_id: str,
    spread: float,
) -> tuple[float, float, float, float, float]:
    prob_s  = _probability_score(prob)
    vol_s   = _volume_score(volume_24h)
    stab_s  = _stability_score(market_id)
    spr_s   = _spread_score(spread)

    composite = (
        prob_s  * config.WEIGHT_PROBABILITY +
        vol_s   * config.WEIGHT_VOLUME      +
        stab_s  * config.WEIGHT_STABILITY   +
        spr_s   * config.WEIGHT_SPREAD
    )
    return composite, prob_s, vol_s, stab_s, spr_s


# ---------------------------------------------------------------------------
# Market parsing helpers
# ---------------------------------------------------------------------------

def _parse_outcome_prices(market: dict) -> list[float]:
    """
    outcomePrices may be a JSON string like '["0.82","0.18"]' or a list.
    Returns a list of floats.
    """
    raw = market.get("outcomePrices", [])
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    try:
        return [float(p) for p in raw]
    except Exception:
        return []


def _parse_clob_token_ids(market: dict) -> list[str]:
    """
    clobTokenIds may be a JSON string or a list.
    Returns a list of token-id strings.
    """
    raw = market.get("clobTokenIds", [])
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    return [str(t) for t in raw]


def _parse_outcomes(market: dict) -> list[str]:
    raw = market.get("outcomes", [])
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    return [str(o) for o in raw]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_markets(markets: list[dict]) -> list[BetCandidate]:
    """
    Score all markets and return candidates that pass the MIN_SCORE threshold,
    sorted by composite score descending.
    """
    candidates: list[BetCandidate] = []

    for market in markets:
        try:
            _score_single(market, candidates)
        except Exception as exc:
            logger.debug("Skipping market %s: %s", market.get("id", "?"), exc)

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def _score_single(market: dict, candidates: list[BetCandidate]) -> None:
    market_id    = market.get("id", "")
    condition_id = market.get("conditionId", market.get("condition_id", ""))
    question     = market.get("question", "")

    if not market_id or not condition_id:
        return

    # Volume filter
    volume_24h = float(market.get("volume24hr", market.get("volume", 0)) or 0)
    if volume_24h < config.MIN_VOLUME_24H:
        return

    outcome_prices = _parse_outcome_prices(market)
    outcomes       = _parse_outcomes(market)
    token_ids      = _parse_clob_token_ids(market)

    if not outcome_prices or not outcomes:
        return

    # Find highest-probability outcome in the sweet spot
    best_idx: Optional[int] = None
    best_prob = 0.0
    for i, prob in enumerate(outcome_prices):
        if config.MIN_PROBABILITY <= prob <= config.MAX_PROBABILITY and prob > best_prob:
            best_prob = prob
            best_idx  = i

    if best_idx is None:
        return

    # Token id (kept for reference, not used for spread)
    token_id = token_ids[best_idx] if best_idx < len(token_ids) else ""

    # Use spread already present in market response — avoids slow/inverted CLOB calls
    spread_raw = market.get("spread")
    if spread_raw is not None:
        spread = abs(float(spread_raw))
    else:
        # Derive from bestBid/bestAsk if available
        best_bid = market.get("bestBid")
        best_ask = market.get("bestAsk")
        if best_bid is not None and best_ask is not None:
            spread = abs(float(best_ask) - float(best_bid))
        else:
            spread = 0.03  # neutral fallback

    if spread > config.MAX_SPREAD:
        return

    # Skip if already holding an open bet on this market
    if database.is_market_open(market_id):
        return

    composite, *_ = _composite_score(best_prob, volume_24h, market_id, spread)

    if composite < config.MIN_SCORE:
        return

    outcome_name = outcomes[best_idx] if best_idx < len(outcomes) else f"Outcome {best_idx}"

    # --- Implied-edge filter + Kelly sizing ---
    category = _infer_category(question)
    edge, true_prob = compute_edge(question, category, best_prob)

    if edge is not None and edge < config.MIN_EDGE:
        return  # signal available but edge too thin

    stake = float(config.VIRTUAL_BET_SIZE)  # fallback when signal unavailable
    if true_prob is not None:
        s = _calc_kelly(
            true_prob, best_prob,
            config.VIRTUAL_BANKROLL, config.KELLY_FRACTION,
            config.MIN_BET_SIZE, config.MAX_BET_SIZE,
        )
        stake = s if s > 0 else float(config.VIRTUAL_BET_SIZE)

    candidates.append(BetCandidate(
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
        edge         = edge,
        true_prob    = true_prob,
        kelly_stake  = round(stake, 2),
    ))
