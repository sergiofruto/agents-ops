"""
Polymarket Backtester
=====================
Standalone script that simulates the dry-run scoring strategy against resolved
historical markets fetched from the Gamma + CLOB APIs.

Usage:
    python backtest.py                           # 90-day, default thresholds
    python backtest.py --days 30                 # last 30 days only
    python backtest.py --days 180 --limit 1000   # 6-month, larger dataset
    python backtest.py --min-score 0.55          # looser threshold comparison
    python backtest.py --hours-before 24         # entry 24h before close
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TaskProgressColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich.text import Text

from signals import compute_edge, kelly_stake as calc_kelly

# ---------------------------------------------------------------------------
# Config constants (mirrors config.py so this file runs standalone)
# ---------------------------------------------------------------------------
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE  = "https://clob.polymarket.com"

MIN_PROBABILITY     = 0.70
MAX_PROBABILITY     = 0.97
MIN_VOLUME_24H      = 5_000
MAX_SPREAD          = 0.05
MIN_SCORE_DEFAULT   = 0.65
VIRTUAL_BET_SIZE    = 100
MIN_EDGE_DEFAULT    = 0.03

VIRTUAL_BANKROLL    = 10_000
KELLY_FRACTION      = 0.5
MAX_BET_SIZE        = 250
MIN_BET_SIZE        = 10

WEIGHT_PROBABILITY  = 0.40
WEIGHT_VOLUME       = 0.25
WEIGHT_STABILITY    = 0.20
WEIGHT_SPREAD       = 0.15

_TIMEOUT   = 15
_PAGE_SIZE = 100

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json"})
_adapter = HTTPAdapter(pool_connections=25, pool_maxsize=25)
SESSION.mount("https://", _adapter)
SESSION.mount("http://",  _adapter)

console = Console()
logging.basicConfig(level=logging.WARNING)


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    market_id:     str
    condition_id:  str
    question:      str
    outcome:       str
    outcome_index: int
    entry_price:   float
    spread:        float
    volume:        float
    score:         float
    prob_score:    float
    vol_score:     float
    stab_score:    float   # always 0.5 (no intraday history)
    spread_score:  float
    won:           bool
    close_date:    str
    category:      str     # crypto / sports / politics+macro / other
    edge:          Optional[float] = None
    true_prob:     Optional[float] = None
    kelly_stake:   float           = 100.0


# ---------------------------------------------------------------------------
# Replicated signal scorers (no import of analyzer.py)
# ---------------------------------------------------------------------------

def _probability_score(prob: float, min_prob: float, max_prob: float) -> float:
    if prob < min_prob or prob > max_prob:
        return 0.0
    peak = 0.83
    if prob <= peak:
        return (prob - min_prob) / (peak - min_prob)
    return (max_prob - prob) / (max_prob - peak)


def _volume_score(volume_24h: float) -> float:
    if volume_24h <= 0:
        return 0.0
    ceiling = math.log10(500_000)
    return min(math.log10(max(volume_24h, 1)) / ceiling, 1.0)


def _spread_score(spread: float) -> float:
    return max(0.0, 1.0 - spread / 0.10)


def _composite_score(
    prob: float,
    volume_24h: float,
    spread: float,
    min_prob: float,
    max_prob: float,
) -> tuple[float, float, float, float, float]:
    prob_s  = _probability_score(prob, min_prob, max_prob)
    vol_s   = _volume_score(volume_24h)
    stab_s  = 0.5  # neutral — no intraday history for historical markets
    spr_s   = _spread_score(spread)

    composite = (
        prob_s  * WEIGHT_PROBABILITY +
        vol_s   * WEIGHT_VOLUME      +
        stab_s  * WEIGHT_STABILITY   +
        spr_s   * WEIGHT_SPREAD
    )
    return composite, prob_s, vol_s, stab_s, spr_s


# ---------------------------------------------------------------------------
# Category inference
# ---------------------------------------------------------------------------

_CRYPTO_KEYWORDS   = ["bitcoin", "btc", "eth", "ethereum", "crypto", "solana", "sol",
                       "xrp", "doge", "token", "defi", "nft", "blockchain", "coin"]
_SPORTS_KEYWORDS   = ["nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball",
                       "baseball", "tennis", "golf", "championship", "super bowl",
                       "world cup", "league", "match", "game", "team", "player",
                       "wins", "beat", "score"]
_POLITICS_KEYWORDS = ["election", "president", "senate", "congress", "trump", "biden",
                       "democrat", "republican", "vote", "poll", "gdp", "inflation",
                       "fed", "interest rate", "cpi", "unemployment", "macro",
                       "federal reserve", "rate hike"]


def _infer_category(question: str) -> str:
    q = question.lower()
    if any(kw in q for kw in _CRYPTO_KEYWORDS):
        return "crypto"
    if any(kw in q for kw in _SPORTS_KEYWORDS):
        return "sports"
    if any(kw in q for kw in _POLITICS_KEYWORDS):
        return "politics+macro"
    return "other"


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _parse_json_field(raw) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return []
    return []


# ---------------------------------------------------------------------------
# Gamma API: fetch resolved markets
# ---------------------------------------------------------------------------

def fetch_resolved_markets(days_back: int, limit: int) -> list[dict]:
    cutoff_ts = int((datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp())
    markets: list[dict] = []
    offset = 0

    with console.status(f"[cyan]Fetching resolved markets (last {days_back} days)…"):
        while len(markets) < limit:
            try:
                resp = SESSION.get(
                    f"{GAMMA_BASE}/markets",
                    params={
                        "closed":    "true",
                        "limit":     _PAGE_SIZE,
                        "offset":    offset,
                        "order":     "closedTime",
                        "ascending": "false",
                    },
                    timeout=_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                console.print(f"[red]Gamma fetch error at offset {offset}: {exc}[/red]")
                break

            page = data if isinstance(data, list) else data.get("data", data.get("markets", []))
            if not page:
                break

            past_cutoff = False
            for m in page:
                closed_time_str = m.get("closedTime") or m.get("endDate") or ""
                close_ts = _parse_timestamp(closed_time_str)
                if close_ts is None or close_ts < cutoff_ts:
                    past_cutoff = True
                    break
                markets.append(m)
                if len(markets) >= limit:
                    break

            offset += len(page)
            # Stop if we've scrolled past the time window or exhausted pages
            if past_cutoff or len(page) < _PAGE_SIZE or len(markets) >= limit:
                break

    return markets


def _parse_timestamp(s: str) -> Optional[int]:
    if not s:
        return None
    # Normalise "+00" / "+00:00" timezone suffixes to UTC then parse with fromisoformat
    normalized = s.strip()
    # "2026-02-28 21:35:25+00" → replace space with T, append :00 if tz is bare +00
    normalized = normalized.replace(" ", "T")
    if normalized.endswith("+00"):
        normalized += ":00"
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            continue
    try:
        return int(float(s))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# CLOB API: fetch historical price
# ---------------------------------------------------------------------------

def fetch_price_at_offset(token_id: str, close_ts: int, hours_before: int) -> Optional[float]:
    """
    Return the last price in a 4-hour window ending `hours_before` before close.
    Falls back to None if the endpoint fails or returns no data.
    """
    end_ts   = close_ts - hours_before * 3600
    start_ts = end_ts - 4 * 3600  # 4-hour lookback window

    try:
        resp = SESSION.get(
            f"{CLOB_BASE}/prices-history",
            params={
                "market":    token_id,
                "startTs":   start_ts,
                "endTs":     end_ts,
                "fidelity":  60,
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    # Response shape: {"history": [{"t": ..., "p": ...}, ...]}
    history = data.get("history", [])
    if not history:
        return None

    try:
        return float(history[-1]["p"])
    except (KeyError, TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Per-market processing
# ---------------------------------------------------------------------------

def process_market(
    market: dict,
    hours_before: int,
    min_score: float,
    min_prob: float,
    max_prob: float,
    min_vol: float,
    max_spread: float,
    min_edge: float = 0.0,
) -> Optional[BacktestResult]:
    """Score one resolved market; return BacktestResult or None if filtered out."""

    market_id    = market.get("id", "")
    condition_id = market.get("conditionId", market.get("condition_id", ""))
    question     = market.get("question", "")

    if not market_id:
        return None

    # --- timestamps ---
    closed_time_str = market.get("closedTime") or market.get("endDate") or ""
    close_ts = _parse_timestamp(closed_time_str)
    if not close_ts:
        return None

    start_time_str = market.get("startDate") or market.get("createdAt") or ""
    start_ts = _parse_timestamp(start_time_str)
    days_open = ((close_ts - start_ts) / 86400) if start_ts else 30
    days_open = max(days_open, 1)

    # --- volume approximation ---
    raw_vol = float(market.get("volumeClob") or market.get("volume") or 0)
    volume_24h_approx = raw_vol / days_open

    if volume_24h_approx < min_vol:
        return None

    # --- outcome metadata ---
    outcome_prices_raw = _parse_json_field(market.get("outcomePrices", []))
    outcomes_raw       = _parse_json_field(market.get("outcomes", []))
    token_ids_raw      = _parse_json_field(market.get("clobTokenIds", []))

    try:
        final_prices = [float(p) for p in outcome_prices_raw]
    except (TypeError, ValueError):
        return None

    if not final_prices or not outcomes_raw:
        return None

    outcomes  = [str(o) for o in outcomes_raw]
    token_ids = [str(t) for t in token_ids_raw]

    # Determine winning outcome from final settlement (settles at >= 0.99)
    winning_index: Optional[int] = None
    for i, p in enumerate(final_prices):
        if p >= 0.99:
            winning_index = i
            break

    if winning_index is None:
        return None  # market not cleanly settled

    # --- spread ---
    spread_raw = market.get("spread")
    if spread_raw is not None:
        spread = abs(float(spread_raw))
    else:
        best_bid = market.get("bestBid")
        best_ask = market.get("bestAsk")
        if best_bid is not None and best_ask is not None:
            spread = abs(float(best_ask) - float(best_bid))
        else:
            spread = 0.03  # neutral fallback

    if spread > max_spread:
        return None

    # --- fetch historical entry prices for all tokens from CLOB ---
    # Final outcomePrices are settlement prices (0.99/0.01), not entry prices.
    # We query CLOB price-history to find which outcome was in the sweet spot
    # hours_before the close.
    historical_prices: list[Optional[float]] = []
    for tid in token_ids:
        p = fetch_price_at_offset(tid, close_ts, hours_before) if tid else None
        historical_prices.append(p)

    # Find the outcome whose historical price is in the probability sweet spot
    best_idx: Optional[int] = None
    best_hist_prob = 0.0
    for i, hist_p in enumerate(historical_prices):
        if hist_p is not None and min_prob <= hist_p <= max_prob and hist_p > best_hist_prob:
            best_hist_prob = hist_p
            best_idx = i

    if best_idx is None:
        return None  # no outcome was in the sweet spot at entry time

    entry_price = best_hist_prob

    # --- scoring ---
    composite, prob_s, vol_s, stab_s, spr_s = _composite_score(
        entry_price, volume_24h_approx, spread, min_prob, max_prob
    )

    if composite < min_score:
        return None

    outcome_name = outcomes[best_idx] if best_idx < len(outcomes) else f"Outcome {best_idx}"
    won          = (best_idx == winning_index)
    close_date   = datetime.fromtimestamp(close_ts, tz=timezone.utc).strftime("%Y-%m-%d")
    category     = _infer_category(question)

    # --- Implied-edge filter + Kelly sizing ---
    edge, true_prob = compute_edge(question, category, entry_price, close_date)

    if min_edge > 0 and edge is not None and edge < min_edge:
        return None  # signal available but edge too thin

    stake = float(VIRTUAL_BET_SIZE)
    if true_prob is not None:
        s = calc_kelly(true_prob, entry_price,
                       VIRTUAL_BANKROLL, KELLY_FRACTION, MIN_BET_SIZE, MAX_BET_SIZE)
        stake = s if s > 0 else float(VIRTUAL_BET_SIZE)

    return BacktestResult(
        market_id     = market_id,
        condition_id  = condition_id,
        question      = question,
        outcome       = outcome_name,
        outcome_index = best_idx,
        entry_price   = entry_price,
        spread        = spread,
        volume        = volume_24h_approx,
        score         = round(composite, 4),
        prob_score    = round(prob_s,  4),
        vol_score     = round(vol_s,   4),
        stab_score    = round(stab_s,  4),
        spread_score  = round(spr_s,   4),
        won           = won,
        close_date    = close_date,
        category      = category,
        edge          = edge,
        true_prob     = true_prob,
        kelly_stake   = round(stake, 2),
    )


# ---------------------------------------------------------------------------
# Concurrent processing
# ---------------------------------------------------------------------------

def run_backtest(
    markets: list[dict],
    hours_before: int,
    min_score: float,
    min_prob: float   = MIN_PROBABILITY,
    max_prob: float   = MAX_PROBABILITY,
    min_vol: float    = MIN_VOLUME_24H,
    max_spread: float = MAX_SPREAD,
    min_edge: float   = 0.0,
) -> list[BacktestResult]:
    results: list[BacktestResult] = []

    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        task = progress.add_task("Scoring markets…", total=len(markets))
        with ThreadPoolExecutor(max_workers=20) as pool:
            futures = {
                pool.submit(
                    process_market,
                    m,
                    hours_before,
                    min_score,
                    min_prob,
                    max_prob,
                    min_vol,
                    max_spread,
                    min_edge,
                ): m
                for m in markets
            }
            for fut in as_completed(futures):
                progress.advance(task)
                try:
                    res = fut.result()
                    if res is not None:
                        results.append(res)
                except Exception as exc:
                    logging.debug("process_market error: %s", exc)

    return results


# ---------------------------------------------------------------------------
# Rich report
# ---------------------------------------------------------------------------

def _pnl_for(r: BacktestResult) -> float:
    if r.won:
        return r.kelly_stake * (1.0 / r.entry_price - 1)
    return -r.kelly_stake


def _fmt_pnl(value: float) -> Text:
    s = f"${value:+.2f}"
    return Text(s, style="bold green" if value >= 0 else "bold red")


def _fmt_winrate(rate: float) -> Text:
    s = f"{rate:.1f}%"
    return Text(s, style="bold green" if rate >= 60 else "bold red")


def _fmt_winrate_bucket(rate: float) -> Text:
    s = f"{rate:.1f}%"
    if rate >= 60:
        style = "bold green"
    elif rate >= 50:
        style = "bold yellow"
    else:
        style = "bold red"
    return Text(s, style=style)


def print_report(results: list[BacktestResult], min_score: float, min_edge: float = 0.0) -> None:
    if not results:
        console.print("[yellow]No simulated bets matched the filters.[/yellow]")
        return

    # --- aggregate stats ---
    total_bets    = len(results)
    won_bets      = sum(1 for r in results if r.won)
    lost_bets     = total_bets - won_bets
    win_rate      = 100 * won_bets / total_bets if total_bets else 0.0
    total_pnl     = sum(_pnl_for(r) for r in results)
    total_wagered = sum(r.kelly_stake for r in results)
    avg_stake     = total_wagered / total_bets if total_bets else 0.0
    roi           = 100 * total_pnl / total_wagered if total_wagered else 0.0

    # --- avg edge (only bets with a signal) ---
    edges_known = [r.edge for r in results if r.edge is not None]
    avg_edge_str = f"{sum(edges_known)/len(edges_known):+.1%}" if edges_known else "N/A"

    # ----------------------------------------------------------------
    # Section 1 — Summary panel
    # ----------------------------------------------------------------
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(justify="left")
    grid.add_column(justify="right")

    grid.add_row("Bets simulated",  str(total_bets))
    grid.add_row("Won / Lost",      f"{won_bets} / {lost_bets}")
    grid.add_row("Win rate",        _fmt_winrate(win_rate))
    grid.add_row("Simulated P&L",   _fmt_pnl(total_pnl))
    grid.add_row("ROI",             Text(f"{roi:+.1f}%", style="bold green" if roi >= 0 else "bold red"))
    grid.add_row("Avg stake",       f"${avg_stake:.0f}")
    grid.add_row("Total wagered",   f"${total_wagered:,.0f}")
    grid.add_row("Avg edge",        avg_edge_str)
    grid.add_row("Min score used",  f"{min_score:.2f}")
    grid.add_row("Min edge used",   f"{min_edge:.2%}" if min_edge > 0 else "disabled")

    console.print(Panel(grid, title="[bold]Backtest Summary[/bold]", border_style="cyan"))

    # ----------------------------------------------------------------
    # Section 2 — By Category
    # ----------------------------------------------------------------
    cats: dict[str, dict] = {}
    for r in results:
        c = cats.setdefault(r.category, {"bets": 0, "won": 0, "pnl": 0.0})
        c["bets"] += 1
        c["won"]  += int(r.won)
        c["pnl"]  += _pnl_for(r)

    cat_table = Table(
        title="By Category",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        expand=True,
    )
    cat_table.add_column("Category",  style="cyan")
    cat_table.add_column("Bets",      justify="right")
    cat_table.add_column("Won",       justify="right")
    cat_table.add_column("Win%",      justify="right")
    cat_table.add_column("P&L",       justify="right")

    for cat_name in sorted(cats):
        c   = cats[cat_name]
        wr  = 100 * c["won"] / c["bets"] if c["bets"] else 0.0
        cat_table.add_row(
            cat_name,
            str(c["bets"]),
            str(c["won"]),
            _fmt_winrate(wr),
            _fmt_pnl(c["pnl"]),
        )

    console.print(cat_table)

    # ----------------------------------------------------------------
    # Section 3 — Win Rate by Score Bucket
    # ----------------------------------------------------------------
    buckets = [
        ("0.40–0.55", 0.40, 0.55),
        ("0.55–0.65", 0.55, 0.65),
        ("0.65–0.75", 0.65, 0.75),
        ("0.75+",     0.75, 9.99),
    ]

    bucket_table = Table(
        title="Win Rate by Score Bucket",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        expand=True,
    )
    bucket_table.add_column("Score Range", style="cyan")
    bucket_table.add_column("Bets",        justify="right")
    bucket_table.add_column("Won",         justify="right")
    bucket_table.add_column("Win%",        justify="right")

    for label, lo, hi in buckets:
        subset = [r for r in results if lo <= r.score < hi]
        if not subset:
            continue
        b_won = sum(1 for r in subset if r.won)
        b_wr  = 100 * b_won / len(subset)
        bucket_table.add_row(
            label,
            str(len(subset)),
            str(b_won),
            _fmt_winrate_bucket(b_wr),
        )

    console.print(bucket_table)

    # ----------------------------------------------------------------
    # Section 4 — All Simulated Bets
    # ----------------------------------------------------------------
    bets_table = Table(
        title="All Simulated Bets (newest first)",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        expand=True,
    )
    bets_table.add_column("Date",    style="dim",   width=11)
    bets_table.add_column("Question",              ratio=4)
    bets_table.add_column("Outcome",  style="cyan", ratio=1)
    bets_table.add_column("Result",   width=8)
    bets_table.add_column("Prob",     justify="right", width=7)
    bets_table.add_column("Score",    justify="right", width=7)
    bets_table.add_column("Edge",     justify="right", width=8)
    bets_table.add_column("Stake",    justify="right", width=8)
    bets_table.add_column("P&L",      justify="right", width=9)

    sorted_results = sorted(results, key=lambda r: r.close_date, reverse=True)
    for r in sorted_results:
        result_text = Text("WON",  style="bold green") if r.won else Text("LOST", style="bold red")
        if r.edge is not None:
            edge_text = Text(f"{r.edge:+.1%}", style="green" if r.edge >= 0 else "red")
        else:
            edge_text = Text("N/A", style="dim")
        bets_table.add_row(
            r.close_date,
            r.question[:65],
            r.outcome[:20],
            result_text,
            f"{r.entry_price:.2%}",
            f"{r.score:.3f}",
            edge_text,
            f"${r.kelly_stake:.0f}",
            _fmt_pnl(_pnl_for(r)),
        )

    console.print(bets_table)
    console.print(
        "[dim]* Sports edge N/A for historical markets — "
        "The Odds API covers upcoming events only[/dim]"
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backtest the Polymarket dry-run scoring strategy against resolved markets."
    )
    parser.add_argument("--days",         type=int,   default=90,               help="Days back to backtest (default: 90)")
    parser.add_argument("--limit",        type=int,   default=500,              help="Max resolved markets to fetch (default: 500)")
    parser.add_argument("--min-score",    type=float, default=MIN_SCORE_DEFAULT, help=f"Override composite score threshold (default: {MIN_SCORE_DEFAULT})")
    parser.add_argument("--min-edge",     type=float, default=MIN_EDGE_DEFAULT,  help=f"Min implied edge to bet (default: {MIN_EDGE_DEFAULT}; 0 disables filter)")
    parser.add_argument("--hours-before", type=int,   default=48,               help="Hours before close used as entry point (default: 48)")
    args = parser.parse_args()

    console.rule("[bold cyan]Polymarket Backtester[/bold cyan]")
    console.print(
        f"  Days back: [bold]{args.days}[/bold]   "
        f"Market limit: [bold]{args.limit}[/bold]   "
        f"Min score: [bold]{args.min_score}[/bold]   "
        f"Min edge: [bold]{args.min_edge:.0%}[/bold]   "
        f"Entry: [bold]{args.hours_before}h[/bold] before close\n"
    )

    markets = fetch_resolved_markets(args.days, args.limit)
    console.print(f"[green]Fetched {len(markets)} resolved markets.[/green]\n")

    if not markets:
        console.print("[red]No markets fetched — check API connectivity.[/red]")
        return

    results = run_backtest(
        markets,
        hours_before=args.hours_before,
        min_score=args.min_score,
        min_edge=args.min_edge,
    )

    console.print(f"\n[green]{len(results)} bets passed all filters.[/green]\n")
    console.rule()

    print_report(results, args.min_score, args.min_edge)


if __name__ == "__main__":
    main()
