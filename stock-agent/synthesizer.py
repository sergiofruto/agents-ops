"""
Intelligence synthesizer — daily brief via Claude Sonnet.

Aggregates signals from:
  - Twitter (semiconductor insiders)
  - Infosec (CISA KEV, NVD, AWS bulletins)
  - Semicon (RSS feeds, price movers)

Produces a structured brief covering:
  1. Supply chain pulse (components under pressure)
  2. Threat landscape (hardware/ICS CVEs)
  3. Second-order implications (what it means for NVDA, TSMC, etc.)
  4. Watch list (things to monitor in the next 24-72h)
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("synthesizer")

BRIEF_CACHE_TTL = 3600 * 6  # Re-generate at most every 6 hours
_brief_cache: tuple[float, str] | None = None


# ── Signal summarizer helpers ─────────────────────────────────────────────────

def _format_tweets(tweets: list[dict], max_items: int = 12) -> str:
    if not tweets:
        return "No new tweets."
    lines = []
    for t in tweets[:max_items]:
        handle = t.get("handle", "?")
        text = t.get("text", "").replace("\n", " ").strip()[:200]
        likes = t.get("likes", 0)
        lines.append(f"  @{handle} [{likes}♥]: {text}")
    return "\n".join(lines)


def _format_cves(cves: list[dict], max_items: int = 8) -> str:
    if not cves:
        return "No new hardware CVEs."
    lines = []
    for c in cves[:max_items]:
        cve_id = c.get("cve_id", "")
        desc = c.get("description", "")[:120]
        score = c.get("cvss_score", "")
        vendor = c.get("vendor", "")
        src = c.get("source", "")
        score_str = f" [CVSS {score}]" if score else ""
        vendor_str = f" ({vendor})" if vendor else ""
        lines.append(f"  {cve_id}{score_str}{vendor_str} — {desc}")
    return "\n".join(lines)


def _format_news(items: list[dict], max_items: int = 10) -> str:
    if not items:
        return "No relevant news."
    lines = []
    for item in items[:max_items]:
        src = item.get("source", "")
        title = item.get("title", "")[:100]
        lines.append(f"  [{src}] {title}")
    return "\n".join(lines)


def _format_movers(movers: list[dict]) -> str:
    if not movers:
        return "No significant price moves."
    lines = []
    for m in movers:
        ticker = m.get("ticker", "")
        pct = m.get("pct_change", 0)
        price = m.get("curr_close", 0)
        lines.append(f"  {ticker:6s} {pct:+.1f}%  (${price:.2f})")
    return "\n".join(lines)


# ── Prompt builder ────────────────────────────────────────────────────────────

def _format_mining(items: list[dict], max_items: int = 10) -> str:
    if not items:
        return "No relevant mining/lithium news."
    lines = []
    for item in items[:max_items]:
        src   = item.get("source", "")
        if src in ("lithium-mover",):
            ticker = item.get("ticker", "")
            pct    = item.get("pct_change", 0)
            price  = item.get("curr_close", 0)
            desc   = item.get("description", "")
            lines.append(f"  [{src}] {ticker} {pct:+.1f}% (${price:.2f}) — {desc}")
        else:
            title = item.get("title", "")[:100]
            lines.append(f"  [{src}] {title}")
    return "\n".join(lines)


def _build_prompt(
    tweets: list[dict],
    cves: list[dict],
    news: list[dict],
    movers: list[dict],
) -> str:
    from intelligence.mining import SALTA_CONTEXT

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    infosec_news = [x for x in news if x.get("source") in ("CISA-KEV", "NVD", "AWS-Security")]
    semicon_news = [x for x in news if x.get("source") not in (
        "CISA-KEV", "NVD", "AWS-Security", "price-mover", "lithium-mover",
        "MiningPress AR", "Mining.com", "Kitco", "Ambito",
    )]
    mining_news  = [x for x in news if x.get("source") in (
        "MiningPress AR", "Mining.com", "Kitco", "Ambito", "lithium-mover",
    )]
    mining_movers = [x for x in movers if x.get("source") == "lithium-mover"]

    tweet_block   = _format_tweets(tweets)
    cve_block     = _format_cves(cves)
    semicon_block = _format_news(semicon_news)
    movers_block  = _format_movers(movers)
    mining_block  = _format_mining(mining_news + mining_movers)

    return f"""You are a senior technology and critical minerals intelligence analyst.
Areas of expertise: semiconductor supply chain, hardware security, and Argentine mining/lithium investment.
Today's date: {now}

Produce a concise, actionable daily brief from the raw signals below.
Apply second-order thinking throughout. Name specific tickers/companies when relevant.

──────────────────────────────────────────────────
TWITTER — Semiconductor insiders
──────────────────────────────────────────────────
{tweet_block}

──────────────────────────────────────────────────
HARDWARE / ICS SECURITY (CISA KEV + NVD CRITICAL)
──────────────────────────────────────────────────
{cve_block}

──────────────────────────────────────────────────
SEMICONDUCTOR & COMPONENT NEWS
──────────────────────────────────────────────────
{semicon_block}

──────────────────────────────────────────────────
SEMICON PRICE MOVERS (>3% daily)
──────────────────────────────────────────────────
{movers_block}

──────────────────────────────────────────────────
CRITICAL MINERALS & ARGENTINA MINING
──────────────────────────────────────────────────
{mining_block}

──────────────────────────────────────────────────
SALTA PROVINCE — INVESTMENT CONTEXT
──────────────────────────────────────────────────
{SALTA_CONTEXT}

──────────────────────────────────────────────────
BRIEF FORMAT (follow exactly):

## Supply Chain Pulse
[2-4 bullets. Components/nodes under pressure, allocation shifts, lead time signals.
 Link semiconductor demand to upstream mineral constraints where relevant.]

## Threat Landscape
[2-3 bullets. Hardware/ICS CVEs, supply chain attack vectors.]

## Argentina / Lithium Triangle
[2-4 bullets. Salta/Jujuy/Catamarca project updates, policy signals (RIGI, royalties, FX),
 lithium price moves, company news. Flag anything relevant to a direct investor in the province.
 Include: infrastructure gaps, workforce signals, permitting, water rights, community relations.]

## Second-Order Implications
[2-3 bullets. Cross-cutting themes: e.g., AI demand → battery demand → lithium price → Salta projects.
 Who wins, who loses? Specific tickers or investment angles.]

## Watch List (next 24-72h)
[3-5 items. What to monitor and where to look.]

Keep it tight. If a section has no signal, say "Nothing material this cycle." and move on.
"""


# ── Claude API call ───────────────────────────────────────────────────────────

def _call_claude(prompt: str) -> str:
    try:
        import anthropic
        import config
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except ImportError:
        logger.error("anthropic package not installed — run: pip install anthropic")
        return "Error: anthropic package not available."
    except Exception as exc:
        logger.error("Claude API call failed: %s", exc)
        return f"Error generating brief: {exc}"


# ── Public API ────────────────────────────────────────────────────────────────

def generate_brief(
    tweets: list[dict],
    infosec_signals: list[dict],
    semicon_signals: list[dict],
    force: bool = False,
) -> str:
    """
    Generate a daily intelligence brief from aggregated signals.
    Results are cached for BRIEF_CACHE_TTL seconds unless force=True.

    Args:
        tweets:           From intelligence.twitter.fetch_new_tweets()
        infosec_signals:  From intelligence.infosec.fetch_all_infosec()
        semicon_signals:  From intelligence.semicon.fetch_all_semicon()
        force:            Skip cache and regenerate.

    Returns:
        Markdown-formatted brief string.
    """
    global _brief_cache

    if not force and _brief_cache is not None:
        ts, brief = _brief_cache
        if time.time() - ts < BRIEF_CACHE_TTL:
            logger.debug("Synthesizer: returning cached brief")
            return brief

    # Separate movers from news in semicon_signals
    movers = [s for s in semicon_signals if s.get("source") == "price-mover"]
    news   = infosec_signals + [s for s in semicon_signals if s.get("source") != "price-mover"]

    total_signals = len(tweets) + len(infosec_signals) + len(semicon_signals)
    logger.info("Synthesizer: generating brief from %d signals", total_signals)

    prompt = _build_prompt(tweets, infosec_signals, news, movers)
    brief  = _call_claude(prompt)

    _brief_cache = (time.time(), brief)
    return brief


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from intelligence.infosec import fetch_all_infosec
    from intelligence.semicon import fetch_all_semicon
    from intelligence.twitter import fetch_new_tweets

    print("Fetching signals…")
    tweets   = fetch_new_tweets(seen_ids=set())
    infosec  = fetch_all_infosec()
    semicon  = fetch_all_semicon()

    print(f"  Tweets:  {len(tweets)}")
    print(f"  Infosec: {len(infosec)}")
    print(f"  Semicon: {len(semicon)}")
    print("\nGenerating brief…\n")

    brief = generate_brief(tweets, infosec, semicon, force=True)
    print(brief)
