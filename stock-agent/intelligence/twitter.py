"""
Twitter/X intelligence monitor via Nitter RSS.

Uses public Nitter instances to fetch tweets as RSS — no account or API key needed.
Falls back through a list of instances if one is down or rate-limiting.

For accounts that publish their own RSS (e.g. SemiAnalysis substack),
a direct feed URL is used instead of Nitter.

Runtime:
    fetch_new_tweets(seen_ids) → list[dict]   called from main scan loop
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger("intel.twitter")

# ── Nitter instance pool ──────────────────────────────────────────────────────
# Tried in order; first one that returns entries wins.
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.1d4.us",
    "https://nitter.kavin.rocks",
]

# ── Watched accounts ──────────────────────────────────────────────────────────
# Format: { "handle": { "description": ..., "rss_override": ... } }
# Set rss_override to use a direct RSS feed instead of Nitter (no scraping needed).
WATCHED_ACCOUNTS: dict[str, dict] = {
    "zephyr_z9": {
        "description":    "Semiconductor supply chain — components, substrates, fab capacity",
        "rss_override":   None,
    },
    "TechInsightsInc": {
        "description":    "Chiplet / die teardown + process node analysis",
        "rss_override":   None,
    },
    "SemiAnalysis": {
        "description":    "Foundry economics, AI chip demand, CoWoS/HBM deep dives",
        "rss_override":   "https://semianalysis.com/feed",   # own site — no Nitter needed
    },
    "IanCutress": {
        "description":    "CPU/GPU architecture + fab process coverage",
        "rss_override":   None,
    },
    "dylan522p": {
        "description":    "GPU supply chain + VRAM component tracking",
        "rss_override":   None,
    },
}

MAX_ITEMS_PER_ACCOUNT = 10


# ── RSS helpers ───────────────────────────────────────────────────────────────

def _fetch_rss(url: str, timeout: int = 10) -> list:
    """Return feedparser entries for a URL, or [] on failure."""
    try:
        import feedparser
        feed = feedparser.parse(url, request_headers={"User-Agent": "silicon-intel/1.0"})
        if feed.get("bozo") and not feed.entries:
            return []
        return feed.entries
    except ImportError:
        logger.error("feedparser not installed — run: pip install feedparser")
        return []
    except Exception as exc:
        logger.debug("RSS fetch failed for %s: %s", url, exc)
        return []


def _nitter_url(instance: str, handle: str) -> str:
    return f"{instance}/{handle}/rss"


def _fetch_account(handle: str, account_cfg: dict) -> list[dict]:
    """Fetch recent posts for one account. Returns normalized tweet dicts."""

    # Direct RSS override (e.g. Substack / own site)
    override = account_cfg.get("rss_override")
    if override:
        entries = _fetch_rss(override)
        if entries:
            logger.debug("@%s: %d items via direct RSS", handle, len(entries))
            return _parse_entries(handle, entries)

    # Try Nitter instances in order
    for instance in NITTER_INSTANCES:
        url = _nitter_url(instance, handle)
        entries = _fetch_rss(url)
        if entries:
            logger.debug("@%s: %d items via %s", handle, len(entries), instance)
            return _parse_entries(handle, entries)
        time.sleep(0.5)  # brief pause between instance attempts

    logger.warning("@%s: all Nitter instances failed", handle)
    return []


def _parse_entries(handle: str, entries: list) -> list[dict]:
    """Normalize feedparser entries into tweet dicts."""
    results = []
    for entry in entries[:MAX_ITEMS_PER_ACCOUNT]:
        # ID: use the entry link or id as a stable identifier
        entry_id = entry.get("id") or entry.get("link") or ""
        # Derive a stable integer-ish key from the URL (last path segment or hash)
        tweet_id = _stable_id(entry_id)

        title   = entry.get("title", "")
        summary = entry.get("summary", entry.get("description", ""))
        # Prefer summary (full text) over title (truncated)
        text = summary if len(summary) > len(title) else title
        # Strip HTML tags
        text = _strip_html(text)

        published = entry.get("published", entry.get("updated", ""))
        link      = entry.get("link", "")

        results.append({
            "id":         tweet_id,
            "handle":     handle,
            "text":       text.strip()[:500],
            "url":        link,
            "created_at": published,
            "likes":      0,   # Nitter RSS doesn't expose engagement metrics
            "retweets":   0,
            "views":      0,
        })
    return results


def _stable_id(url: str) -> int:
    """Derive a stable integer ID from a URL string."""
    import hashlib
    return int(hashlib.md5(url.encode()).hexdigest()[:12], 16)


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    import re
    return re.sub(r"<[^>]+>", " ", text).strip()


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_new_tweets(seen_ids: set[int]) -> list[dict]:
    """
    Fetch recent posts from all watched accounts, skipping already-seen IDs.
    Returns list of new tweet dicts. Compatible with the main scan loop.
    """
    all_tweets: list[dict] = []

    for handle, cfg in WATCHED_ACCOUNTS.items():
        tweets = _fetch_account(handle, cfg)
        for t in tweets:
            if t["id"] not in seen_ids:
                all_tweets.append(t)

    logger.info(
        "Twitter/Nitter: %d new item(s) from %d accounts",
        len(all_tweets), len(WATCHED_ACCOUNTS),
    )
    return all_tweets


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import logging as _logging, sys
    _logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s — %(message)s")

    handle_filter = sys.argv[1] if len(sys.argv) > 1 else None
    accounts = (
        {handle_filter: WATCHED_ACCOUNTS[handle_filter]}
        if handle_filter and handle_filter in WATCHED_ACCOUNTS
        else WATCHED_ACCOUNTS
    )

    for handle, cfg in accounts.items():
        print(f"\n── @{handle} — {cfg['description']} ──")
        tweets = _fetch_account(handle, cfg)
        if not tweets:
            print("  (no items fetched)")
        for t in tweets[:5]:
            print(f"  [{t['created_at'][:16]}] {t['text'][:120]}")
            print(f"           {t['url']}")
