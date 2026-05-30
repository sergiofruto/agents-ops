# Solaris

Coordinator dashboard aggregating my autonomous agents — polymarket trading,
dota betting, market data, job hunt — into one live, auth-gated view.

```
agents → local SQLite → sync.py (one-way) → Turso (libSQL) → Next.js 16 (Vercel)
market data → fetched live in Next.js
finance → mock data in the deploy; real data stays local
```

## Architecture

- **`turso/schema.sql`** — hosted read-model tables (polymarket bets, dota bets/backtest/elo, jobs)
- **`turso_client.py`** — Python libSQL client helper
- **`sync.py`** — reads each agent's local SQLite read-only, upserts to Turso; **excludes finance**
- **`web-next/`** — Next.js 16 app
  - `lib/db.ts`, `lib/queries.ts` — server-only Turso reads via `@libsql/client`
  - `lib/market.ts` — live BTC / stocks / Fear&Greed (port of `market_data.py`)
  - `lib/finance.mock.ts` + `components/FinanceCard.tsx` — placeholder finance card
  - `proxy.ts` — single-password gate (Next 16 renamed middleware → proxy)
  - `app/login` — login page + server action

## Run locally

```bash
# 1. Push agent data to Turso (Turso URL+token in solaris/.env)
cd solaris && python sync.py

# 2. Run the dashboard (Turso vars + SOLARIS_PASSWORD + AUTH_SECRET in web-next/.env.local)
cd solaris/web-next && npm run dev    # http://localhost:3010
```

## Deploy

```bash
cd solaris/web-next
npx vercel link
npx vercel env add TURSO_DATABASE_URL production
npx vercel env add TURSO_AUTH_TOKEN production
npx vercel env add SOLARIS_PASSWORD production
npx vercel env add AUTH_SECRET production
npx vercel --prod
```

Keep Turso fresh by running `python sync.py` on a cron (~15 min).

## Tests

```bash
cd solaris && python -m pytest test_sync.py -v
```

## Phase 2 (out of this build)

- 1–2 articles on the architecture
- `coordinator/status` + `good-morning` sections (read local files; need sync)
- silicon-intel / stock-agent section
- Custom domain (`solaris.sergiofruto.dev`), `ARCHITECTURE.md`, `DEPLOY.md`
- Re-enable `JobTracker` mutations via a write path
