"""
Dota Agent — Model Backtest
============================
Tests the Elo + form + H2H prediction model against historical match results
fetched from OpenDota.

Method
------
1. Pull top N teams by Elo rating from OpenDota.
2. For each team, fetch recent matches (last LOOKBACK_DAYS days).
3. Deduplicate matches by match_id.
4. For each unique match where both teams are in the roster:
   - Compute elo_win_probability (pure signal, no look-ahead bias).
   - Compute the full model's true_prob (form/H2H use current data → slight
     look-ahead for very recent matches; noted in output).
5. Compare predicted winner (prob > 0.50) vs actual winner.
6. Report accuracy, Brier score, calibration buckets, and simulated P&L.

Also runs a small Polymarket sanity-check: fetches recently closed Dota
markets and verifies which side the model would have backed.

Usage
-----
    python backtest.py
    python backtest.py --days 180 --teams 30
    python backtest.py --days 60 --min-league-tier professional
"""

import argparse
import sys
import os
import time
import math
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))

import requests
import config
import database
import opendota

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json"})
_TIMEOUT = 15

LOOKBACK_DAYS = 90
N_TOP_TEAMS   = 25


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch(url: str, params: dict = None) -> list | dict:
    resp = SESSION.get(url, params=params or {}, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _fetch_closed_poly_dota(limit: int = 100) -> list[dict]:
    """Fetch closed Dota 2 markets from Polymarket Gamma API."""
    try:
        data = _fetch(
            f"{config.GAMMA_BASE}/markets",
            params={"closed": "true", "limit": limit, "order": "closedTime", "ascending": "false"},
        )
        markets = data if isinstance(data, list) else data.get("data", [])
        return [m for m in markets if "dota" in m.get("question", "").lower()]
    except Exception as e:
        print(f"  Polymarket fetch failed: {e}")
        return []


def _brier_score(records: list[tuple[float, int]]) -> float:
    """Mean squared error between predicted prob and actual outcome (0/1)."""
    if not records:
        return float("nan")
    return sum((p - a) ** 2 for p, a in records) / len(records)


def _log_loss(records: list[tuple[float, int]]) -> float:
    """Binary cross-entropy."""
    if not records:
        return float("nan")
    eps = 1e-9
    return -sum(
        a * math.log(max(p, eps)) + (1 - a) * math.log(max(1 - p, eps))
        for p, a in records
    ) / len(records)


def _simulated_pnl(
    records: list[tuple[float, float, int]],
    bankroll: float = 10_000,
    kelly_frac: float = 0.5,
    min_edge: float = 0.05,
) -> dict:
    """
    Simulate Kelly-staked bets on every match where model edge >= min_edge.
    Each record is (true_prob, market_prob, actual_win).
    market_prob is elo_prob (used as a proxy for the efficient market price).
    """
    bets, wins, total_staked, total_pnl = 0, 0, 0.0, 0.0
    for true_p, mkt_p, actual in records:
        edge = true_p - mkt_p
        if edge < min_edge:
            continue
        b = 1.0 / mkt_p - 1.0
        kelly = (true_p * b - (1 - true_p)) / b * kelly_frac
        if kelly <= 0:
            continue
        stake = max(10, min(200, kelly * bankroll))
        payout = stake / mkt_p
        pnl    = payout - stake if actual else -stake
        bets       += 1
        wins       += actual
        total_staked += stake
        total_pnl    += pnl

    roi = (total_pnl / total_staked * 100) if total_staked > 0 else 0.0
    return {
        "bets": bets,
        "wins": wins,
        "staked": round(total_staked, 2),
        "pnl":   round(total_pnl, 2),
        "roi":   round(roi, 1),
        "win_rate": round(wins / bets * 100, 1) if bets > 0 else 0.0,
    }


def _calibration_table(
    records: list[tuple[float, int]],
    buckets: int = 5,
) -> list[dict]:
    """Group predictions into probability buckets and measure actual win rate."""
    grouped = defaultdict(list)
    step = 1.0 / buckets
    for prob, actual in records:
        bucket = min(int(prob / step), buckets - 1)
        grouped[bucket].append(actual)

    rows = []
    for i in range(buckets):
        lo = i * step
        hi = lo + step
        items = grouped.get(i, [])
        actual_rate = sum(items) / len(items) if items else float("nan")
        mid = (lo + hi) / 2
        rows.append({
            "range": f"{lo:.0%}–{hi:.0%}",
            "n": len(items),
            "predicted_mid": mid,
            "actual_win_rate": actual_rate,
            "error": actual_rate - mid if items else float("nan"),
        })
    return rows


# ---------------------------------------------------------------------------
# Main backtest
# ---------------------------------------------------------------------------

def run(days: int = LOOKBACK_DAYS, n_teams: int = N_TOP_TEAMS):
    print(f"\n{'='*60}")
    print(f"  Dota Agent — Model Backtest")
    print(f"  Lookback: {days} days  |  Top teams: {n_teams}")
    print(f"{'='*60}\n")

    # 1. Build roster
    print("Step 1/4  Building team roster…")
    opendota.build_team_roster(limit=1000)
    roster = opendota._roster  # name → (team_id, rating)
    print(f"          {len(roster)} teams indexed\n")

    # Select top N teams by rating
    top_teams = sorted(roster.items(), key=lambda kv: kv[1][1], reverse=True)[:n_teams]
    print(f"Step 2/4  Fetching matches for top {n_teams} teams…")

    cutoff_ts = time.time() - days * 86400
    all_matches: dict[int, dict] = {}   # match_id → enriched record
    id_to_rating: dict[int, float] = {tid: r for _, (tid, r) in roster.items()}

    for name, (team_id, rating) in top_teams:
        raw_matches = opendota._fetch_team_matches(team_id, limit=100)
        new = 0
        for m in raw_matches:
            mid = m.get("match_id")
            if not mid or m.get("start_time", 0) < cutoff_ts:
                continue
            if mid in all_matches:
                continue

            opp_id = m.get("opposing_team_id")
            if not opp_id:
                continue

            # team_a = queried team, team_b = opponent
            # team_a_won = (is_radiant == radiant_won)
            is_radiant  = m.get("radiant", False)
            radiant_win = m.get("radiant_win", False)
            team_a_won  = int(is_radiant == radiant_win)

            all_matches[mid] = {
                "match_id":    mid,
                "league":      m.get("league_name", ""),
                "start_time":  m.get("start_time", 0),
                "team_a_id":   team_id,
                "team_a_name": name,
                "team_b_id":   opp_id,
                "team_b_name": m.get("opposing_team_name", ""),
                "team_a_won":  team_a_won,
                "rating_a":    rating,
                "rating_b":    id_to_rating.get(opp_id, 0.0),
            }
            new += 1

        print(f"          {name[:28]:28}  rating={rating:6.1f}  +{new} matches")
        time.sleep(0.3)   # gentle rate-limit

    print(f"\n          Total unique matches collected: {len(all_matches)}")

    # Filter to matches where both teams have known ratings
    usable = [
        r for r in all_matches.values()
        if r["rating_a"] > 0 and r["rating_b"] > 0
    ]
    print(f"          Matches with both ratings known: {len(usable)}\n")

    if not usable:
        print("ERROR: No usable matches found. Widen --days or --teams.")
        return

    # 3. Apply model
    print("Step 3/4  Applying model to each match…")

    elo_records:   list[tuple[float, int]]        = []  # (elo_prob,  actual)
    model_records: list[tuple[float, int]]        = []  # (true_prob, actual)
    pnl_records:   list[tuple[float, float, int]] = []  # (true_prob, elo_prob, actual)
    match_rows:    list[dict]                     = []  # for DB persistence
    skipped = 0

    for r in usable:
        elo_p = opendota.elo_win_probability(r["rating_a"], r["rating_b"])
        actual = r["team_a_won"]
        elo_records.append((elo_p, actual))

        try:
            signals = opendota.compute_true_prob(r["team_a_name"], r["team_b_name"])
        except Exception:
            signals = None

        if signals:
            tp      = signals["true_prob"]
            raw_tp  = signals.get("raw_true_prob", tp)
            correct = int((tp > 0.5) == bool(actual))
            model_records.append((tp, actual))
            pnl_records.append((tp, elo_p, actual))
            match_rows.append({
                "match_id":     r["match_id"],
                "team_a":       r["team_a_name"],
                "team_b":       r["team_b_name"],
                "league":       r.get("league", ""),
                "start_time":   r.get("start_time", 0),
                "elo_prob":     round(elo_p, 4),
                "raw_true_prob": round(raw_tp, 4),
                "true_prob":    round(tp, 4),
                "team_a_won":   actual,
                "model_correct": correct,
            })
        else:
            skipped += 1

    print(f"          Scored: {len(model_records)}  |  Skipped (no signal): {skipped}\n")

    # 4. Results
    print("Step 4/4  Computing metrics…\n")

    # -- Accuracy --
    elo_correct   = sum(1 for p, a in elo_records   if (p > 0.5) == bool(a))
    model_correct = sum(1 for p, a in model_records if (p > 0.5) == bool(a))

    elo_acc   = elo_correct   / len(elo_records)   * 100
    model_acc = model_correct / len(model_records) * 100

    # -- Brier / Log-Loss --
    elo_brier   = _brier_score(elo_records)
    model_brier = _brier_score(model_records)
    elo_ll      = _log_loss(elo_records)
    model_ll    = _log_loss(model_records)

    # Baseline: always predict 50%
    baseline_brier = _brier_score([(0.5, a) for _, a in elo_records])

    # -- Simulated P&L (vs elo_prob as market proxy) --
    pnl = _simulated_pnl(pnl_records)

    # -- Calibration --
    elo_cal   = _calibration_table(elo_records)
    model_cal = _calibration_table(model_records)

    # ---- Print report ----
    print(f"{'─'*60}")
    print(f"  ACCURACY (predicted winner = actual winner)")
    print(f"{'─'*60}")
    print(f"  Baseline  (always 50%)     : 50.0%")
    print(f"  Elo-only                   : {elo_acc:5.1f}%   (n={len(elo_records)})")
    print(f"  Full model (Elo+form+H2H)  : {model_acc:5.1f}%   (n={len(model_records)})")
    print()

    print(f"{'─'*60}")
    print(f"  CALIBRATION  (lower Brier = better; baseline = {baseline_brier:.4f})")
    print(f"{'─'*60}")
    print(f"  Elo-only   Brier={elo_brier:.4f}  LogLoss={elo_ll:.4f}")
    print(f"  Full model Brier={model_brier:.4f}  LogLoss={model_ll:.4f}")
    print()

    print(f"{'─'*60}")
    print(f"  CALIBRATION TABLE — Full model")
    print(f"{'─'*60}")
    print(f"  {'Prob range':12}  {'N':>5}  {'Pred mid':>9}  {'Actual win%':>11}  {'Error':>7}")
    for row in model_cal:
        n = row["n"]
        if n == 0:
            continue
        err_str = f"{row['error']:+.1%}" if not math.isnan(row["error"]) else "  n/a"
        aw      = f"{row['actual_win_rate']:.1%}" if not math.isnan(row["actual_win_rate"]) else "  n/a"
        print(f"  {row['range']:12}  {n:>5}  {row['predicted_mid']:>9.1%}  {aw:>11}  {err_str:>7}")
    print()

    print(f"{'─'*60}")
    print(f"  SIMULATED P&L  (edge gate: 5%, half-Kelly, $10–$200/bet)")
    print(f"  NOTE: market price proxied by elo_prob — real Polymarket prices")
    print(f"        would differ; treat as directional, not absolute.")
    print(f"{'─'*60}")
    if pnl["bets"] > 0:
        print(f"  Bets placed : {pnl['bets']}")
        print(f"  Win rate    : {pnl['win_rate']}%")
        print(f"  Total staked: ${pnl['staked']:,.2f}")
        print(f"  P&L         : ${pnl['pnl']:+,.2f}")
        print(f"  ROI         : {pnl['roi']:+.1f}%")
    else:
        print("  No bets cleared edge gate.")
    print()

    # -- Polymarket sanity check --
    print(f"{'─'*60}")
    print(f"  POLYMARKET SANITY CHECK — closed Dota markets")
    print(f"{'─'*60}")
    poly_markets = _fetch_closed_poly_dota(limit=200)
    if not poly_markets:
        print("  No closed Dota markets found on Polymarket.")
    else:
        import json, re
        _VS = re.compile(r"(?:dota\s*2\s*[:\-]\s*)?([^vV]+?)\s+vs\.?\s+([^\(\?]+)", re.I)
        correct_poly = 0
        total_poly   = 0
        for m in poly_markets:
            q = m.get("question", "")
            match = _VS.search(q)
            if not match:
                continue
            ta = match.group(1).strip()
            tb = re.sub(r"\s*[\(\?].*$", "", match.group(2)).strip()

            # Determine actual winner from settled outcomePrices
            raw = m.get("outcomePrices", "[]")
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except Exception:
                    continue
            prices = []
            try:
                prices = [float(p) for p in raw]
            except Exception:
                continue
            if not prices or max(prices) < 0.99:
                continue  # not fully settled

            outcomes_raw = m.get("outcomes", "[]")
            if isinstance(outcomes_raw, str):
                try:
                    outcomes_raw = json.loads(outcomes_raw)
                except Exception:
                    continue
            outcomes = [str(o) for o in outcomes_raw]

            winner_idx  = prices.index(max(prices))
            winner_name = outcomes[winner_idx] if winner_idx < len(outcomes) else ta

            signals = opendota.compute_true_prob(ta, tb)
            if not signals:
                continue

            model_picks_a = signals["true_prob"] > 0.5
            actual_a_won  = winner_name.lower() in ta.lower() or ta.lower() in winner_name.lower()

            model_correct_here = model_picks_a == actual_a_won
            correct_poly += int(model_correct_here)
            total_poly   += 1

            tick = "✓" if model_correct_here else "✗"
            print(f"  {tick}  {ta[:20]:20} vs {tb[:20]:20}  "
                  f"model={signals['true_prob']:.0%} for {ta[:12]}  "
                  f"winner={winner_name[:16]}")

        if total_poly > 0:
            print(f"\n  Polymarket accuracy: {correct_poly}/{total_poly} = "
                  f"{correct_poly/total_poly:.0%}")
        else:
            print("  Could not match teams for any closed Polymarket markets.")
    print()

    # -- Persist to DB --
    database.init_db()
    run_id = database.save_backtest_run(
        days               = days,
        n_teams            = n_teams,
        n_matches          = len(model_records),
        elo_accuracy       = round(elo_acc / 100, 4),
        model_accuracy     = round(model_acc / 100, 4),
        elo_brier          = elo_brier,
        model_brier        = model_brier,
        baseline_brier     = baseline_brier,
        calibration_factor = config.CALIBRATION_FACTOR,
        matches            = match_rows,
    )
    print(f"  Results saved to DB (run #{run_id}) — visible at http://localhost:5002\n")

    # -- Summary verdict --
    print(f"{'='*60}")
    print(f"  VERDICT")
    print(f"{'='*60}")
    delta_acc  = model_acc - 50.0
    delta_brier = baseline_brier - model_brier  # positive = better than random

    if model_acc >= 58 and delta_brier > 0:
        verdict = "PROMISING — model beats random; edge filter likely valid."
    elif model_acc >= 53:
        verdict = "MARGINAL — small edge exists; watch for small sample size."
    else:
        verdict = "WEAK — model not reliably better than random. Revisit signals."

    print(f"  Accuracy lift vs 50% baseline : {delta_acc:+.1f}pp")
    print(f"  Brier improvement vs baseline : {delta_brier:+.4f}")
    print(f"  Assessment: {verdict}")
    print(f"{'='*60}\n")

    print("NOTE: Form/H2H signals use CURRENT team data, not data from match")
    print("      date. For very recent matches this is approximate; for matches")
    print("      >30 days old it may introduce look-ahead bias.")
    print("      Elo-only accuracy is the cleanest signal (no look-ahead).\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest the Dota agent model")
    parser.add_argument("--days",   type=int, default=LOOKBACK_DAYS,
                        help=f"Lookback window in days (default {LOOKBACK_DAYS})")
    parser.add_argument("--teams",  type=int, default=N_TOP_TEAMS,
                        help=f"Number of top teams to sample (default {N_TOP_TEAMS})")
    args = parser.parse_args()
    run(days=args.days, n_teams=args.teams)
