# Solaris → Production Deploy — Design

**Date:** 2026-05-27
**Status:** Approved (pending written-spec review)
**Component:** `solaris/` + `solaris/web-next/`
**Why:** Showcase artifact for the JustPaid interview ("show us a tool you've built and love / a walkthrough of your GitHub work you're most proud of"). Goal: a polished, *live*, deployed, well-documented multi-agent coordinator dashboard.

---

## Goal

Take Solaris from a currently-headless local app to a deployed, auth-gated, live dashboard on Vercel, backed by a hosted database fed by the local agents — and document the architecture well enough to write articles about it.

## Current state (important)

The `solaris/web/` Flask API was deleted (this session) and **not replaced** — Solaris is currently headless. `web-next` (Next.js 16) still proxies `/api/*` to a `localhost:5002` Flask server that no longer exists. `agents.py` reads other agents' local SQLite DBs read-only via `file:?mode=ro` URIs. `solaris.db` holds `jobs` + `interviews`. `market_data.py` fetches CoinGecko/yfinance/Fear&Greed live.

## Non-Goals

- No real-time websockets (periodic revalidation is enough).
- No full auth provider (Clerk/Auth0) — a single shared password suffices.
- Agents do **not** write to Turso directly (one-way sync keeps agents untouched).
- Prod is **read-only** — edits (e.g., job tracker) happen on the local instance and sync up.
- The articles themselves are Phase 2 (separate writing task), not this plan.

---

## Architecture

```
agents (polymarket, dota, stock/silicon-intel, job-hunter)
  → local SQLite (bets.db, dota_bets.db, solaris.db, …)
  → sync.py  [local cron ~15 min, one-way, read-only on sources]
  → Turso (libSQL, hosted)            ← aggregation store
Next.js 16 on Vercel
  → server components / route handlers read Turso via @libsql/client (server-only)
  → middleware password gate
  → auth-gated dashboard
market data (CoinGecko / yfinance / Fear&Greed) → fetched LIVE in Next.js (public, not synced)
finance → real data NEVER leaves local; deployed build renders a mock fixture
```

Agents stay untouched. Sync is strictly one-way (local → Turso).

---

## Components

### 1. Turso database (`solaris-prod`, libSQL)
- One hosted libSQL DB. Schema = the dashboard's read-models, defined in `solaris/turso/schema.sql`:
  - `polymarket_bets` (+ a `polymarket_stats` summary)
  - `dota_bets`, `dota_analytics` (elo/backtest)
  - `jobs`, `interviews` (from `solaris.db`)
  - **No finance tables** — real finance is never uploaded.
- Tables mirror the SQLite source columns the UI needs (not raw internals).

### 2. `sync.py` (new, `solaris/sync.py`)
- One-way uploader. Opens each agent's local SQLite read-only (reusing the `agents.py` `_open_ro` pattern), reads the needed rows, and **upserts** into Turso via the libSQL Python client.
- Idempotent upserts keyed by natural IDs (bet id, job id, interview id, date).
- Per-source `try/except`: a missing or broken agent DB is logged and skipped, never aborts the run.
- **Explicitly excludes finance** — `finance.db` is never read by `sync.py`.
- Config: `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` in `solaris/.env`.
- Run manually or via launchd/cron (~15 min). Writes a short log.

### 3. Read layer (`web-next/lib`)
- `lib/db.ts` — server-only `@libsql/client` instance (URL + token from env).
- `lib/queries.ts` — TS port of `agents.py` read functions: `getPolymarketBets`, `getPolymarketStats`, `getDotaBets`, `getDotaAnalytics`, `getJobs`, `getInterviews`. Server-only.
- `lib/market.ts` — live fetch of CoinGecko / yfinance / Fear&Greed (port of `market_data.py`) with `revalidate` caching.
- `lib/finance.mock.ts` — committed, realistic **placeholder** finance data (net worth, goal, allocation) for the deployed build. No real numbers.
- The old `lib/api.ts` (fetched Flask `:5002`) is removed; pages become RSC reading these directly. Route handlers only where a client component needs fetch.

### 4. Auth (middleware password gate)
- `web-next/middleware.ts` — checks a signed httpOnly cookie; if absent/invalid → redirect `/login`. Protects all routes except `/login` and static assets.
- `/login` — posts a password, compared constant-time against `SOLARIS_PASSWORD`; on success sets an httpOnly cookie signed with `AUTH_SECRET`.
- One shared password; grant interviewers access on request.

### 5. Deploy (Vercel)
- Connect `web-next` to Vercel. Env: `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, `SOLARIS_PASSWORD`, `AUTH_SECRET`.
- Remove the `localhost:5002` `/api` rewrite from `next.config.ts`.
- Optional custom domain `solaris.sergiofruto.dev`.

### 6. Documentation (the deliverable)
- `solaris/README.md` — what it is, the architecture diagram, how to run/sync/deploy.
- `solaris/ARCHITECTURE.md` — data-flow diagram + decisions (why Turso, one-way sync, RSC reads, finance-mock, auth).
- `solaris/DEPLOY.md` — Vercel + Turso setup steps.
- These double as raw material for the Phase 2 articles.

---

## Data flow & privacy

- **Market data:** live server fetch (public, no sync).
- **Polymarket / dota / jobs / interviews:** synced to Turso, behind the auth gate.
- **Finance:** real data stays in local `finance.db` only; the deployed build renders `lib/finance.mock.ts`. Real finance never touches Turso or Vercel.
- **Note (secondary):** `jobs`/`interviews` reveal which companies you're applying to (incl. JustPaid). Behind auth, acceptable; flag if you'd rather mock those too.

## Error handling

- `sync.py`: per-source try/except, log + skip on failure; skip missing DBs.
- Next.js: query failures render empty states; market fetch failures fall back to last cached value.
- Auth: invalid password → generic error.

## Testing (minimal — it's a showcase)

- `sync.py`: idempotency test against a temp libSQL file (run twice → no duplicate rows).
- `lib/queries.ts`: light tests against a seeded libSQL file.

---

## Phasing

Target: **Phase 1 shippable in ~1 week**, JustPaid application by ~day 10. If late, we're early for the next role.

- **Phase 1 (this spec/plan — the 1-week shippable):** Turso schema + `sync.py` + TS read layer + auth + Vercel deploy + `README.md` → a working, deployed, live, auth-gated Solaris.
  - **Deployed sections:** Polymarket (stats + bets), Dota (stats + bets + backtest/elo), Markets (live BTC/stocks/Fear&Greed), Jobs/pipeline, and a **small mock finance card** (new component fed by a placeholder fixture — no real finance data).
  - **Deferred to Phase 2** (read solaris-local files, not worth the sync cost this week): `coordinator/status`, `good-morning`. Also deferred: silicon-intel/stock section, custom domain, long-form `ARCHITECTURE.md`/`DEPLOY.md`, deeper tests.
- **Phase 2 (second week, separate):** 1–2 articles about the process. Angle: "Local SQLite → Turso → edge: productionizing a personal multi-agent dashboard." Also deferred to Phase 2: silicon-intel/stock section, custom domain (`solaris.sergiofruto.dev`), `ARCHITECTURE.md`/`DEPLOY.md` long-form, and deeper test coverage.

## Out of scope (YAGNI)

- Real-time websockets; full auth provider; agents writing to Turso; prod-side mutations; bidirectional sync.
