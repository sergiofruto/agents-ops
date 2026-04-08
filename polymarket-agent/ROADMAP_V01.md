# Polymarket Agent — v0.1 Stabilization Roadmap

Current state: DB reset, live mode active, $100 bankroll, 0 open bets.
Goal: a version that can run unsupervised in live mode without catastrophic failure.

---

## CRITICAL — Must fix before v0.1

### 1. Live mode: startup credential validation
**File:** `main.py`
**Problem:** In live mode the agent starts all three threads before ever checking if
POLY_PRIVATE_KEY / POLY_API_KEY / POLY_API_SECRET / POLY_API_PASSPHRASE are valid.
It silently fails on the first attempted bet, after already having scanned and scored markets.
**Fix:** Before starting threads in live mode, call `_get_clob_client()` and do a test
API call (e.g. `client.get_ok()`). Abort with a clear error if credentials are missing or rejected.

### 2. Live mode: stop-loss / take-profit must place a sell order
**File:** `tracker.py`
**Problem:** `_check_exit_triggers()` in live mode logs a warning: "Manual action required".
The agent has no way to protect capital autonomously. A stop-loss that only logs is not a stop-loss.
**Fix:** In live mode, call `client.create_and_post_order(OrderArgs(token_id, price=0.01, size, "SELL"))`
when stop-loss triggers. Mirror the dry-run auto-close logic but with a real order.

### 3. Minimum CLOB order size guard
**File:** `simulator.py` `_place_live_bet()`
**Problem:** CLOB rejects orders below its minimum size (varies by market, typically $1–$5 USDC).
Kelly sizing might produce a valid-looking stake that the exchange rejects silently.
**Fix:** After computing `size`, check against a config floor (`MIN_LIVE_ORDER_USDC = 2.0`).
Skip and log clearly if below floor.

### 4. Add `.env.example`
**File:** new `.env.example`
**Problem:** No reference config file. Anyone setting up the agent has to read code to know
what vars are needed.
**Fix:** Create `.env.example` with every variable, its default, and a one-line comment.

---

## IMPORTANT — Should be in v0.1

### 6. CoinGecko rate-limit backoff
**File:** `signals.py` `_fetch_crypto_data()`
**Problem:** Cache key is `coin_id:days_to_expiry` — a 1-day change in DTE creates a new
cache entry, so a scan with 50 crypto markets triggers 50 API calls. CoinGecko free tier
allows 10–30 req/min. We'll get 429s.
**Fix:** Change cache key to just `coin_id`. Vol blending still uses the DTE from the call
argument, but the underlying price/sigma data is only fetched once per TTL per coin.
Also add exponential backoff (1s, 2s, 4s) on 429 responses.

### 7. Live order fill confirmation
**File:** `simulator.py` `_place_live_bet()`
**Problem:** We post the order and record whatever status string the CLOB returns.
We never verify it actually matched and filled. An unmatched limit order sits open
but we record it as an "open bet" — our exposure calculation is wrong.
**Fix:** After posting, poll `client.get_order(order_id)` once. If status is `"unmatched"`
or `"open"`, log a warning and mark the DB entry with `order_status='pending_fill'`.
Tracker should re-check pending_fill bets on each cycle.

### 8. LIVE mode banner in reporter
**File:** `reporter.py`
**Problem:** The terminal dashboard doesn't make it obviously clear you're in live mode
spending real money.
**Fix:** Add a prominent red "⚡ LIVE MODE — REAL FUNDS" banner to the dashboard header
when `DRY_RUN=False`. In dry-run, show a dim "[DRY RUN]" indicator.

### 9. LLM edge stricter in live mode
**File:** `signals.py` `_llm_edge()`
**Problem:** In live mode, Claude Haiku's probability estimate is used for "other" markets
(geopolitical, macro, elections). Low-confidence signals are filtered but "medium"
confidence gets through. With $100 at stake, medium-confidence LLM estimates should
have a higher edge bar.
**Fix:** In live mode, require `confidence == "high"` OR `edge > MIN_EDGE * 2` for LLM signals.
Read `config.DRY_RUN` inside `_llm_edge()` to apply stricter threshold.

### 10. Graceful shutdown summary
**File:** `main.py`
**Problem:** Ctrl+C just prints "Agent stopped." with no summary of open positions.
**Fix:** On KeyboardInterrupt, print a table of all open bets (market, stake, current P&L
estimate) before exiting. In live mode, add a warning if positions are open.

---

## NICE TO HAVE — Polish for v0.1

### 11. Web UI: show live/dry-run mode and wallet balance
**File:** `web/app.py`, `web/templates/index.html`
**Fix:** Add mode badge and wallet balance (live) or virtual bankroll (dry-run) to dashboard.

### 12. README update
**File:** `README.md`
**Fix:** Document live setup flow end-to-end: install deps → configure .env → run live_setup.py → run main.py.
Add section on bankroll sizing advice ($100 is aggressive, $500+ recommended for Kelly to be stable).

### 13. Cooldown bug: uses placement timestamp, not resolution timestamp
**File:** `database.py` `is_market_on_cooldown()`
**Problem:** Cooldown checks `timestamp >= cutoff` (the bet placement time), not the resolution time.
A market bet on Day 0, resolving Day 5, is on "cooldown" from Day 0 even if the cooldown window
should start at Day 5.
**Fix:** Add a `resolved_at` column to bets table; set it in `update_bet_result()`.
Cooldown check uses `resolved_at >= cutoff`.

### 14. `rescore.py` — wire into the main loop or document
**File:** `rescore.py`
**Problem:** This file exists but isn't called from anywhere. Unclear if it's a utility or dead code.
**Fix:** Either integrate into scan cycle (re-score open bets to catch degraded signals)
or move to a `tools/` directory and document it.

---

## Out of scope for v0.1

- Multi-outcome markets (currently only binary YES/NO)
- Portfolio-level risk (correlation between open bets)
- Telegram alerts
- Backtesting integration into main loop
- Web UI chat / analytics
