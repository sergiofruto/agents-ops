# agents-ops

A personal platform of AI agents and AI products, built by [Sergio Gabriel Fruto](https://www.linkedin.com/in/sergio-gabriel-fruto/) to answer one question: what does it take to move applied AI from demo to something that runs with real stakes?

**▶ Live demo: [Biomech Lab](https://biomech-lab.vercel.app)** — upload a yoga pose, get it recognized and scored from joint angles measured entirely in your browser.

---

## What's here

| Project | What it does | Status | Stack |
|---|---|---|---|
| [**Biomech Lab**](biomech-lab/) | Recognizes Warrior II, Tree and Downward Dog in a photo and scores posture from measured joint angles. Images never leave the browser. | **Live** · [biomech-lab.vercel.app](https://biomech-lab.vercel.app) | Next.js 16 · TypeScript · MediaPipe Pose · Vitest · Vercel |
| [**Polymarket agent**](polymarket-agent/) | Scores prediction markets, estimates true probability, sizes with half-Kelly, places and exits CLOB orders. | Active (dry-run by default, live mode available) | Python · Polymarket CLOB · Claude Haiku · SQLite |
| [**Dota agent**](dota-agent/) | Predicts pro Dota 2 match outcomes from Elo and history; simulates Kelly-sized bets. | Simulation only | Python · OpenDota API · SQLite |
| [**Job Hunter**](job-hunter-agent/) | Scores job postings against a candidate profile, writes tailored cover notes, syncs roles to the dashboard. | Active | Python · Claude API · SQLite |
| [**The Analyst**](analyst-agent/) | Daily intelligence brief: CVEs (NIST NVD, CISA KEV), AWS security bulletins, OSINT signals (OpenSky, GDELT), synthesized into one report. | Active (daily) | Python · Claude API · Next.js |
| [**Silicon Intel**](stock-agent/) | Semiconductor supply-chain and hardware-security terminal; Claude writes a daily brief from industry, CVE and materials feeds. | Paused | Python · Claude Sonnet · RSS feeds |
| [**Finance agent**](finance-agent/) | Personal finance tracker (statements, goals, net worth). | Paused, local use | Python · SQLite |
| [**Solaris**](solaris/) | Coordinator + dashboard that runs the agents in dependency order and writes a daily operations log. | Active | Python · Flask · Next.js 16 · shadcn/ui |

---

## Biomech Lab

The newest project, and the one you can click.

- **Pipeline:** MediaPipe detects 33 body landmarks in the browser → pure TypeScript modules convert them to pixel space, infer the camera view (front/side) and framing, classify the pose by rules, and score each check (e.g. "front knee 90° ± 10°") with partial credit.
- **Honest scoring:** a readiness gate refuses to show a number when the view is wrong, the body is badly framed, more than one person is in frame, or less than 70% of the checks can be measured — the visitor gets a specific prompt instead.
- **Privacy:** images stay on the device. MediaPipe ships a built-in usage logger with no opt-out; a `connect-src` Content-Security-Policy blocks it, verified in production.
- **Tested:** 83 unit and golden tests, including scores from real sample photos and mirrored-input invariance.
- **Next:** a streamed Claude coach for feedback on the weakest checks, and live camera mode.

Details: [biomech-lab/README.md](biomech-lab/README.md) · [design spec](biomech-lab/docs/design-spec.md)

---

## Solaris — how the agents run together

```
agents-ops/
├── solaris/              ← Coordinator + dashboard
│   ├── coordinator.py    ← DAG orchestrator
│   ├── roadmap_updater.py
│   ├── daily_log.py      ← Claude synthesis
│   ├── SOLARIS.md        ← Coordinator system prompt
│   └── web-next/         ← Next.js 16 dashboard
│
├── polymarket-agent/     ← Prediction market trading
├── dota-agent/           ← Esports match prediction (simulation)
├── job-hunter-agent/     ← Job opportunity pipeline
├── analyst-agent/        ← Security & OSINT intelligence brief
├── stock-agent/          ← Silicon Intel (paused)
├── finance-agent/        ← Personal finance (paused)
└── biomech-lab/          ← Standalone web app (not orchestrated)
```

Each agent declares a `roadmap.yaml` — tasks, dependencies, schedule and outputs. The coordinator reads all of them at startup, builds a dependency graph, runs agents in topological order, and writes a Claude-generated daily operations log.

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

**Coordinator (`coordinator.py`)**
- Discovers agents by scanning `*/roadmap.yaml`
- Builds a dependency DAG and runs Kahn's topological sort
- Dispatches each agent as a subprocess, injecting context via the `COORDINATOR_CONTEXT` env var
- Agents report back via a JSON sentinel line on stdout: `{"__coordinator_outputs__": {...}}`
- Updates each `roadmap.yaml` after the run (task status, memory, last output)

**Daily log (`daily_log.py` + `SOLARIS.md`)**
- One Claude call at the end of each run
- Input: run results, current roadmap state for all agents, yesterday's log
- Output: structured Markdown — agent status table, blockers, cross-agent signals, suggestions

**Dashboard (`web-next/`)**
- Next.js 16 server components, shadcn/ui, Tailwind; proxies `/api/*` to the Flask backend
- Sections: agent health, market data (BTC, stocks, Fear & Greed), job pipeline, Polymarket bets, Dota analytics

---

## Polymarket agent

- Fetches active markets from the Gamma API and scores them on a composite signal: probability sweet-spot, volume, bid-ask spread, price stability, days to expiry
- Derives **true probability** from domain signals: crypto volatility (CoinGecko), sports odds (The Odds API), and Claude Haiku for everything else
- Sizes positions with **half-Kelly** against a bankroll with exposure caps
- In live mode, places limit orders on the Polymarket CLOB (L2 auth, Polygon) and exits autonomously on **stop-loss** / **take-profit**
- Dry-run by default (`DRY_RUN=true`): every decision is recorded without placing orders

---

## Tech stack

| Layer | Technologies |
|---|---|
| Languages | Python 3.11 · TypeScript (strict) |
| AI / LLM | Claude API (Anthropic) — signals, synthesis, cover notes, intelligence briefs |
| Computer vision | MediaPipe Pose Landmarker (WASM/WebGL, in-browser) |
| Frontend | Next.js 16 · React 19 · Tailwind · shadcn/ui · Canvas API |
| Backend | Flask · SQLite (per-agent DBs) |
| Trading & data | Polymarket CLOB · py-clob-client · CoinGecko · The Odds API · yfinance · OpenDota |
| Orchestration | Custom DAG coordinator (Kahn's algorithm) · `schedule` · per-agent `roadmap.yaml` |
| Testing & deploy | Vitest · Vercel |

---

## Running

Each project is independent.

```bash
# Biomech Lab (Node 22.12+)
cd biomech-lab && npm install && npm run dev      # http://localhost:3000
npm test                                           # 83 tests

# Polymarket agent (dry-run by default)
cd polymarket-agent
pip install -r requirements.txt
cp .env.example .env   # fill in API keys
python main.py

# Solaris dashboard
cd solaris && pip install -r requirements.txt && WEB_PORT=5002 python main.py
cd solaris/web-next && npm install && npm run dev

# Coordinator (runs all enabled agents)
cd solaris && python coordinator.py
```

Live trading requires Polymarket credentials (`DRY_RUN=false` + `POLY_PRIVATE_KEY`); run `python live_setup.py` once to generate CLOB API keys.

---

## Design principles

- **Each agent is sovereign** — runs standalone, no hard dependency on the coordinator
- **The coordinator is additive** — agents don't need to know they're being orchestrated
- **LLMs where they earn their cost** — Claude handles ambiguous signals and synthesis; deterministic code handles measurement and scoring
- **Real stakes, explicit switches** — live trading is opt-in, with stop-loss and take-profit exits
- **Privacy by default** — Biomech Lab keeps images on the device and blocks third-party telemetry
- **Roadmap as runtime state** — `roadmap.yaml` doubles as task tracker and agent memory
