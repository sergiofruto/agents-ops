# agents-op — Roadmap

---

## Tomorrow (Apr 8)

### Morning — Polymarket v0.1 finish line
Three quick items to close out stabilization. Agent is live with real money.

1. **`.env.example`** — document every config var with defaults and one-line comments
2. **CoinGecko cache key fix** — change cache key from `coin_id:dte` to `coin_id` only. Stops 429 storms on crypto scans
3. **LLM stricter in live mode** — require `confidence=high` OR `edge > MIN_EDGE*2` for Claude Haiku signals when `DRY_RUN=false`

### Afternoon — Job Hunter `main.py`
Most directly useful right now. Build the entry point:
- Finish `profile.yml` — exit story, Auth0/Scale AI proof points, visa status
- Read all HTMLs from `job-hunter-agent/`
- Parse, score fit against `profile.yml`
- Generate cover note via Claude
- Sync to Solaris DB, enable agent in `roadmap.yaml`

### Evening — Coordinator dry run
Run `python coordinator.py` for real. Read the daily log output. Tune `SOLARIS.md` based on quality.

---

## Daily Agent Routines

Each agent gets one focused improvement per session. Small, compounding.

### Polymarket
| Day | Focus |
|-----|-------|
| Mon | Review last week's bets — which signal categories are winning/losing? |
| Tue | Edge filter tuning — adjust `MIN_EDGE` based on live results |
| Wed | Add or improve one signal source |
| Thu | Tracker improvements — resolution detection, void handling |
| Fri | Backtest a parameter change before applying it live |

### Dota Agent
| Day | Focus |
|-----|-------|
| Mon | ELO calibration — do rankings match recent tournament results? |
| Tue | Feature addition — one new signal (patch version, tournament tier weight) |
| Wed | Backtest the new feature |
| Thu | Review open bets — any systematic misses? |
| Fri | Roster update check |

### Job Hunter
| Day | Focus |
|-----|-------|
| Mon | Process new HTML files dropped into `job-hunter-agent/` |
| Tue | Improve fit scorer — add one new scoring dimension |
| Wed | Follow-up check — update status on applied roles in Solaris |
| Thu | Research one company in the pipeline |
| Fri | Outreach — send one cold message or follow-up |

### Solaris
| Day | Focus |
|-----|-------|
| Mon | Read yesterday's daily log — action any suggestions |
| Tue | Dashboard improvement — one UI thing that's been annoying |
| Wed | Coordinator tune — update roadmap.yaml tasks |
| Thu | New data source or API connection |
| Fri | Review weekly coordinator logs — what patterns emerged? |

---

## Deployment (Hetzner VPS)

Goal: move all agents off local machine to a Hetzner CX22 VPS (~€4/month).
Architecture: one VPS for all daemons + Flask/FastAPI backends, Vercel for Next.js frontends.

### Tasks
- [ ] **provision_vps** — Create Hetzner CX22 (Ubuntu 24.04), SSH key, UFW firewall rules
- [ ] **nginx_setup** — Install nginx + Certbot; one subdomain per service behind HTTPS
- [ ] **systemd_units** — Write unit files for each agent (polymarket, stock, analyst, dota, alfajor-backend, solaris-api); auto-restart on crash
- [ ] **migrate_dbs** — rsync SQLite files from local to VPS; verify integrity
- [ ] **deploy_agents** — Clone repo on VPS, set .env files, enable + start all systemd units
- [ ] **deploy_frontends** — Point Solaris web-next + Alfajor frontend to VPS API URL; deploy both to Vercel free tier
- [ ] **verify_all** — Confirm all agents are scanning/tracking, web UIs accessible, logs flowing

---

## Backlog (prioritized)

### High
- [ ] Job hunter `main.py` — entry point, fit scorer, cover note generator, Solaris sync
- [ ] `profile.yml` completion — exit story, proof points, visa status
- [ ] Polymarket order fill confirmation — poll `get_order()` after posting; mark `pending_fill`
- [ ] Analyst web UI — finish briefs pages, npm install, end-to-end test

### Medium
- [ ] Coordinator cron — launchd job, runs at 6am without manual trigger
- [ ] Daily log viewer in Solaris — `/logs` page with markdown renderer
- [ ] Polymarket graceful shutdown — print open positions on Ctrl+C
- [ ] Polymarket cooldown bug — use `resolved_at` not `placed_at`
- [ ] Dota coordinator outputs — emit `__coordinator_outputs__` at end of run
- [ ] Polymarket P&L chart — equity curve on `/polymarket` page

### Low
- [ ] Polymarket LIVE mode banner in reporter terminal
- [ ] `rescore.py` — integrate into scan cycle or move to `tools/`
- [ ] README screenshots — terminal + dashboard
- [ ] Solaris mobile layout — responsive fixes for small screens

---

## Weekly rhythm

| | Mon | Tue | Wed | Thu | Fri | Weekend |
|-|-----|-----|-----|-----|-----|---------|
| **Agent** | Polymarket | Job Hunter | Solaris | Dota | Any | Build session |
| **Ritual** | Read weekly P&L | Process job HTMLs | Read daily logs | Dota backtest | Backlog item | Update this roadmap |
