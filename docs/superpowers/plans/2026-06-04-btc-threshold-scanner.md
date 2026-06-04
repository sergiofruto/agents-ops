# BTC Threshold Scanner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a **read-only** BTC-threshold scanner that surfaces ranked `"Will Bitcoin reach $X by [date]"` Polymarket markets every 15 min and snapshots them to disk — *without placing bets* — so we can observe whether a dedicated BTC pipeline beats the general scan on the proven BTC sub-segment.

**Architecture:** New sidecar module `btc_scanner.py` reuses `fetcher.fetch_active_markets` + `analyzer.score_markets` + `signals._crypto_edge` (no duplication). `main.py` gets a new `--btc-scan` CLI flag (ad-hoc run) and a new opt-in scheduler thread (15-min cadence) that calls the scanner and writes a JSON snapshot. **No bets are placed in v1.**

**Tech Stack:** Python 3.11, stdlib `re`/`json`, `schedule` library (already in deps), `threading` (already used), pytest.

**Scope (v1):** detection + ranking + snapshot only. **Out of scope:** bet placement (Phase 2), per-source bet attribution column, multi-coin expansion.

---

## File Structure

- Create: `polymarket-agent/btc_scanner.py` — regex matcher, candidate finder, snapshot writer
- Create: `polymarket-agent/test_btc_scanner.py` — unit tests (no network)
- Modify: `polymarket-agent/config.py` — add `BTC_SCANNER_ENABLED`, `BTC_SCAN_INTERVAL_MINUTES`, `BTC_TOP_N`
- Modify: `polymarket-agent/main.py` — argparse for `--btc-scan` + scheduler thread (opt-in via env)
- Modify: `polymarket-agent/.gitignore` — add `btc_candidates.json` and `btc_scanner.log`

---

## Task 1: BTC pattern detector (TDD)

**Files:**
- Create: `polymarket-agent/btc_scanner.py`
- Create: `polymarket-agent/test_btc_scanner.py`

- [ ] **Step 1: Write the failing test**

Create `polymarket-agent/test_btc_scanner.py`:
```python
import pytest
from btc_scanner import is_btc_threshold


@pytest.mark.parametrize("q", [
    "Will Bitcoin reach $80,000 in April?",
    "Will Bitcoin reach $82,500 in April?",
    "Will Bitcoin dip to $60,000 in April?",
    "Will BTC hit $100K by end of year?",
    "Will Bitcoin cross $90,000 by May 31?",
    "Bitcoin above $75,000 on May 1?",
])
def test_matches_btc_threshold_questions(q):
    assert is_btc_threshold(q) is True


@pytest.mark.parametrize("q", [
    "Will Ethereum hit $4,000 in May?",          # wrong asset
    "Will Trump tweet about Bitcoin?",            # no verb/price
    "Will Bitcoin dominance exceed 60%?",         # percent, not $
    "Bitcoin halving in 2028?",                   # no verb, no $ threshold
    "Will SOL reach $200 in June?",               # wrong asset
])
def test_rejects_non_btc_threshold_questions(q):
    assert is_btc_threshold(q) is False
```

- [ ] **Step 2: Run to verify failure**

Run: `cd polymarket-agent && python -m pytest test_btc_scanner.py -q`
Expected: FAIL — `ImportError: cannot import name 'is_btc_threshold' from 'btc_scanner'`.

- [ ] **Step 3: Implement `is_btc_threshold`**

Create `polymarket-agent/btc_scanner.py`:
```python
"""
BTC threshold scanner — read-only sidecar that surfaces ranked
"Will Bitcoin reach $X by [date]" Polymarket markets.

v1 is detection + ranking + snapshot. NO bets are placed.
Promotion to live = separate spec.
"""
from __future__ import annotations

import re

# Match: BTC keyword + threshold verb + dollar threshold (e.g. $80,000 or $100K)
_BTC_THRESHOLD_RE = re.compile(
    r"\b(?:bitcoin|btc)\b"
    r".*?\b(?:reach|hit|above|over|under|dip|cross|below|exceed|surpass)\b"
    r".*?\$\s?(?:\d{1,3}(?:,\d{3})+|\d{2,6})\s?[Kk]?",
    re.IGNORECASE | re.DOTALL,
)


def is_btc_threshold(question: str) -> bool:
    """Return True if the market question looks like a BTC price-threshold market."""
    if not question:
        return False
    return bool(_BTC_THRESHOLD_RE.search(question))
```

- [ ] **Step 4: Run tests — verify pass**

Run: `cd polymarket-agent && python -m pytest test_btc_scanner.py -q`
Expected: PASS — `11 passed`.

- [ ] **Step 5: Commit**

```bash
git add polymarket-agent/btc_scanner.py polymarket-agent/test_btc_scanner.py
git commit -m "feat(polymarket): add BTC threshold pattern detector"
```

---

## Task 2: `find_btc_threshold_candidates` (reuses fetcher + analyzer)

**Files:**
- Modify: `polymarket-agent/btc_scanner.py`
- Modify: `polymarket-agent/test_btc_scanner.py`

- [ ] **Step 1: Write the failing test (mocks fetcher to avoid network)**

Append to `polymarket-agent/test_btc_scanner.py`:
```python
from unittest.mock import patch
import btc_scanner as bs


# Minimal raw-market dict mimicking what fetcher.fetch_active_markets returns.
def _raw(question: str, market_id: str = "m1") -> dict:
    return {
        "id": market_id,
        "conditionId": f"0x{market_id}",
        "question": question,
        "outcomes": '["Yes","No"]',
        "outcomePrices": '["0.15","0.85"]',
        "clobTokenIds": '["t1","t2"]',
        "volume24hr": 5000,
        "endDate": "2026-12-31T00:00:00Z",
        "active": True,
        "closed": False,
        "archived": False,
    }


def test_find_btc_threshold_filters_and_ranks():
    markets = [
        _raw("Will Bitcoin reach $80,000 in April?", "m1"),
        _raw("Will Ethereum hit $4K in May?", "m2"),          # filtered
        _raw("Will BTC hit $100K by end of year?", "m3"),
    ]

    # Bypass network entirely: fetcher returns our fixture.
    with patch.object(bs, "fetch_active_markets", return_value=markets), \
         patch.object(bs, "score_markets") as mock_score:
        # score_markets returns BetCandidate-like objects; mock returns them
        # in arbitrary order so the function MUST sort by edge*score desc.
        from analyzer import BetCandidate
        a = BetCandidate(market_id="m1", condition_id="0xm1",
                         question="Will Bitcoin reach $80,000 in April?",
                         outcome="No", outcome_index=1, token_id="t2",
                         probability=0.85, score=0.80, volume_24h=5000, spread=0.01,
                         edge=0.08, true_prob=0.93, kelly_stake=10.0, days_to_expiry=5)
        b = BetCandidate(market_id="m3", condition_id="0xm3",
                         question="Will BTC hit $100K by end of year?",
                         outcome="No", outcome_index=1, token_id="t4",
                         probability=0.82, score=0.75, volume_24h=8000, spread=0.02,
                         edge=0.15, true_prob=0.97, kelly_stake=12.0, days_to_expiry=180)
        mock_score.return_value = [a, b]

        out = bs.find_btc_threshold_candidates(limit=10)

    # Ethereum filtered out before scoring; b ranks above a (0.15*0.75 > 0.08*0.80).
    assert [c.market_id for c in out] == ["m3", "m1"]
    # score_markets was called with only the 2 BTC markets, not the ETH one
    passed_to_scorer = mock_score.call_args.args[0]
    assert {m["id"] for m in passed_to_scorer} == {"m1", "m3"}
```

- [ ] **Step 2: Run — verify failure**

Run: `cd polymarket-agent && python -m pytest test_btc_scanner.py -q`
Expected: FAIL — `AttributeError: module 'btc_scanner' has no attribute 'find_btc_threshold_candidates'`.

- [ ] **Step 3: Implement `find_btc_threshold_candidates`**

Append to `polymarket-agent/btc_scanner.py`:
```python
import logging

from fetcher import fetch_active_markets
from analyzer import BetCandidate, score_markets

logger = logging.getLogger("polymarket.btc_scanner")


def find_btc_threshold_candidates(limit: int = 20) -> list[BetCandidate]:
    """
    Read-only: pull all active markets, keep only BTC threshold ones,
    score via the existing analyzer, return top `limit` ranked by edge * score.
    """
    raw = fetch_active_markets()
    btc_only = [m for m in raw if is_btc_threshold(m.get("question", ""))]
    logger.info(
        "btc_scanner: %d/%d markets match BTC threshold pattern",
        len(btc_only), len(raw),
    )
    if not btc_only:
        return []

    candidates: list[BetCandidate] = score_markets(btc_only)

    def _rank_key(c: BetCandidate) -> float:
        edge = c.edge if c.edge is not None else 0.0
        return edge * c.score

    candidates.sort(key=_rank_key, reverse=True)
    return candidates[:limit]
```

- [ ] **Step 4: Run — verify pass**

Run: `cd polymarket-agent && python -m pytest test_btc_scanner.py -q`
Expected: PASS — `12 passed`.

- [ ] **Step 5: Commit**

```bash
git add polymarket-agent/btc_scanner.py polymarket-agent/test_btc_scanner.py
git commit -m "feat(polymarket): add find_btc_threshold_candidates (read-only)"
```

---

## Task 3: `snapshot()` — write ranked candidates to JSON

**Files:**
- Modify: `polymarket-agent/btc_scanner.py`
- Modify: `polymarket-agent/test_btc_scanner.py`

- [ ] **Step 1: Write the failing test**

Append to `polymarket-agent/test_btc_scanner.py`:
```python
import json


def test_snapshot_writes_expected_shape(tmp_path):
    from analyzer import BetCandidate
    candidates = [
        BetCandidate(market_id="m3", condition_id="0xm3",
                     question="Will BTC hit $100K?", outcome="No", outcome_index=1,
                     token_id="t4", probability=0.82, score=0.75, volume_24h=8000,
                     spread=0.02, edge=0.15, true_prob=0.97, kelly_stake=12.0,
                     days_to_expiry=180),
    ]
    out = tmp_path / "btc_candidates.json"
    bs.snapshot(candidates, out)

    payload = json.loads(out.read_text())
    assert "generated_at" in payload
    assert payload["count"] == 1
    assert payload["candidates"][0]["market_id"] == "m3"
    assert payload["candidates"][0]["edge"] == 0.15
    assert payload["candidates"][0]["kelly_stake"] == 12.0
    assert payload["candidates"][0]["question"] == "Will BTC hit $100K?"
```

- [ ] **Step 2: Run — verify failure**

Run: `cd polymarket-agent && python -m pytest test_btc_scanner.py::test_snapshot_writes_expected_shape -q`
Expected: FAIL — `AttributeError: module 'btc_scanner' has no attribute 'snapshot'`.

- [ ] **Step 3: Implement `snapshot`**

Append to `polymarket-agent/btc_scanner.py`:
```python
import json
from datetime import datetime, timezone
from pathlib import Path


def snapshot(candidates: list[BetCandidate], path: Path) -> None:
    """Write a JSON snapshot of ranked BTC candidates. Overwrites each cycle."""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(candidates),
        "candidates": [
            {
                "market_id":      c.market_id,
                "condition_id":   c.condition_id,
                "question":       c.question,
                "outcome":        c.outcome,
                "token_id":       c.token_id,
                "probability":    c.probability,
                "score":          round(c.score, 4),
                "edge":           round(c.edge, 4) if c.edge is not None else None,
                "true_prob":      round(c.true_prob, 4) if c.true_prob is not None else None,
                "kelly_stake":    round(c.kelly_stake, 2),
                "days_to_expiry": c.days_to_expiry,
                "volume_24h":     c.volume_24h,
                "spread":         c.spread,
            }
            for c in candidates
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run full test file — all green**

Run: `cd polymarket-agent && python -m pytest test_btc_scanner.py -q`
Expected: PASS — `13 passed`.

- [ ] **Step 5: Commit**

```bash
git add polymarket-agent/btc_scanner.py polymarket-agent/test_btc_scanner.py
git commit -m "feat(polymarket): add JSON snapshot for BTC candidates"
```

---

## Task 4: Config knobs for the scanner

**Files:**
- Modify: `polymarket-agent/config.py`

- [ ] **Step 1: Add the env-overridable config**

Open `polymarket-agent/config.py` and add these lines **after** the existing `MAX_BETS_PER_CATEGORY = ...` line (around line 39):

```python
# ── BTC scanner (read-only, v1 — no bets placed) ─────────────────────────
BTC_SCANNER_ENABLED       = os.getenv("BTC_SCANNER_ENABLED", "true").lower() == "true"
BTC_SCAN_INTERVAL_MINUTES = int(os.getenv("BTC_SCAN_INTERVAL_MINUTES", "15"))
BTC_TOP_N                 = int(os.getenv("BTC_TOP_N", "20"))
```

- [ ] **Step 2: Verify import doesn't break the agent**

Run: `cd polymarket-agent && python -c "import config; print('enabled:', config.BTC_SCANNER_ENABLED, '| interval:', config.BTC_SCAN_INTERVAL_MINUTES, '| top_n:', config.BTC_TOP_N)"`
Expected: `enabled: True | interval: 15 | top_n: 20`.

- [ ] **Step 3: Commit**

```bash
git add polymarket-agent/config.py
git commit -m "feat(polymarket): config knobs for BTC scanner"
```

---

## Task 5: `--btc-scan` CLI flag in `main.py`

**Files:**
- Modify: `polymarket-agent/main.py`

- [ ] **Step 1: Add argparse + dispatch at the top of `main()`**

In `polymarket-agent/main.py`, replace the existing `def main():` first line + body opener with the version that parses args and dispatches early when `--btc-scan` is passed. Concretely, change:

```python
def main():
    mode = "LIVE" if not config.DRY_RUN else "DRY-RUN"
    logger.info("Polymarket Agent starting… [%s]", mode)
    database.init_db()
```

to:

```python
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Polymarket Agent")
    parser.add_argument(
        "--btc-scan",
        action="store_true",
        help="Run the BTC threshold scanner once (read-only), print + snapshot, exit.",
    )
    args = parser.parse_args()

    if args.btc_scan:
        import btc_scanner
        from pathlib import Path
        logger.info("Running BTC threshold scanner (one-shot, read-only)…")
        candidates = btc_scanner.find_btc_threshold_candidates(limit=config.BTC_TOP_N)
        out = Path(__file__).parent / "btc_candidates.json"
        btc_scanner.snapshot(candidates, out)
        print(f"\n{'rank':<4} {'edge':>6} {'score':>6} {'days':>4} {'kelly':>6}  question")
        print("-" * 92)
        for i, c in enumerate(candidates, 1):
            edge = (c.edge or 0) * 100
            print(f"{i:<4} {edge:5.1f}% {c.score:6.2f} {c.days_to_expiry or '—':>4} ${c.kelly_stake:5.2f}  {c.question[:55]}")
        print(f"\n→ Snapshot written to {out} ({len(candidates)} candidates)")
        return

    mode = "LIVE" if not config.DRY_RUN else "DRY-RUN"
    logger.info("Polymarket Agent starting… [%s]", mode)
    database.init_db()
```

- [ ] **Step 2: Smoke-test the CLI against the real Polymarket API**

Run: `cd polymarket-agent && python main.py --btc-scan 2>&1 | tail -15`
Expected: a ranked table (may be empty if no BTC threshold markets are currently live), and a "Snapshot written to …/btc_candidates.json" line. Exit cleanly.

- [ ] **Step 3: Verify the snapshot file**

Run: `cd polymarket-agent && python3 -c "import json; d=json.load(open('btc_candidates.json')); print('count:', d['count'], '| generated_at:', d['generated_at'])"`
Expected: prints a count (0 or more) and a recent timestamp.

- [ ] **Step 4: Commit**

```bash
git add polymarket-agent/main.py
git commit -m "feat(polymarket): --btc-scan CLI (one-shot, read-only)"
```

---

## Task 6: Add the 15-min BTC scanner thread

**Files:**
- Modify: `polymarket-agent/main.py`

- [ ] **Step 1: Add a `_run_btc_scan` helper near the existing scan helpers**

In `polymarket-agent/main.py`, add this function **near the other `_run_*` helpers** (search for `def _run_scan` and add right after it):

```python
def _run_btc_scan() -> None:
    """Read-only BTC scanner cycle: find, rank, snapshot. No bets placed."""
    import btc_scanner
    from pathlib import Path
    try:
        candidates = btc_scanner.find_btc_threshold_candidates(limit=config.BTC_TOP_N)
        out = Path(__file__).parent / "btc_candidates.json"
        btc_scanner.snapshot(candidates, out)
        top = candidates[0] if candidates else None
        logger.info(
            "BTC scan: %d candidates | top: %s | edge=%.1f%%",
            len(candidates),
            (top.question[:50] if top else "—"),
            ((top.edge or 0) * 100 if top else 0.0),
        )
    except Exception as exc:
        logger.error("BTC scan failed: %s", exc)
```

- [ ] **Step 2: Wire the thread (opt-in via env) into `main()` right after `web_thread = …` is defined**

Find this block:

```python
    web_thread = threading.Thread(
        target=run_web,
        kwargs={"host": config.WEB_HOST, "port": config.WEB_PORT},
        daemon=True,
        name="web",
    )

    scan_thread.start()
    track_thread.start()
    web_thread.start()
```

Replace it with:

```python
    web_thread = threading.Thread(
        target=run_web,
        kwargs={"host": config.WEB_HOST, "port": config.WEB_PORT},
        daemon=True,
        name="web",
    )

    # BTC scanner thread — read-only, opt-in via BTC_SCANNER_ENABLED env
    btc_thread = None
    if config.BTC_SCANNER_ENABLED:
        btc_thread = threading.Thread(
            target=_scheduler_thread,
            args=(_run_btc_scan, config.BTC_SCAN_INTERVAL_MINUTES, "next_btc_scan_secs"),
            daemon=True,
            name="btc_scan",
        )

    scan_thread.start()
    track_thread.start()
    web_thread.start()
    if btc_thread:
        btc_thread.start()
        logger.info(
            "BTC scanner thread started (read-only, every %d min)",
            config.BTC_SCAN_INTERVAL_MINUTES,
        )
```

- [ ] **Step 3: Smoke-test: agent starts cleanly with the BTC thread enabled**

This requires running `main.py` — which keeps running. Quick check: launch for ~20 seconds and confirm the BTC scanner log line appears, then Ctrl-C.

Run:
```
cd polymarket-agent
timeout 25 python main.py 2>&1 | grep -E 'BTC|scan_thread|Threads' | head -10 || true
```
Expected: see lines like `BTC scanner thread started (read-only, every 15 min)` and `BTC scan: N candidates | top: …`.

(If you don't want to start the agent right now, skip this step and verify later when you restart `main.py` for the sizing changes.)

- [ ] **Step 4: Commit**

```bash
git add polymarket-agent/main.py
git commit -m "feat(polymarket): scheduled BTC scanner thread (read-only)"
```

---

## Task 7: gitignore the scanner outputs

**Files:**
- Modify: `polymarket-agent/.gitignore` (create if missing)

- [ ] **Step 1: Check whether the agent already has a .gitignore**

Run: `ls polymarket-agent/.gitignore 2>&1 || echo "no local .gitignore — root one applies"`

- [ ] **Step 2: Add the scanner outputs to the appropriate .gitignore**

If `polymarket-agent/.gitignore` exists, append:
```
btc_candidates.json
btc_scanner.log
```
If it doesn't exist, append the same two lines to the root `/Users/sergiofruto/Projects/claude-code-agents/.gitignore` (which already covers `*.log`, so really only `btc_candidates.json` is new — but listing both keeps intent explicit).

- [ ] **Step 3: Verify it's ignored**

Run: `cd /Users/sergiofruto/Projects/claude-code-agents && git check-ignore polymarket-agent/btc_candidates.json && echo "ignored ✓"`
Expected: prints the path then `ignored ✓`.

- [ ] **Step 4: Commit**

```bash
git add polymarket-agent/.gitignore 2>/dev/null; git add .gitignore 2>/dev/null
git commit -m "chore(polymarket): gitignore BTC scanner outputs"
```

---

## Self-Review Notes

- **Spec coverage:**
  - "New module `btc_scanner.py` with `_is_btc_threshold` and `find_btc_threshold_candidates`" → Tasks 1, 2. (Spec called it `_is_btc_threshold`; plan exports the public name as `is_btc_threshold` — public-API helper, not private; tests reference the same name.)
  - "JSON snapshot to `btc_candidates.json`" → Task 3.
  - "`--btc-scan` CLI in `main.py`" → Task 5.
  - "15-min scheduler thread, opt-in via `BTC_SCANNER_ENABLED`" → Tasks 4 + 6.
  - ".gitignore the snapshot + log" → Task 7.
  - "No bets placed in v1" → never reached; `place_bet` not imported by `btc_scanner.py`. Confirmed in Task 2/3 code.
  - "Reuses fetcher / analyzer / signals._crypto_edge" → Task 2 imports `fetch_active_markets` + `score_markets`; `_crypto_edge` runs inside `score_markets`. No duplication.
  - "One regex unit test with true/false positives" → Task 1 covers 11 cases.
  - "Promotion criteria for Phase 2 (≥1 week, ≥15 markets, +5pp ROI, ≥70% win rate)" → in spec, deferred to Phase 2 spec; not a code task here.

- **Placeholder scan:** none — every code step shows full code; CLI smoke and snapshot verification have concrete commands + expected output.

- **Type consistency:** `BetCandidate` fields used in tests and `snapshot()` match the actual dataclass (`market_id`, `condition_id`, `question`, `outcome`, `outcome_index`, `token_id`, `probability`, `score`, `volume_24h`, `spread`, `edge`, `true_prob`, `kelly_stake`, `days_to_expiry`). The mock fixture `_raw()` mirrors the keys `fetcher.fetch_active_markets` emits. Public function names (`is_btc_threshold`, `find_btc_threshold_candidates`, `snapshot`) match the spec and across tasks.

- **One spec deviation flagged:** spec used `_is_btc_threshold` (private prefix); plan uses `is_btc_threshold` (public). Reason: it's imported directly from tests + may be useful externally; underscore would force test imports of a "private" function. Trivial, not load-bearing.
