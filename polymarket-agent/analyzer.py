import logging
import math
import re
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
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
    edge:           Optional[float] = None
    true_prob:      Optional[float] = None
    kelly_stake:    float           = 100.0
    days_to_expiry: Optional[int]   = None


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
    """Log-scale normalised against $50K ceiling.
    Most quality Polymarket markets sit in the $5K–$50K range;
    a $500K ceiling compresses that range and reduces discrimination.
    """
    if volume_24h <= 0:
        return 0.0
    ceiling = math.log10(50_000)
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


_MONTH_NAMES = ['january','february','march','april','may','june',
                'july','august','september','october','november','december']

def _parse_days_to_expiry(close_date) -> Optional[int]:
    """
    Parse close_date → days until expiry.
    Handles: ISO timestamps, 'April 30', 'by June 30, 2026', 'end of April',
             bare years ('2028'), ordinals ('April 30th'), date ranges (uses last date).
    """
    if not close_date:
        return None
    if not isinstance(close_date, str):
        try:
            dt = close_date
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return max(0, (dt - datetime.now(timezone.utc)).days)
        except Exception:
            return None

    s = close_date.strip()

    # 1. ISO / RFC date: 2026-04-30T... or 2026-04-30
    if re.search(r'\d{4}-\d{2}-\d{2}', s):
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return max(0, (dt - datetime.now(timezone.utc)).days)
        except Exception:
            pass

    sl = s.lower()
    now = datetime.now(timezone.utc)

    # 2. Bare year: "2028" or "by 2028" → Dec 31 of that year
    year_only = re.search(r'\b(20\d{2})\b', sl)
    month_match = re.search(
        r'\b(' + '|'.join(_MONTH_NAMES) + r')\b'
        r'(?:\s+(\d{1,2})(?:st|nd|rd|th)?)?'
        r'(?:,?\s*(20\d{2}))?',
        sl
    )

    if month_match:
        # Use last occurrence for date ranges ("Feb 23 – March 1")
        all_months = list(re.finditer(
            r'\b(' + '|'.join(_MONTH_NAMES) + r')\b'
            r'(?:\s+(\d{1,2})(?:st|nd|rd|th)?)?'
            r'(?:,?\s*(20\d{2}))?',
            sl
        ))
        m = all_months[-1]
        month_num = _MONTH_NAMES.index(m.group(1)) + 1
        day  = int(m.group(2)) if m.group(2) else 28
        year = int(m.group(3)) if m.group(3) else now.year
        # If parsed date is in the past, assume next year
        try:
            dt = datetime(year, month_num, day, tzinfo=timezone.utc)
            if dt < now and not m.group(3):
                dt = dt.replace(year=now.year + 1)
            return max(0, (dt - now).days)
        except ValueError:
            pass

    if year_only and not month_match:
        try:
            dt = datetime(int(year_only.group(1)), 12, 31, tzinfo=timezone.utc)
            return max(0, (dt - now).days)
        except Exception:
            pass

    return None


def _expiry_score(close_date) -> float:
    """
    Reward near-term resolution — faster capital cycle, lower variance exposure.

    Score shape:
      < 1 day  → 0.0  (too late to act / already settled)
      1–2 days → 0.5  (very imminent, risky to enter)
      3–30 days → 1.0 (sweet spot)
      31–90 days → linear decay to 0.3
      > 90 days  → 0.1 (long-dated; high variance, slow cycle)
      unknown    → 0.4 (mild penalty)
    """
    days = _parse_days_to_expiry(close_date)
    if days is None:
        return 0.4
    if days <= 0:
        return 0.0
    if days <= 2:
        return 0.5
    if days <= 30:
        return 1.0
    if days <= 90:
        return 1.0 - 0.7 * (days - 30) / 60  # 1.0 → 0.3
    return 0.1


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def _composite_score(
    prob: float,
    volume_24h: float,
    market_id: str,
    spread: float,
    close_date=None,
) -> tuple[float, float, float, float, float, float]:
    prob_s   = _probability_score(prob)
    vol_s    = _volume_score(volume_24h)
    stab_s   = _stability_score(market_id)
    spr_s    = _spread_score(spread)
    expiry_s = _expiry_score(close_date)

    composite = (
        prob_s   * config.WEIGHT_PROBABILITY +
        vol_s    * config.WEIGHT_VOLUME      +
        stab_s   * config.WEIGHT_STABILITY   +
        spr_s    * config.WEIGHT_SPREAD      +
        expiry_s * config.WEIGHT_EXPIRY
    )
    return composite, prob_s, vol_s, stab_s, spr_s, expiry_s


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

# Canonical coin name extracted from a question, used for correlation detection.
_COIN_ALIASES: dict[str, str] = {
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "solana": "solana", "sol": "solana",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "ripple": "ripple", "xrp": "ripple",
    "cardano": "cardano", "ada": "cardano",
    "bnb": "bnb", "binance": "bnb",
    "avalanche": "avalanche", "avax": "avalanche",
    "polygon": "polygon", "matic": "polygon",
}


def _extract_coin(question: str) -> Optional[str]:
    """Return canonical coin name if the question is about a specific crypto asset."""
    q = question.lower()
    for alias, canonical in _COIN_ALIASES.items():
        if alias in q:
            return canonical
    return None


def _is_correlated_with_open(candidate: BetCandidate, open_bets: list) -> bool:
    """
    Return True if the candidate is correlated with an existing open bet.
    Detected case: same coin + same outcome direction (both No, or both Yes).
    Rationale: "Will BTC reach $80K? No" and "Will BTC reach $82.5K? No" are
    effectively the same directional thesis on BTC price — holding both doubles
    exposure without diversifying.
    """
    coin = _extract_coin(candidate.question)
    if coin is None:
        return False

    direction = candidate.outcome.strip().lower()
    for bet in open_bets:
        if _extract_coin(bet["question"]) == coin and bet["outcome"].strip().lower() == direction:
            logger.info(
                "Correlation filter: skipping '%s' (coin=%s, outcome=%s) — "
                "already holding correlated bet '%s'",
                candidate.question[:60], coin, candidate.outcome,
                bet["question"][:60],
            )
            return True
    return False


def score_markets(markets: list[dict]) -> list[BetCandidate]:
    """
    Score all markets, then apply risk filters before returning candidates.

    Filters applied (in order, after scoring):
      1. Category cap  — skip if open bets in same category >= MAX_BETS_PER_CATEGORY
      2. Correlation   — skip crypto bets in the same direction on the same coin
    Both filters also account for candidates already selected in this scan cycle,
    so placing 5 BTC bets in a single scan is not possible even if the DB is empty.
    """
    candidates: list[BetCandidate] = []

    for market in markets:
        try:
            _score_single(market, candidates)
        except Exception as exc:
            logger.debug("Skipping market %s: %s", market.get("id", "?"), exc)

    candidates.sort(key=lambda c: c.score, reverse=True)

    # ── Build current open-bet state ──────────────────────────────────────────
    open_bets = database.get_open_bets()

    # Category counts from existing open bets
    category_counts: dict[str, int] = {}
    for bet in open_bets:
        cat = _infer_category(bet["question"])
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # ── Greedy filter: best score first ──────────────────────────────────────
    # We track a mutable list of "virtual open bets" that includes both DB open
    # bets and candidates already accepted this scan, so intra-scan correlation
    # is caught too.
    virtual_open = list(open_bets)  # sqlite3.Row objects; accessed via ["key"]

    filtered: list[BetCandidate] = []
    for c in candidates:
        cat = _infer_category(c.question)

        # 1. Category cap
        if category_counts.get(cat, 0) >= config.MAX_BETS_PER_CATEGORY:
            logger.info(
                "Category cap: skipping '%s' — '%s' already at %d open bet(s)",
                c.question[:60], cat, category_counts[cat],
            )
            continue

        # 2. Correlation filter
        if _is_correlated_with_open(c, virtual_open):
            continue

        filtered.append(c)
        category_counts[cat] = category_counts.get(cat, 0) + 1

        # Add a dict proxy so _extract_coin / outcome lookups work on it
        virtual_open.append({"question": c.question, "outcome": c.outcome})  # type: ignore[arg-type]

    return filtered


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

    # Skip if already holding an open bet, or recently resolved (cooldown)
    if database.is_market_open(market_id):
        return
    if database.is_market_on_cooldown(market_id, config.MARKET_COOLDOWN_DAYS):
        return

    close_date = market.get("endDateIso") or market.get("endDate")

    # Hard cutoff: skip very long-dated markets (low capital efficiency, high variance)
    dte = _parse_days_to_expiry(close_date)
    if dte is not None and dte > config.MAX_DAYS_TO_EXPIRY:
        return

    composite, *_ = _composite_score(best_prob, volume_24h, market_id, spread, close_date)

    if composite < config.MIN_SCORE:
        return

    outcome_name = outcomes[best_idx] if best_idx < len(outcomes) else f"Outcome {best_idx}"

    # --- Implied-edge filter + Kelly sizing ---
    category = _infer_category(question)
    edge, true_prob = compute_edge(question, category, best_prob, close_date)

    # compute_edge returns P(affirmative event in question text).
    # When the selected outcome is "No" we are betting on the negation,
    # so flip true_prob and recompute edge.
    if true_prob is not None and outcome_name.strip().lower() == "no":
        true_prob = 1.0 - true_prob
        edge = true_prob - best_prob

    if edge is not None and edge < config.MIN_EDGE:
        return  # signal available but edge too thin

    stake = float(config.VIRTUAL_BET_SIZE)  # fallback when signal unavailable
    if true_prob is not None:
        live_bankroll = database.get_live_bankroll(config.VIRTUAL_BANKROLL)
        s = _calc_kelly(
            true_prob, best_prob,
            live_bankroll, config.KELLY_FRACTION,
            config.MIN_BET_SIZE, config.MAX_BET_SIZE,
        )
        stake = s if s > 0 else float(config.VIRTUAL_BET_SIZE)

    candidates.append(BetCandidate(
        market_id      = market_id,
        condition_id   = condition_id,
        question       = question,
        outcome        = outcome_name,
        outcome_index  = best_idx,
        token_id       = token_id,
        probability    = best_prob,
        score          = round(composite, 4),
        volume_24h     = volume_24h,
        spread         = spread,
        edge           = edge,
        true_prob      = true_prob,
        kelly_stake    = round(stake, 2),
        days_to_expiry = _parse_days_to_expiry(close_date),
    ))
