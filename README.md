# agents-op

A personal multi-agent operations platform. Three autonomous agents — prediction market trading, esports betting simulation, and job hunting — coordinated by a central orchestrator that resolves dependencies, dispatches context, and synthesizes a daily log via Claude.

Built as an experiment in applied AI: what does it look like when you wire real APIs, real money, and real LLMs into a system that runs itself?

---

## Architecture

```
agents-op/
├── solaris/              ← Coordinator + dashboard
│   ├── coordinator.py    ← DAG orchestrator
│   ├── roadmap_updater.py
│   ├── daily_log.py      ← Claude synthesis
│   ├── SOLARIS.md        ← Coordinator system prompt
│   └── web-next/         ← Next.js 16 dashboard
│
├── polymarket-agent/     ← Prediction market trading
├── dota-agent/           ← Esports betting simulation
└── job-hunter-agent/     ← Job opportunity pipeline
```

Each agent declares a `roadmap.yaml` — tasks, dependencies, schedule, and outputs. The coordinator reads all of them at startup, builds a dependency graph, runs agents in topological order, and writes a Claude-generated daily operations log.

```
Startup
  └── Read all roadmap.yaml files
  └── Build dependency DAG → topological sort

For each agent (in order):
  └── Inject: tasks_today + memory + upstream outputs
  └── Run agent subprocess
  └── Collect outputs
  └── roadmap_updater.py → mark tasks done / blocked

End of day:
  └── Claude call → daily_logs/YYYY-MM-DD.md
       ├── Agent status table
       ├── Blockers
       ├── Cross-agent patterns & signals
       └── Prioritized suggestions
```

---

## Agents

### Polymarket Trading Agent
Live prediction market trading on [Polymarket](https://polymarket.com) via the CLOB API.

- Fetches active markets from the Gamma API, scores them on a composite signal (probability sweet-spot, volume, bid-ask spread, price stability, days to expiry)
- Derives **true probability** from domain-specific signals: crypto volatility (CoinGecko), sports odds (The Odds API), and LLM inference (Claude Haiku) for everything else
- Sizes positions using **half-Kelly criterion** against a virtual bankroll with exposure caps
- Places real limit orders on the Polymarket CLOB (L2 auth, Polygon mainnet)
- Tracks open positions for resolution, **stop-loss**, and **take-profit** — exits autonomously

**Stack:** Python · Polymarket CLOB API · py-clob-client · CoinGecko · The Odds API · Claude API · SQLite · Rich terminal dashboard · Flask web UI

---

### Dota Agent
Simulation-only betting agent for professional Dota 2 matches.

- Fetches pro match data from the **OpenDota API**
- Scores match outcomes using team ELO rankings, draft analysis, and historical win rates
- Simulates bets with Kelly sizing against a virtual bankroll
- Tracks results and computes running P&L, win rate, and ROI

**Stack:** Python · OpenDota API · SQLite · Flask web UI

---

### Job Hunter
Processes job postings, scores fit against a candidate profile, generates tailored cover notes, and syncs qualified roles to the Solaris DB.

- Reads locally saved HTML job postings (Wellfound, LinkedIn)
- Scores fit against `config/profile.yml`: stack match, seniority, equity, remote policy
- Generates cover notes via Claude, personalized to the role and company context
- Auto-inserts qualified roles into the Solaris jobs pipeline

**Stack:** Python · Claude API · HTMLParser · SQLite

---

## Solaris — Coordinator Dashboard

The central nervous system. Coordinates all agents and serves a unified dashboard.

**Coordinator (`coordinator.py`)**
- Discovers agents by scanning `*/roadmap.yaml`
- Builds a dependency DAG and runs Kahn's topological sort
- Dispatches each agent as a subprocess, injecting context via `COORDINATOR_CONTEXT` env var
- Agents report back via a JSON sentinel line on stdout: `{"__coordinator_outputs__": {...}}`
- Updates each `roadmap.yaml` after the run (task status, memory, last output)

**Daily Log (`daily_log.py` + `SOLARIS.md`)**
- One Claude call at the end of each run
- Input: run results, current roadmap state for all agents, yesterday's log
- Output: structured Markdown — agent status table, blockers, cross-agent signals, suggestions
- Stored in `daily_logs/YYYY-MM-DD.md`

**Dashboard (`web-next/`)**
- Next.js 16 server components, shadcn/ui, Tailwind
- Proxies `/api/*` to Flask backend
- Sections: agent health, market data (BTC, stocks, Fear & Greed), job pipeline, Polymarket bets, Dota analytics

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Languages | Python 3.11 · TypeScript |
| AI / LLM | Claude API (Anthropic) — streaming chat, edge signals, daily synthesis |
| Frontend | Next.js 16 · React · shadcn/ui · Tailwind · Canvas API |
| Backend | Flask · SQLite (per-agent DBs) |
| Trading | Polymarket CLOB API · py-clob-client · Polygon (EVM, chain 137) |
| Market data | CoinGecko · The Odds API · yfinance · Fear & Greed Index |
| Orchestration | Custom DAG coordinator · Kahn's topological sort · schedule |
| DevOps | GitHub Actions-ready · dotenv config · per-agent roadmap.yaml |

---

## Running

Each agent is independent. The coordinator ties them together.

```bash
# Polymarket agent (dry-run by default)
cd polymarket-agent
pip install -r requirements.txt
cp .env.example .env   # fill in API keys
python main.py

# Solaris dashboard
cd solaris
pip install -r requirements.txt
WEB_PORT=5002 python main.py

cd solaris/web-next
npm install && npm run dev   # Next.js on :3000

# Coordinator (runs all agents)
cd solaris
python coordinator.py
```

**Live trading** requires Polymarket credentials (`DRY_RUN=false` + `POLY_PRIVATE_KEY`). Run `python live_setup.py` once to generate CLOB API keys.

---

## Design Principles

- **Each agent is sovereign** — runs standalone, no hard dependency on the coordinator
- **Coordinator is additive** — agents don't need to know they're being orchestrated
- **LLM where it earns its cost** — Claude handles ambiguous signals and synthesis, not boilerplate
- **Real stakes** — polymarket agent runs with real money in live mode; stop-loss and take-profit exit autonomously
- **Roadmap as runtime state** — `roadmap.yaml` doubles as task tracker and agent memory, updated after every run
