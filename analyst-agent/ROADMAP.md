# The Analyst — Roadmap

---

## Week of Apr 6–12, 2026 — Web UI (current sprint)

### Day 1–2 — Finish the UI skeleton
- [ ] Complete Next.js scaffold (finish briefs pages, dynamic routes)
- [ ] `npm install` and verify the app boots at localhost:3011
- [ ] Verify Flask API at localhost:5003: `/api/sky`, `/api/solar`, `/api/status`
- [ ] Wire up the star map canvas — confirm planets and constellation lines render

### Day 3 — Chat goes live
- [ ] Add `anthropic` to requirements.txt and install
- [ ] Set `ANTHROPIC_API_KEY` in `.env`
- [ ] End-to-end test: send a message, get a streamed response from The Analyst persona
- [ ] Session sidebar: list, switch, delete conversations
- [ ] Suggested prompt chips on empty state

### Day 4 — Solar widget + dashboard polish
- [ ] Verify NOAA endpoints return real data (solar flare feed, Kp index, solar wind)
- [ ] X-ray gauge renders correctly for current class
- [ ] Kp bar animates
- [ ] Alert pulse on HIGH/CRITICAL solar events
- [ ] Dashboard status bar wired to live `/api/status`
- [ ] Responsive: works on a laptop screen at 1280px

### Day 5 — Briefs archive
- [ ] `/briefs` — list page (all briefs, paginated)
- [ ] `/briefs/[id]` — full brief detail (cyber body, cosmic body, synthesis, quote)
- [ ] Threat level colour coding throughout
- [ ] Link from dashboard → latest brief

### Day 6–7 — Testing & hardening
- [ ] Test with Flask API offline — graceful empty states everywhere
- [ ] Test with no `ANTHROPIC_API_KEY` — show clear error in chat
- [ ] Run a real intel scan cycle: CVE feed + cosmic scan → synthesise brief → appears in UI
- [ ] Write run instructions in README

---

## Phase 2 — Intelligence Depth (next sprint)
- [ ] Live AIS ship tracking overlay on a world map (aisstream.io)
- [ ] OpenSky anomalous aircraft map (region overlays)
- [ ] Shodan integration: infrastructure sweep on watched IP ranges
- [ ] MITRE ATT&CK technique tagging on CVEs

## Phase 3 — Predictive Engine
- [ ] "Forecast" mode: 7-day prediction from cosmic + threat trends
- [ ] Historical brief archive with search
- [ ] Confidence scoring per prediction, tracked over time
- [ ] Correlation engine: map past sky patterns to historical events

## Phase 4 — Solaris Integration
- [ ] Analyst card in Solaris dashboard (latest brief + threat level)
- [ ] `/api/analyst/brief` consumed by Solaris Good Morning

## Phase 5 — Autonomous Operation
- [ ] Daily brief posted to private Telegram channel
- [ ] Push alert on CRITICAL threat level
- [ ] Weekly digest: top CVEs + sky themes + predictions
