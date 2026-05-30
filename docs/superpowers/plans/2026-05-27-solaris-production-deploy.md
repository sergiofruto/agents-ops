# Solaris Production Deploy — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy Solaris as a live, auth-gated Next.js dashboard on Vercel, backed by Turso (libSQL) that a local one-way `sync.py` feeds from the agents' SQLite DBs.

**Architecture:** Local agents keep their SQLite DBs untouched. `sync.py` reads them read-only and upserts into hosted Turso. The Next.js 16 app reads Turso directly in server components (no Python server in prod), fetches market data live, renders a mock finance card, and gates everything behind a password middleware.

**Tech Stack:** Turso/libSQL, `libsql-client` (Python), `@libsql/client` (TS), Next.js 16.2.2, React 19, Tailwind 4, Vercel, pytest.

**Scope (1-week):** Polymarket, Dota, Markets (live), Jobs/pipeline, mock finance card, auth, deploy, README. Deferred to Phase 2: coordinator-status, good-morning, silicon-intel, custom domain, long-form docs, articles.

---

## File Structure

- Create `solaris/turso/schema.sql` — Turso table DDL (read-models)
- Create `solaris/turso_client.py` — Python libSQL connection helper
- Create `solaris/sync.py` — one-way uploader (local SQLite → Turso); **excludes finance**
- Create `solaris/test_sync.py` — upsert idempotency test (stdlib sqlite3, no network)
- Create `solaris/web-next/lib/db.ts` — server-only `@libsql/client`
- Create `solaris/web-next/lib/queries.ts` — TS read queries (port of `agents.py` + jobs/pipeline)
- Create `solaris/web-next/lib/market.ts` — live market fetch (port of `market_data.py`)
- Create `solaris/web-next/lib/finance.mock.ts` — placeholder finance fixture + type
- Create `solaris/web-next/lib/auth.ts` — cookie sign/verify
- Create `solaris/web-next/middleware.ts` — password gate
- Create `solaris/web-next/app/login/page.tsx` + `solaris/web-next/app/login/actions.ts` — login
- Create `solaris/web-next/components/FinanceCard.tsx` — mock finance card
- Modify `solaris/web-next/app/page.tsx`, `app/polymarket/page.tsx`, `app/dota/page.tsx` — read new lib
- Modify `solaris/web-next/next.config.ts` — remove dead `/api` proxy
- Delete `solaris/web-next/lib/api.ts` — replaced by direct reads
- Create `solaris/README.md`

---

## Task 0: Provision Turso (manual, no code)

- [ ] **Step 1: Install the Turso CLI and create the DB**

Run:
```bash
brew install tursodatabase/tap/turso
turso auth signup        # or: turso auth login
turso db create solaris-prod
turso db show solaris-prod --url
turso db tokens create solaris-prod
```
Expected: a `libsql://solaris-prod-<org>.turso.io` URL and an auth token string.

- [ ] **Step 2: Put credentials in `solaris/.env`**

Add to `solaris/.env`:
```
TURSO_DATABASE_URL=libsql://solaris-prod-<org>.turso.io
TURSO_AUTH_TOKEN=<token from step 1>
```
Expected: `grep TURSO solaris/.env` shows both lines.

---

## Task 1: Turso schema + Python connection helper (validates libSQL API early)

**Files:**
- Create: `solaris/turso/schema.sql`
- Create: `solaris/turso_client.py`
- Modify: `solaris/requirements.txt`

- [ ] **Step 1: Add the Python dependency**

Append to `solaris/requirements.txt`:
```
libsql-client>=0.3.1
```
Run: `cd solaris && pip install -r requirements.txt`
Expected: `libsql-client` installs.

- [ ] **Step 2: Write the schema**

Create `solaris/turso/schema.sql`:
```sql
CREATE TABLE IF NOT EXISTS polymarket_bets (
  id INTEGER PRIMARY KEY,
  question TEXT, outcome TEXT, price_at_bet REAL, virtual_amount REAL,
  potential_payout REAL, score REAL, edge REAL, kelly_stake REAL,
  status TEXT, timestamp TEXT, order_id TEXT
);
CREATE TABLE IF NOT EXISTS dota_bets (
  id INTEGER PRIMARY KEY,
  question TEXT, outcome TEXT, team_a TEXT, team_b TEXT, tournament TEXT,
  league_tier TEXT, price_at_bet REAL, virtual_amount REAL, potential_payout REAL,
  score REAL, edge REAL, true_prob REAL, elo_prob REAL, form_a REAL, form_b REAL,
  h2h_winrate REAL, h2h_sample INTEGER, kelly_stake REAL, status TEXT, timestamp TEXT
);
CREATE TABLE IF NOT EXISTS dota_backtest (
  run_at TEXT PRIMARY KEY,
  days INTEGER, n_teams INTEGER, n_matches INTEGER,
  model_accuracy REAL, elo_accuracy REAL, model_brier REAL, elo_brier REAL,
  calibration_factor REAL
);
CREATE TABLE IF NOT EXISTS dota_elo (
  team_name TEXT PRIMARY KEY,
  elo REAL, snapshot_at TEXT
);
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY,
  company TEXT, role TEXT, url TEXT, salary_min INTEGER, salary_max INTEGER,
  location TEXT, status TEXT, applied_at TEXT, next_action TEXT, notes TEXT,
  updated_at TEXT, interview_count INTEGER DEFAULT 0
);
```

- [ ] **Step 3: Write the connection helper**

Create `solaris/turso_client.py`:
```python
"""libSQL/Turso client helper for the local sync script."""
import os
from dotenv import load_dotenv
import libsql_client

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def get_client() -> "libsql_client.Client":
    url = os.environ["TURSO_DATABASE_URL"]
    token = os.environ["TURSO_AUTH_TOKEN"]
    # libsql-client sync client speaks HTTP; accept libsql:// or https:// URLs.
    if url.startswith("libsql://"):
        url = "https://" + url[len("libsql://"):]
    return libsql_client.create_client_sync(url=url, auth_token=token)


def apply_schema() -> None:
    here = os.path.dirname(__file__)
    with open(os.path.join(here, "turso", "schema.sql")) as f:
        statements = [s.strip() for s in f.read().split(";") if s.strip()]
    client = get_client()
    try:
        for stmt in statements:
            client.execute(stmt)
    finally:
        client.close()


if __name__ == "__main__":
    apply_schema()
    client = get_client()
    try:
        rs = client.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        print("Tables in Turso:", [row[0] for row in rs.rows])
    finally:
        client.close()
```

- [ ] **Step 4: Run the smoke test (this proves the libSQL API + creds work)**

Run: `cd solaris && python turso_client.py`
Expected: `Tables in Turso: ['dota_backtest', 'dota_bets', 'dota_elo', 'jobs', 'polymarket_bets']`
(If `create_client_sync` errors on the URL scheme, try the `https://` form directly from `turso db show solaris-prod --url --http` and adjust `get_client`. Fix here once — everything else depends on it.)

- [ ] **Step 5: Commit**

```bash
git add solaris/turso/schema.sql solaris/turso_client.py solaris/requirements.txt
git commit -m "feat(solaris): add Turso schema + python client helper"
```

---

## Task 2: `sync.py` one-way uploader + idempotency test

**Files:**
- Create: `solaris/sync.py`
- Create: `solaris/test_sync.py`

- [ ] **Step 1: Write the failing idempotency test (stdlib sqlite3, no network)**

Create `solaris/test_sync.py`:
```python
import sqlite3
from sync import UPSERTS, schema_statements


def _apply(conn, statements):
    for s in statements:
        conn.execute(s)


def test_upsert_is_idempotent():
    conn = sqlite3.connect(":memory:")
    _apply(conn, schema_statements())

    rows = [
        {"id": 1, "question": "Q1", "outcome": "Yes", "price_at_bet": 0.8,
         "virtual_amount": 10, "potential_payout": 12.5, "score": 0.9, "edge": 0.05,
         "kelly_stake": 0.1, "status": "open", "timestamp": "2026-05-27", "order_id": None},
    ]
    sql, cols = UPSERTS["polymarket_bets"]
    for _ in range(2):  # run twice — must not duplicate
        for r in rows:
            conn.execute(sql, [r[c] for c in cols])
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM polymarket_bets").fetchone()[0]
    assert count == 1
    # second run updated, not inserted
    row = conn.execute("SELECT status FROM polymarket_bets WHERE id=1").fetchone()
    assert row[0] == "open"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd solaris && python -m pytest test_sync.py -v`
Expected: FAIL — `ModuleNotFoundError`/`ImportError` (sync.py not written yet).

- [ ] **Step 3: Write `sync.py`**

Create `solaris/sync.py`:
```python
"""
One-way uploader: local agent SQLite DBs -> Turso. Read-only on sources.
Excludes finance entirely. Run manually or via cron.
    python sync.py
"""
import logging
import os
import sqlite3
import sys

import config
from turso_client import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("solaris.sync")


def schema_statements() -> list[str]:
    here = os.path.dirname(__file__)
    with open(os.path.join(here, "turso", "schema.sql")) as f:
        return [s.strip() for s in f.read().split(";") if s.strip()]


def _upsert(table: str, cols: list[str]) -> str:
    placeholders = ", ".join("?" for _ in cols)
    updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c not in ("id",))
    # natural key is the first column (id / run_at / team_name)
    return (f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT({cols[0]}) DO UPDATE SET {updates}")


_POLY_COLS = ["id", "question", "outcome", "price_at_bet", "virtual_amount",
              "potential_payout", "score", "edge", "kelly_stake", "status",
              "timestamp", "order_id"]
_DOTA_COLS = ["id", "question", "outcome", "team_a", "team_b", "tournament",
              "league_tier", "price_at_bet", "virtual_amount", "potential_payout",
              "score", "edge", "true_prob", "elo_prob", "form_a", "form_b",
              "h2h_winrate", "h2h_sample", "kelly_stake", "status", "timestamp"]
_BACKTEST_COLS = ["run_at", "days", "n_teams", "n_matches", "model_accuracy",
                  "elo_accuracy", "model_brier", "elo_brier", "calibration_factor"]
_ELO_COLS = ["team_name", "elo", "snapshot_at"]
_JOB_COLS = ["id", "company", "role", "url", "salary_min", "salary_max", "location",
             "status", "applied_at", "next_action", "notes", "updated_at", "interview_count"]

UPSERTS = {
    "polymarket_bets": (_upsert("polymarket_bets", _POLY_COLS), _POLY_COLS),
    "dota_bets":       (_upsert("dota_bets", _DOTA_COLS), _DOTA_COLS),
    "dota_backtest":   (_upsert("dota_backtest", _BACKTEST_COLS), _BACKTEST_COLS),
    "dota_elo":        (_upsert("dota_elo", _ELO_COLS), _ELO_COLS),
    "jobs":            (_upsert("jobs", _JOB_COLS), _JOB_COLS),
}


def _open_ro(path: str) -> sqlite3.Connection | None:
    if not os.path.exists(path):
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(conn: sqlite3.Connection, query: str) -> list[dict]:
    return [dict(r) for r in conn.execute(query).fetchall()]


def _push(client, table: str, rows: list[dict]) -> int:
    sql, cols = UPSERTS[table]
    n = 0
    for r in rows:
        client.execute(sql, [r.get(c) for c in cols])
        n += 1
    return n


def sync() -> dict:
    client = get_client()
    summary = {}
    try:
        for stmt in schema_statements():
            client.execute(stmt)

        # Polymarket
        try:
            conn = _open_ro(config.POLYMARKET_DB)
            if conn:
                rows = _rows(conn, f"SELECT {', '.join(_POLY_COLS)} FROM bets")
                summary["polymarket_bets"] = _push(client, "polymarket_bets", rows)
                conn.close()
        except Exception as e:
            logger.error("polymarket sync failed: %s", e)

        # Dota bets + backtest + elo
        try:
            conn = _open_ro(config.DOTA_DB)
            if conn:
                summary["dota_bets"] = _push(client, "dota_bets",
                    _rows(conn, f"SELECT {', '.join(_DOTA_COLS)} FROM bets"))
                try:
                    summary["dota_backtest"] = _push(client, "dota_backtest",
                        _rows(conn, f"SELECT {', '.join(_BACKTEST_COLS)} FROM backtest_summary"))
                except sqlite3.OperationalError:
                    pass
                try:
                    latest = conn.execute("SELECT MAX(snapshot_at) FROM elo_snapshots").fetchone()[0]
                    if latest:
                        elo = _rows(conn, f"SELECT {', '.join(_ELO_COLS)} FROM elo_snapshots WHERE snapshot_at='{latest}'")
                        summary["dota_elo"] = _push(client, "dota_elo", elo)
                except sqlite3.OperationalError:
                    pass
                conn.close()
        except Exception as e:
            logger.error("dota sync failed: %s", e)

        # Jobs (solaris.db) with interview_count
        try:
            conn = _open_ro(config.SOLARIS_DB)
            if conn:
                jobs = _rows(conn, """
                    SELECT j.id, j.company, j.role, j.url, j.salary_min, j.salary_max,
                           j.location, j.status, j.applied_at, j.next_action, j.notes, j.updated_at,
                           (SELECT COUNT(*) FROM interviews i WHERE i.job_id=j.id) AS interview_count
                    FROM jobs j
                """)
                summary["jobs"] = _push(client, "jobs", jobs)
                conn.close()
        except Exception as e:
            logger.error("jobs sync failed: %s", e)
    finally:
        client.close()

    logger.info("Sync complete: %s", summary)
    return summary


if __name__ == "__main__":
    sync()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd solaris && python -m pytest test_sync.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Run a real sync and verify data landed in Turso**

Run: `cd solaris && python sync.py`
Expected: log line like `Sync complete: {'polymarket_bets': N, 'dota_bets': M, 'jobs': 81}`.
Verify: `turso db shell solaris-prod "SELECT COUNT(*) FROM polymarket_bets;"` returns a non-zero count.

- [ ] **Step 6: Commit**

```bash
git add solaris/sync.py solaris/test_sync.py
git commit -m "feat(solaris): one-way sync from agent SQLite to Turso"
```

---

## Task 3: TS DB client + query layer

**Files:**
- Create: `solaris/web-next/lib/db.ts`
- Create: `solaris/web-next/lib/queries.ts`
- Modify: `solaris/web-next/package.json` (add `@libsql/client`)

- [ ] **Step 1: Install the client**

Run: `cd solaris/web-next && npm install @libsql/client`
Expected: `@libsql/client` in `package.json` dependencies.

- [ ] **Step 2: Write the server-only DB client**

Create `solaris/web-next/lib/db.ts`:
```ts
import "server-only";
import { createClient } from "@libsql/client";

export const db = createClient({
  url: process.env.TURSO_DATABASE_URL!,
  authToken: process.env.TURSO_AUTH_TOKEN!,
});
```

- [ ] **Step 3: Write the query layer (returns the existing `lib/types.ts` shapes)**

Create `solaris/web-next/lib/queries.ts`:
```ts
import "server-only";
import { db } from "./db";
import type {
  PolymarketStats, PolymarketBet, DotaStats, DotaBet, DotaAnalytics,
  Job, PipelineCounts, JobStatus,
} from "./types";

export async function getPolymarketBets(): Promise<PolymarketBet[]> {
  const rs = await db.execute("SELECT * FROM polymarket_bets ORDER BY id DESC");
  return rs.rows as unknown as PolymarketBet[];
}

export async function getPolymarketStats(): Promise<PolymarketStats> {
  const bets = await getPolymarketBets();
  if (bets.length === 0) return { available: false };
  const won = bets.filter(b => b.status === "won").length;
  const lost = bets.filter(b => b.status === "lost").length;
  const resolved = won + lost;
  const pnl = bets.reduce((a, b) =>
    b.status === "won" ? a + (b.potential_payout - b.virtual_amount)
    : b.status === "lost" ? a - b.virtual_amount : a, 0);
  const wagered = bets.filter(b => b.status === "won" || b.status === "lost")
    .reduce((a, b) => a + b.virtual_amount, 0);
  return {
    available: true,
    is_live: bets.some(b => b.order_id),
    total: bets.length,
    open: bets.filter(b => b.status === "open").length,
    won, lost,
    win_rate: resolved ? Math.round((won / resolved) * 1000) / 10 : 0,
    pnl: Math.round(pnl * 100) / 100,
    roi: wagered ? Math.round((pnl / wagered) * 1000) / 10 : 0,
    recent_bets: bets.slice(0, 5).map(b => ({
      question: b.question, outcome: b.outcome, virtual_amount: b.virtual_amount,
      edge: b.edge, kelly_stake: b.kelly_stake, status: b.status, timestamp: b.timestamp,
    })),
  };
}

export async function getDotaBets(): Promise<DotaBet[]> {
  const rs = await db.execute("SELECT * FROM dota_bets ORDER BY id DESC");
  return rs.rows as unknown as DotaBet[];
}

export async function getDotaStats(): Promise<DotaStats> {
  const bets = await getDotaBets();
  if (bets.length === 0) return { available: false };
  const won = bets.filter(b => b.status === "won").length;
  const lost = bets.filter(b => b.status === "lost").length;
  const resolved = won + lost;
  const pnl = bets.reduce((a, b) =>
    b.status === "won" ? a + (b.potential_payout - b.virtual_amount)
    : b.status === "lost" ? a - b.virtual_amount : a, 0);
  const wagered = bets.filter(b => b.status === "won" || b.status === "lost")
    .reduce((a, b) => a + b.virtual_amount, 0);
  const bt = await db.execute("SELECT model_accuracy, elo_accuracy FROM dota_backtest ORDER BY run_at DESC LIMIT 1");
  const latest = bt.rows[0] as { model_accuracy?: number; elo_accuracy?: number } | undefined;
  return {
    available: true, is_live: false, total: bets.length,
    open: bets.filter(b => b.status === "open").length, won, lost,
    win_rate: resolved ? Math.round((won / resolved) * 1000) / 10 : 0,
    pnl: Math.round(pnl * 100) / 100,
    roi: wagered ? Math.round((pnl / wagered) * 1000) / 10 : 0,
    model_accuracy: latest?.model_accuracy != null ? Math.round(latest.model_accuracy * 1000) / 10 : null,
    elo_accuracy: latest?.elo_accuracy != null ? Math.round(latest.elo_accuracy * 1000) / 10 : null,
    recent_bets: bets.slice(0, 5).map(b => ({
      question: b.question, outcome: b.outcome, virtual_amount: b.virtual_amount,
      edge: b.edge, kelly_stake: b.kelly_stake, status: b.status, timestamp: b.timestamp,
      team_a: b.team_a, team_b: b.team_b, tournament: b.tournament,
    })),
  };
}

export async function getDotaAnalytics(): Promise<DotaAnalytics> {
  const bt = await db.execute("SELECT * FROM dota_backtest ORDER BY run_at DESC");
  const elo = await db.execute("SELECT team_name, elo FROM dota_elo ORDER BY elo DESC LIMIT 100");
  const team_rankings = elo.rows.map(r => ({ name: r.team_name as string, elo: r.elo as number }));
  return {
    backtest_history: bt.rows as unknown as DotaAnalytics["backtest_history"],
    team_rankings,
    roster_available: team_rankings.length > 0,
  };
}

export async function getJobs(): Promise<Job[]> {
  const rs = await db.execute("SELECT * FROM jobs ORDER BY updated_at DESC");
  return rs.rows as unknown as Job[];
}

export async function getPipeline(): Promise<PipelineCounts> {
  const jobs = await getJobs();
  const counts: PipelineCounts = {
    bookmarked: 0, applied: 0, phone: 0, technical: 0, final: 0, offer: 0, rejected: 0,
  };
  for (const j of jobs) {
    const s = j.status as JobStatus;
    if (s in counts) counts[s as keyof PipelineCounts]++;
  }
  return counts;
}
```

- [ ] **Step 4: Verify it compiles and reads Turso**

Create a temporary check (do not commit it): `solaris/web-next/scripts/check-queries.mts`:
```ts
import { getPolymarketStats, getJobs } from "../lib/queries";
const stats = await getPolymarketStats();
const jobs = await getJobs();
console.log("polymarket:", stats.total, "jobs:", jobs.length);
```
Run: `cd solaris/web-next && TURSO_DATABASE_URL=$(grep TURSO_DATABASE_URL ../.env | cut -d= -f2) TURSO_AUTH_TOKEN=$(grep TURSO_AUTH_TOKEN ../.env | cut -d= -f2) npx tsx scripts/check-queries.mts`
Expected: `polymarket: <N> jobs: 81`. Then delete the scripts/ file: `rm -r scripts`.

- [ ] **Step 5: Commit**

```bash
git add solaris/web-next/lib/db.ts solaris/web-next/lib/queries.ts solaris/web-next/package.json solaris/web-next/package-lock.json
git commit -m "feat(solaris): TS query layer reading Turso"
```

---

## Task 4: Live market fetch + mock finance card

**Files:**
- Create: `solaris/web-next/lib/market.ts`
- Create: `solaris/web-next/lib/finance.mock.ts`
- Create: `solaris/web-next/components/FinanceCard.tsx`

- [ ] **Step 1: Write the market fetchers**

Create `solaris/web-next/lib/market.ts`:
```ts
import type { BtcData, StockItem, FearGreed } from "./types";

const REVALIDATE = 300; // 5 min

export async function getBtc(): Promise<BtcData> {
  try {
    const r = await fetch(
      "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
      { next: { revalidate: REVALIDATE } });
    const d = (await r.json()).bitcoin;
    let sparkline: number[] = [];
    try {
      const r2 = await fetch(
        "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=7&interval=daily",
        { next: { revalidate: REVALIDATE } });
      sparkline = ((await r2.json()).prices ?? []).slice(-7).map((p: number[]) => Math.round(p[1]));
    } catch {}
    return { price: d.usd, change_24h: Math.round((d.usd_24h_change ?? 0) * 100) / 100, sparkline };
  } catch {
    return { price: null, change_24h: null, sparkline: [] };
  }
}

export async function getFearGreed(): Promise<FearGreed> {
  try {
    const r = await fetch("https://api.alternative.me/fng/", { next: { revalidate: REVALIDATE } });
    const item = (await r.json()).data[0];
    return { value: parseInt(item.value, 10), label: item.value_classification };
  } catch {
    return { value: null, label: "Unknown" };
  }
}

// yfinance has no public JSON API; use Yahoo's quote endpoint for the watchlist.
export async function getStocks(tickers = ["SPY", "QQQ", "NVDA"]): Promise<StockItem[]> {
  try {
    const r = await fetch(
      `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${tickers.join(",")}`,
      { next: { revalidate: REVALIDATE }, headers: { "User-Agent": "Mozilla/5.0" } });
    const result = (await r.json()).quoteResponse?.result ?? [];
    return tickers.map(t => {
      const q = result.find((x: { symbol: string }) => x.symbol === t);
      return {
        ticker: t,
        price: q?.regularMarketPrice != null ? Math.round(q.regularMarketPrice * 100) / 100 : null,
        change_pct: q?.regularMarketChangePercent != null ? Math.round(q.regularMarketChangePercent * 100) / 100 : null,
      };
    });
  } catch {
    return tickers.map(t => ({ ticker: t, price: null, change_pct: null }));
  }
}
```

- [ ] **Step 2: Write the mock finance fixture**

Create `solaris/web-next/lib/finance.mock.ts`:
```ts
// PLACEHOLDER finance data for the public/deployed build. NOT real numbers.
export interface FinanceSummary {
  net_worth_usd: number;
  goal_name: string;
  goal_target_usd: number;
  goal_progress_pct: number;
  allocation: { label: string; usd: number }[];
}

export const financeMock: FinanceSummary = {
  net_worth_usd: 18750,
  goal_name: "Sample goal — house fund",
  goal_target_usd: 60000,
  goal_progress_pct: 31,
  allocation: [
    { label: "USD cash", usd: 14200 },
    { label: "Money market", usd: 3100 },
    { label: "Crypto", usd: 950 },
    { label: "Other", usd: 500 },
  ],
};
```

- [ ] **Step 3: Write the FinanceCard component**

Create `solaris/web-next/components/FinanceCard.tsx`:
```tsx
import { financeMock } from "@/lib/finance.mock";

export function FinanceCard() {
  const f = financeMock;
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-950 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-neutral-300">Finance (demo data)</h3>
        <span className="rounded bg-neutral-800 px-1.5 py-0.5 text-[10px] text-neutral-400">SAMPLE</span>
      </div>
      <div className="mt-2 text-2xl font-semibold">${f.net_worth_usd.toLocaleString()}</div>
      <div className="mt-1 text-xs text-neutral-400">
        {f.goal_name}: {f.goal_progress_pct}% of ${f.goal_target_usd.toLocaleString()}
      </div>
      <ul className="mt-3 space-y-1 text-xs text-neutral-400">
        {f.allocation.map(a => (
          <li key={a.label} className="flex justify-between">
            <span>{a.label}</span><span>${a.usd.toLocaleString()}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 4: Verify build compiles**

Run: `cd solaris/web-next && npx tsc --noEmit`
Expected: no type errors from the three new files.

- [ ] **Step 5: Commit**

```bash
git add solaris/web-next/lib/market.ts solaris/web-next/lib/finance.mock.ts solaris/web-next/components/FinanceCard.tsx
git commit -m "feat(solaris): live market fetch + mock finance card"
```

---

## Task 5: Rewire pages to read Turso; remove dead proxy + api.ts

**Files:**
- Modify: `solaris/web-next/app/page.tsx`, `app/polymarket/page.tsx`, `app/dota/page.tsx`
- Modify: `solaris/web-next/next.config.ts`
- Delete: `solaris/web-next/lib/api.ts`

- [ ] **Step 1: Remove the dead `/api` proxy**

Replace `solaris/web-next/next.config.ts` with:
```ts
import type { NextConfig } from "next";
const nextConfig: NextConfig = {};
export default nextConfig;
```

- [ ] **Step 2: Repoint each page from `lib/api` to the new lib**

In `app/page.tsx`, `app/polymarket/page.tsx`, `app/dota/page.tsx`: replace imports `from "@/lib/api"` (or `"../lib/api"`) and their calls as follows — the function names match, so it is a source swap:
- `getPolymarketStats`, `getPolymarketBets`, `getDotaStats`, `getDotaBets`, `getDotaAnalytics`, `getJobs` → import from `@/lib/queries`
- `getDashboard` is gone; build the dashboard data inline in `app/page.tsx`:
```tsx
import { getPolymarketStats, getDotaStats, getJobs, getPipeline } from "@/lib/queries";
import { getBtc, getStocks, getFearGreed } from "@/lib/market";
import { FinanceCard } from "@/components/FinanceCard";

export default async function Page() {
  const [polymarket, dota, jobs, pipeline, btc, stocks, fear_greed] = await Promise.all([
    getPolymarketStats(), getDotaStats(), getJobs(), getPipeline(),
    getBtc(), getStocks(), getFearGreed(),
  ]);
  // pass these to the existing dashboard section components;
  // add <FinanceCard /> into the Markets/overview area.
  // ...existing JSX, now fed by the variables above...
}
```
For any component that previously expected the `DashboardData` object, pass `{ polymarket, dota, btc, stocks, fear_greed, pipeline }`.

- [ ] **Step 3: Delete the old API module**

Run: `cd solaris/web-next && git rm lib/api.ts`
If anything still imports `getCoordinatorStatus` or `getGoodMorning` (Phase 2 features), delete those usages / components for now (e.g. a GoodMorningModal call) — they are deferred.

- [ ] **Step 4: Run the app locally and verify each page renders with real data**

Run (two terminals):
```bash
cd solaris && python sync.py            # ensure Turso is fresh
cd solaris/web-next && TURSO_DATABASE_URL=... TURSO_AUTH_TOKEN=... npm run dev
```
Open `http://localhost:3010`. Expected: dashboard shows polymarket/dota stats, live BTC/stocks/Fear&Greed, jobs/pipeline, and the SAMPLE finance card. Visit `/polymarket` and `/dota` — tables + elo render. No console errors about `localhost:5010`.

- [ ] **Step 5: Verify production build**

Run: `cd solaris/web-next && npm run build`
Expected: build succeeds, pages compile as dynamic/server-rendered.

- [ ] **Step 6: Commit**

```bash
git add solaris/web-next/app solaris/web-next/next.config.ts
git rm solaris/web-next/lib/api.ts
git commit -m "feat(solaris): read Turso directly in pages; drop Flask proxy"
```

---

## Task 6: Password auth gate

**Files:**
- Create: `solaris/web-next/lib/auth.ts`
- Create: `solaris/web-next/middleware.ts`
- Create: `solaris/web-next/app/login/page.tsx`
- Create: `solaris/web-next/app/login/actions.ts`

- [ ] **Step 1: Write the cookie sign/verify helper**

Create `solaris/web-next/lib/auth.ts`:
```ts
import { createHmac, timingSafeEqual } from "crypto";

const COOKIE = "solaris_auth";

function sign(value: string): string {
  const sig = createHmac("sha256", process.env.AUTH_SECRET!).update(value).digest("hex");
  return `${value}.${sig}`;
}

export function makeSessionCookie(): { name: string; value: string } {
  return { name: COOKIE, value: sign("ok") };
}

export function isValidCookie(raw: string | undefined): boolean {
  if (!raw) return false;
  const [value, sig] = raw.split(".");
  if (!value || !sig) return false;
  const expected = createHmac("sha256", process.env.AUTH_SECRET!).update(value).digest("hex");
  try {
    return value === "ok" && timingSafeEqual(Buffer.from(sig), Buffer.from(expected));
  } catch { return false; }
}

export function checkPassword(input: string): boolean {
  const expected = process.env.SOLARIS_PASSWORD ?? "";
  if (input.length !== expected.length) return false;
  return timingSafeEqual(Buffer.from(input), Buffer.from(expected));
}

export const COOKIE_NAME = COOKIE;
```

- [ ] **Step 2: Write the middleware gate**

Create `solaris/web-next/middleware.ts`:
```ts
import { NextResponse, type NextRequest } from "next/server";
import { isValidCookie, COOKIE_NAME } from "@/lib/auth";

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (pathname.startsWith("/login") || pathname.startsWith("/_next") ||
      pathname === "/favicon.ico") {
    return NextResponse.next();
  }
  if (isValidCookie(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.next();
  }
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  return NextResponse.redirect(url);
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
```

- [ ] **Step 3: Write the login server action + page**

Create `solaris/web-next/app/login/actions.ts`:
```ts
"use server";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { checkPassword, makeSessionCookie } from "@/lib/auth";

export async function login(formData: FormData) {
  const pw = String(formData.get("password") ?? "");
  if (!checkPassword(pw)) redirect("/login?error=1");
  const c = makeSessionCookie();
  (await cookies()).set(c.name, c.value, {
    httpOnly: true, secure: true, sameSite: "lax", path: "/", maxAge: 60 * 60 * 24 * 30,
  });
  redirect("/");
}
```

Create `solaris/web-next/app/login/page.tsx`:
```tsx
import { login } from "./actions";

export default async function Login({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  return (
    <main className="flex min-h-screen items-center justify-center bg-black">
      <form action={login} className="w-72 space-y-3 rounded-lg border border-neutral-800 p-6">
        <h1 className="text-lg font-medium text-neutral-200">Solaris</h1>
        <input type="password" name="password" placeholder="Password" autoFocus
          className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-neutral-100" />
        {error && <p className="text-xs text-red-400">Wrong password.</p>}
        <button className="w-full rounded bg-neutral-200 py-2 text-sm font-medium text-black">Enter</button>
      </form>
    </main>
  );
}
```

- [ ] **Step 4: Verify the gate locally**

Add `SOLARIS_PASSWORD=test123` and `AUTH_SECRET=$(openssl rand -hex 32)` to a local `.env.local` in `web-next`, restart `npm run dev`.
Expected: visiting `/` redirects to `/login`; wrong password shows error; correct password sets cookie and lands on the dashboard; refresh stays logged in.

- [ ] **Step 5: Commit**

```bash
git add solaris/web-next/lib/auth.ts solaris/web-next/middleware.ts solaris/web-next/app/login
git commit -m "feat(solaris): password auth gate via middleware"
```

---

## Task 7: Deploy to Vercel

**Files:** none (platform config)

- [ ] **Step 1: Link the project**

Run:
```bash
cd solaris/web-next
npx vercel link
```
Expected: project linked (`.vercel/` created; it is gitignored by Next defaults — confirm).

- [ ] **Step 2: Set production env vars**

Run (paste values when prompted):
```bash
npx vercel env add TURSO_DATABASE_URL production
npx vercel env add TURSO_AUTH_TOKEN production
npx vercel env add SOLARIS_PASSWORD production
npx vercel env add AUTH_SECRET production
```
Expected: four vars added for production.

- [ ] **Step 3: Deploy**

Run: `npx vercel --prod`
Expected: a production URL is printed and the build succeeds.

- [ ] **Step 4: Smoke-test production**

Open the URL. Expected: redirected to `/login`; correct password → dashboard with live market data, polymarket/dota stats, jobs, SAMPLE finance card. Check `/polymarket` and `/dota`.
If data is empty but local worked: re-run `python sync.py` (prod reads the same Turso) and reload.

- [ ] **Step 5: Commit any config changes**

```bash
git add solaris/web-next/.gitignore
git commit -m "chore(solaris): vercel project config" || echo "nothing to commit"
```

---

## Task 8: README (Phase 1 doc)

**Files:**
- Create: `solaris/README.md`

- [ ] **Step 1: Write the README**

Create `solaris/README.md`:
```markdown
# Solaris

Coordinator dashboard aggregating my autonomous agents (polymarket trading,
dota betting, market data, job hunt) into one live, auth-gated view.

## Architecture

    agents → local SQLite → sync.py (one-way) → Turso (libSQL) → Next.js 16 (Vercel)
    market data → fetched live in Next.js
    finance → mock data in the deploy; real data stays local

- **`turso/schema.sql`** — hosted read-model tables
- **`sync.py`** — reads agent SQLite read-only, upserts to Turso (excludes finance)
- **`web-next/`** — Next.js 16 app; server components read Turso via `@libsql/client`
- **`web-next/middleware.ts`** — password gate

## Run locally

    cd solaris && python sync.py                 # push agent data to Turso
    cd solaris/web-next && npm run dev            # needs TURSO_*, SOLARIS_PASSWORD, AUTH_SECRET

## Deploy

    cd solaris/web-next && npx vercel --prod      # env vars set via `vercel env add`

Keep Turso fresh by running `python sync.py` on a cron (~15 min).
```

- [ ] **Step 2: Commit**

```bash
git add solaris/README.md
git commit -m "docs(solaris): add README with architecture + run/deploy"
```

---

## Self-Review Notes

- **Spec coverage:** Turso schema (T1), one-way `sync.py` excluding finance (T2), TS read layer (T3), live market + mock finance card (T4), page rewire + proxy removal (T5), auth gate (T6), Vercel deploy (T7), README (T8). Deferred items (coordinator/good-morning/silicon-intel/domain/articles) are explicitly out, per spec.
- **Placeholder scan:** none — every code step has full code; manual-verification steps (UI/deploy) give exact commands + expected output.
- **Type consistency:** `queries.ts` returns the exact `lib/types.ts` interfaces the components already consume (`PolymarketStats`, `DotaBet`, `Job`, `PipelineCounts`, etc.). `sync.py` `UPSERTS`/`schema_statements` names match `test_sync.py`. Env var names (`TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, `SOLARIS_PASSWORD`, `AUTH_SECRET`) are identical across Tasks 1, 3, 6, 7.
- **Known risk flagged in-plan:** the Python libSQL connection (T1 Step 4) and the Yahoo stocks endpoint (T4) are the two external-API uncertainties; T1's smoke test surfaces the first immediately, and `getStocks` degrades gracefully to nulls.
