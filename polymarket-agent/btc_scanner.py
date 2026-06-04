"""
BTC threshold scanner — read-only sidecar that surfaces ranked
"Will Bitcoin reach $X by [date]" Polymarket markets.

v1 is detection + ranking + snapshot. NO bets are placed.
Promotion to live = separate spec.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from fetcher import fetch_active_markets
from analyzer import BetCandidate, score_markets

logger = logging.getLogger("polymarket.btc_scanner")

# Match: BTC keyword + threshold verb + dollar threshold (e.g. $80,000 or $100K)
_BTC_THRESHOLD_RE = re.compile(
    r"\b(?:bitcoin|btc)\b"
    r".*?\b(?:reach|hit|above|over|under|dip|cross|below|exceed|surpass)\b"
    r".*?\$\s?(?:\d{1,3}(?:,\d{3})+|\d{2,6})\s?[Kk]?",
    re.IGNORECASE | re.DOTALL,
)


def is_btc_threshold(question: str) -> bool:
    """Return True if the market question looks like a BTC price-threshold market."""
    if not question:
        return False
    return bool(_BTC_THRESHOLD_RE.search(question))


def find_btc_threshold_candidates(limit: int = 20) -> list[BetCandidate]:
    """
    Read-only: pull all active markets, keep only BTC threshold ones,
    score via the existing analyzer, return top `limit` ranked by edge * score.
    """
    raw = fetch_active_markets()
    btc_only = [m for m in raw if is_btc_threshold(m.get("question", ""))]
    logger.info(
        "btc_scanner: %d/%d markets match BTC threshold pattern",
        len(btc_only), len(raw),
    )
    if not btc_only:
        return []

    candidates: list[BetCandidate] = score_markets(btc_only)

    def _rank_key(c: BetCandidate) -> float:
        edge = c.edge if c.edge is not None else 0.0
        return edge * c.score

    candidates.sort(key=_rank_key, reverse=True)
    return candidates[:limit]


def snapshot(candidates: list[BetCandidate], path: Path) -> None:
    """Write a JSON snapshot of ranked BTC candidates. Overwrites each cycle."""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(candidates),
        "candidates": [
            {
                "market_id":      c.market_id,
                "condition_id":   c.condition_id,
                "question":       c.question,
                "outcome":        c.outcome,
                "token_id":       c.token_id,
                "probability":    c.probability,
                "score":          round(c.score, 4),
                "edge":           round(c.edge, 4) if c.edge is not None else None,
                "true_prob":      round(c.true_prob, 4) if c.true_prob is not None else None,
                "kelly_stake":    round(c.kelly_stake, 2),
                "days_to_expiry": c.days_to_expiry,
                "volume_24h":     c.volume_24h,
                "spread":         c.spread,
            }
            for c in candidates
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
