# BTC Threshold Scanner — Design

**Date:** 2026-06-04
**Status:** Approved (pending written-spec review)
**Component:** `polymarket-agent/`

## Goal

A dedicated, **read-only** scanner that surfaces and ranks `"Will Bitcoin reach $X by [date]"`-shaped Polymarket markets — the proven sub-segment of the agent's track record (5W / 1L on BTC, vs 11W / 6L overall). Output goes to a log + a JSON snapshot; **no bets are placed** in v1. After 1–2 weeks of observation, if the BTC pipeline's hypothetical ROI beats the general scan's actual ROI on the same markets, we promote it to live.

## Non-goals

- No bet placement in v1. (Promotion to live = a separate spec/plan.)
- No new edge model — reuses `signals._crypto_edge` and the existing `analyzer.score_markets` machinery.
- Does not modify the existing scan loop. General scanner keeps handling BTC markets as it always has.
- No replacement of `polymarket-agent/main.py` flow — added as a sidecar.

## Architecture

```
existing:
  main.py  →  fetcher.fetch_markets()  →  analyzer.score_markets()
                                       →  simulator.place_bet()  → bets.db

new (sidecar, read-only):
  main.py [--btc-scan ad-hoc | scheduler thread every 15min]
    →  btc_scanner.find_btc_threshold_candidates()
         ├─ fetcher.fetch_markets()         (reuses)
         ├─ btc_scanner._is_btc_threshold() (regex filter)
         ├─ analyzer.score_markets()        (reuses)
         └─ rank by edge × score, top N
    →  log + write JSON snapshot to btc_candidates.json
    →  NO bets placed
```

## Components

### 1. `polymarket-agent/btc_scanner.py` (new)
- `_is_btc_threshold(question: str) -> bool` — regex matches `(bitcoin|btc)` + `(reach|hit|above|over|under|dip|cross)` + a price token (`\$?\d{2,3}[,.]?\d{3}`) + a date/month signal. Case-insensitive.
- `find_btc_threshold_candidates(limit: int = 20) -> list[BetCandidate]` — calls `fetcher.fetch_markets()`, filters with `_is_btc_threshold`, runs them through `analyzer.score_markets()`, returns the top `limit` ranked by `edge × score` (desc).
- `snapshot(candidates: list[BetCandidate], path: Path) -> None` — writes a JSON snapshot of the candidate list with timestamp + market_id + question + score + edge + recommended Kelly stake (computed but not placed).

### 2. `polymarket-agent/main.py` (modify)
- New CLI flag: `python main.py --btc-scan` runs the scanner once, prints a ranked report to stdout, writes the snapshot. Exits.
- New scheduler thread (started alongside the existing scan/track/web threads): every 15 min, runs `find_btc_threshold_candidates()` and appends to a rolling log + updates `btc_candidates.json`. Logs counts ("scanned N markets, M matched BTC pattern, top edge X%"). Does **not** call `place_bet`.
- The scheduler thread is **opt-in** via env: `BTC_SCANNER_ENABLED=true` (default `true`) — easy off-switch.

### 3. `polymarket-agent/btc_candidates.json` (output, gitignored)
- Rolling snapshot of current top candidates with timestamp. Overwritten each scan. Used for Phase-2 ROI attribution (compare candidates surfaced here to bets actually placed by the general scan).

### 4. `polymarket-agent/.gitignore` (modify)
- Add `btc_candidates.json` and `btc_scanner.log`.

## Dedup

In v1 (read-only) dedup is irrelevant — nothing is placed. When promoted to live (Phase 2), the scanner will **skip** any market that the general scanner already has an open or recently-closed bet on (same `market_id` within last 24h). The general scan keeps owning BTC markets it sees first; the BTC scanner only covers markets the general scan missed.

## Observation period & promotion criteria

Run read-only for ≥1 week, ≥20 ranked snapshots. Promote to live (write a Phase-2 spec) only if:
- Hypothetical BTC-pipeline ROI on its top-3 candidates per scan exceeds general-scan BTC ROI by ≥5pp, **and**
- Win rate on those hypothetical bets ≥ 70%, **and**
- ≥15 markets observed.

## Error handling

- Fetcher / API failures: log and skip the scan cycle (no bets placed = no risk).
- Regex matches a non-BTC market: `analyzer.score_markets` filters it out via the existing crypto-category check; no harm.
- Snapshot write failures: log and continue (next cycle overwrites).

## Testing

- One unit test for `_is_btc_threshold`: a small fixture of true positives ("Will Bitcoin reach $90,000 in May?") and false positives ("Will Ethereum hit $4K?", "Will Trump tweet about Bitcoin?"). Lives in `polymarket-agent/test_btc_scanner.py`.
- No integration test against live Gamma API (flaky, rate-limited). Trust the existing fetcher.

## Out of scope (Phase 2 / later)

- Live bet placement from this scanner.
- Per-source attribution column in `bets.db` (would only matter once live).
- Tunable per-scanner config (edge floor, max bets) — for now reuses globals.
- Extending the pattern to other crypto (ETH, SOL).
