# Solaris & Agents — Roadmap

> Daily improvement log. Each session we pick one or two items, ship them, and mark them done.
> Ordered roughly by impact × effort. Add new ideas at the bottom of each section.

---

## What exists today (baseline)

| System | Status | Notes |
|--------|--------|-------|
| **Solaris** dashboard | ✅ Running | Glassmorphic UI, 4 sections, Good Morning modal |
| Solaris `/polymarket` detail page | ✅ Done | Full bet table, stats chips |
| Solaris `/dota` detail page | ✅ Done | Bets + backtest history + Elo rankings |
| Solaris weather widget | ✅ Done | Open-Meteo + geolocation |
| Solaris job tracker | ✅ Done | Pipeline CRUD, interview tracking |
| Solaris Good Morning modal | ✅ Done | Agent status, overnight activity, water tracker, daily quote |
| **Polymarket agent** | ✅ Running live | Kelly sizing, implied-edge filter, 5-signal scorer |
| **Dota 2 agent** | ✅ Dry-run | Elo model, backtest, OpenDota API |

---

## Day-by-day plan

### Day 1 — already done ✅
- Glassmorphic redesign of Solaris
- `/polymarket` and `/dota` detail pages
- Weather widget in header
- Daily motivational quote in Good Morning modal

---

### Day 2 — Live clock + SSE push updates
**Goal:** Kill the dumb 60-second meta refresh. Make the dashboard feel alive.

- [ ] Replace `<meta http-equiv="refresh">` with a Server-Sent Events stream (`/api/stream`)
- [ ] Solaris pushes a lightweight JSON ping every 30s with fresh market + agent data
- [ ] JS patches the DOM in-place (no full reload = no flash)
- [ ] Add a live clock in the header (ticks every second in JS)
- [ ] "Last updated" timestamp next to each agent card

**Files:** `solaris/web/app.py`, `solaris/web/templates/index.html`

---

### Day 3 — Polymarket P&L chart
**Goal:** See the equity curve over time, not just a number.

- [ ] Add `recorded_at` snapshots to `bets.db` (cumulative P&L per day)
- [ ] `/api/polymarket/pnl-history` endpoint → `[{date, cumulative_pnl}]`
- [ ] Render as an SVG sparkline (no external chart lib) on the `/polymarket` page
- [ ] Show drawdown and best/worst day

**Files:** `polymarket-agent/database.py`, `solaris/agents.py`, `solaris/web/templates/polymarket.html`

---

### Day 4 — Dota agent: go live
**Goal:** Switch Dota from dry-run to actually placing bets on Polymarket.

- [ ] Map OpenDota team names → Polymarket market slugs
- [ ] Add a confidence gate: only bet when `true_prob > 0.65` AND `edge > 0.08`
- [ ] Test end-to-end with a $1 real bet
- [ ] Add `is_live` flag to dota stats in Solaris

**Files:** `dota-agent/simulator.py`, `dota-agent/analyzer.py`, `dota-agent/config.py`

---

### Day 5 — Solaris mobile + PWA
**Goal:** Open it on your phone and have it feel native.

- [ ] Fix layout breakpoints (current 2-col agent row breaks on small screens)
- [ ] Add `manifest.json` + service worker so it installs as a PWA
- [ ] `apple-touch-icon` + theme color meta tags
- [ ] Tap-friendly button sizes

**Files:** `solaris/web/templates/index.html`, new `solaris/web/static/manifest.json`

---

### Day 6 — Browser push notifications
**Goal:** Get a push notification when a bet resolves (won/lost) without having the page open.

- [ ] Register a service worker with Push API
- [ ] Solaris tracks `last_notified_bet_id` per agent
- [ ] Tracker polling loop calls `/api/notify` when new resolved bets appear
- [ ] Notification shows: "📈 Polymarket — Won $47 on [question]"

**Files:** `solaris/web/app.py`, `solaris/web/templates/index.html`, new service worker

---

### Day 7 — Polymarket signal improvement: news sentiment
**Goal:** Add a news-based signal to the scorer so it can catch momentum shifts.

- [ ] Fetch headlines for a market question via NewsAPI (or free RSS scraping)
- [ ] Run a quick Claude Haiku call: "Given these headlines, is sentiment bullish or bearish for YES?"
- [ ] Add `news_signal` score (−1 to +1) to `BetCandidate`
- [ ] Weight it at ~15% in the final score

**Files:** `polymarket-agent/signals.py`, `polymarket-agent/analyzer.py`, `polymarket-agent/config.py`

---

### Day 8 — Solaris: Job tracker improvements
**Goal:** Make the job tracker actually useful daily, not just a glorified spreadsheet.

- [ ] Add "Days since applied" computed column
- [ ] Color-code rows by staleness (green < 7d, yellow 7–14d, red > 14d)
- [ ] One-click "follow up" button that copies a follow-up email template
- [ ] Add a notes field per job (inline editable)
- [ ] Weekly summary in Good Morning: "You have X jobs in technical round"

**Files:** `solaris/database.py`, `solaris/web/app.py`, `solaris/web/templates/index.html`

---

### Day 9 — New agent: Crypto arbitrage scanner
**Goal:** Scan for price discrepancies between prediction markets and crypto spot.

- [ ] Agent watches BTC/ETH price-correlated Polymarket markets
- [ ] Flags when implied market probability diverges from price action by >10%
- [ ] Dry-run only initially, just alerts in Solaris
- [ ] New `crypto-agent/` directory, same architecture as polymarket-agent

**Files:** new `crypto-agent/` module, `solaris/agents.py`, `solaris/config.py`

---

### Day 10 — Polymarket: Kelly compounding + bankroll management
**Goal:** Grow the virtual bankroll properly instead of fixed $5–100 stakes.

- [ ] Track `current_bankroll` in `bets.db` (starts at $1000 virtual)
- [ ] Kelly stake = `bankroll × kelly_fraction` (capped at 5% per bet)
- [ ] Bankroll updates on each resolution
- [ ] Show bankroll curve on the P&L chart

**Files:** `polymarket-agent/simulator.py`, `polymarket-agent/database.py`, `polymarket-agent/config.py`

---

## Backlog (unscheduled ideas)

### Solaris
- [ ] Dark/light theme toggle (persist in localStorage)
- [ ] CSV export on detail pages
- [ ] Search + filter on bet history tables
- [ ] Keyboard shortcut `G` → Good Morning, `R` → refresh
- [ ] `/api/dashboard` auth (simple token) so it's safe to expose on LAN
- [ ] Multiple watchlists for stocks (tech / macro / personal)

### Polymarket agent
- [ ] Telegram/Discord alert when a high-confidence bet is placed
- [ ] Auto-void detection for markets that resolve ambiguously
- [ ] Multi-leg parlay simulation
- [ ] Back-test the scorer against historical resolved markets

### Dota agent
- [ ] Ingest patch notes → adjust team form scores after major patches
- [ ] Tournament bracket awareness (adjust kelly for BO1 vs BO3)
- [ ] Add a second model: XGBoost trained on OpenDota match history
- [ ] Roster change detection (API → re-run Elo on affected teams)

### New agents
- [ ] **Calendar agent** — scrape upcoming Polymarket market expirations, surface in Good Morning
- [ ] **Earnings agent** — track stock earnings dates, bet on volatility markets around them
- [ ] **Sports agent** — NBA/NFL markets using similar Elo + form approach as Dota

---

## Architecture notes

```
claude-code-agents/
├── polymarket-agent/   # Live betting agent (Polymarket CLOB)
├── dota-agent/         # Dota 2 prediction model + betting
├── solaris/            # Dashboard: aggregates all agents + markets + career
├── crypto-agent/       # (planned Day 9)
└── ROADMAP.md          # This file
```

Each agent is **self-contained**: its own DB, scheduler, Flask mini-UI, and Rich terminal dashboard.
Solaris reads their DBs **read-only** — no coupling, no shared state.

---

*Updated: 2026-03-31*
