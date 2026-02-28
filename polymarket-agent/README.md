# Polymarket Dry-Run Agent

A paper-trading bot for [Polymarket](https://polymarket.com) prediction markets. It scans open markets, scores them using a multi-signal composite, filters by implied edge against a model-derived true probability, and sizes bets with Half-Kelly — all without spending real money.

---

## How it works

1. **Scan** — fetches open markets from the Gamma + CLOB APIs every 30 minutes
2. **Score** — ranks each market on four signals: probability sweet-spot, 24h volume, price stability, and bid-ask spread
3. **Edge filter** — computes a model-derived true probability (crypto via log-normal/CoinGecko, sports via The Odds API) and skips any bet where the implied edge is below 3%
4. **Kelly sizing** — stakes each bet proportionally to the edge using Half-Kelly, capped at $10–$250
5. **Track** — polls open bets for resolution and records won/lost outcomes in SQLite
6. **Report** — live Rich terminal dashboard + Flask web UI at `localhost:5001`

---

## Architecture

```
polymarket-agent/
├── main.py          # Orchestrator: scan/track/web threads + Rich dashboard
├── config.py        # All thresholds and weights, loaded from .env
├── fetcher.py       # Gamma API + CLOB API HTTP calls
├── analyzer.py      # Multi-signal scorer → BetCandidate dataclass
├── signals.py       # Edge computation: crypto (CoinGecko) + sports (Odds API)
├── simulator.py     # Writes dry-run bets to DB
├── tracker.py       # Polls open bets for resolution
├── reporter.py      # Rich terminal live dashboard
├── database.py      # SQLite (bets.db): bets + price_history tables
├── backtest.py      # Standalone backtester against resolved markets
└── web/
    ├── app.py       # Flask web UI
    └── templates/
        └── index.html
```

---

## Quickstart

```bash
git clone git@github.com:sergiofruto/polymarket-agent.git
cd polymarket-agent
pip install -r requirements.txt

# Optional: configure overrides
cp .env.example .env   # edit as needed

python main.py
```

Web dashboard: `http://localhost:5001`

---

## Configuration

All settings are in `config.py` and can be overridden via `.env`:

| Variable | Default | Description |
|---|---|---|
| `MIN_EDGE` | `0.03` | Minimum model-vs-market edge to place a bet (3%) |
| `ODDS_API_KEY` | `` | [The Odds API](https://the-odds-api.com) key for sports edge |
| `VIRTUAL_BANKROLL` | `10000` | Paper bankroll for Kelly sizing ($) |
| `KELLY_FRACTION` | `0.5` | Half-Kelly multiplier |
| `MAX_BET_SIZE` | `250` | Kelly stake cap ($) |
| `MIN_BET_SIZE` | `10` | Kelly stake floor ($) |
| `MIN_PROBABILITY` | `0.70` | Sweet-spot lower bound |
| `MAX_PROBABILITY` | `0.97` | Sweet-spot upper bound |
| `MIN_VOLUME_24H` | `5000` | Minimum 24h liquidity ($) |
| `SCAN_INTERVAL_MINUTES` | `30` | How often to scan for new markets |

---

## Backtester

Simulate the strategy against resolved historical markets:

```bash
# Default: 90 days, 500 markets, 3% edge filter
python backtest.py

# Disable edge filter (reproduce baseline flat-$100 results)
python backtest.py --min-edge 0

# Stricter edge filter, larger dataset
python backtest.py --days 180 --limit 1000 --min-edge 0.05
```

The report shows win rate, P&L, ROI, a breakdown by category (crypto / sports / politics+macro / other), and an edge column per bet.

---

## Edge signals

### Crypto — log-normal binary probability
Parses questions like *"Will the price of Bitcoin be above $80,000 on March 15?"*, fetches spot price and 30-day volatility from CoinGecko (no API key needed, 1h cache), and computes a fair probability using the log-normal model. Edge = `true_prob − polymarket_price`.

### Sports — vig-removed bookmaker consensus
Matches the Polymarket question to an upcoming game via [The Odds API](https://the-odds-api.com), averages fair probabilities across the top 3 bookmakers after removing vig (4h cache). Requires `ODDS_API_KEY`. Covers NFL, NBA, MLB, NHL, EPL, Bundesliga, NCAAB.

### Fallback
Markets without a signal (politics, macro, other) pass through the edge filter and receive a flat $100 stake.

---

## Database

SQLite at `bets.db` (auto-created on first run):

```sql
bets          — id, question, outcome, price_at_bet, virtual_amount,
                kelly_stake, edge, score, status, result_price, timestamp
price_history — market_id, token_id, price, timestamp
```

Schema migrations run automatically — safe to upgrade an existing database.
