"""
Smoke test: inject a synthetic Dota market and run the full pipeline.

Usage:  python test_pipeline.py
        python test_pipeline.py --keep   (don't delete the test bet afterwards)
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import config
import database
import fetcher
import opendota
import analyzer
import simulator

# ---------------------------------------------------------------------------
# Synthetic market — mimics a real Polymarket moneyline response
# ---------------------------------------------------------------------------
FAKE_MARKET = {
    "id":            "test-aurora-liquid-fake",
    "conditionId":   "test-aurora-liquid-fake",
    "question":      "Dota 2: Aurora vs Team Liquid (BO3) - DreamLeague Grand Final",
    "sportsMarketType": "moneyline",
    "outcomePrices": json.dumps(["0.72", "0.28"]),   # Aurora 72% implied
    "outcomes":      json.dumps(["Aurora", "Team Liquid"]),
    "clobTokenIds":  json.dumps(["tok-a", "tok-b"]),
    "volume24hr":    85_000,
    "spread":        0.03,
    "groupItemTitle": "DreamLeague Season 25",
    "active": True,
    "closed": False,
    "resolved": False,
}


def main(keep: bool = False):
    print("=== Dota Agent Smoke Test ===\n")

    # 1. DB init
    database.init_db()
    print("✓ Database initialised")

    # 2. Roster build (live call to OpenDota)
    print("  Building OpenDota team roster (live call)…")
    opendota.build_team_roster()
    n = len(opendota._roster)
    print(f"✓ Roster: {n} teams indexed")

    # 3. Team resolution
    for name in ["Aurora", "Team Liquid"]:
        result = opendota.resolve_team_id(name)
        if result:
            tid, rating = result
            print(f"  resolve({name!r}) → id={tid}, rating={rating:.1f}")
        else:
            print(f"  resolve({name!r}) → NOT FOUND (OpenDota may lack this team)")

    # 4. True probability
    print("\n  Computing true probability (live OpenDota calls)…")
    signals = opendota.compute_true_prob("Aurora", "Team Liquid", FAKE_MARKET)
    if signals:
        print(f"  Signals: {signals}")
    else:
        print("  WARNING: compute_true_prob returned None (team not in roster)")
        print("  Injecting synthetic signals for pipeline test…")
        signals = {
            "true_prob":   0.78,
            "elo_prob":    0.76,
            "form_a":      0.68,
            "form_b":      0.52,
            "h2h_winrate": 0.60,
            "h2h_sample":  8,
            "league_tier": "premium",
        }

    # 5. Build a candidate manually (bypasses probability-window filter)
    true_prob    = signals["true_prob"]
    market_prob  = 0.72
    edge         = true_prob - market_prob

    print(f"\n  market_prob={market_prob:.2%}  true_prob={true_prob:.2%}  edge={edge:+.2%}")

    if edge < config.MIN_EDGE:
        print(f"  (edge {edge:.2%} < MIN_EDGE {config.MIN_EDGE:.2%} — would be filtered)")
        print("  Overriding edge for smoke-test purposes…")
        true_prob = market_prob + config.MIN_EDGE + 0.01
        edge      = true_prob - market_prob
        signals["true_prob"] = true_prob

    from analyzer import DotaBetCandidate, _composite_score, _kelly_stake
    composite = _composite_score(
        edge,
        signals["form_a"],
        signals["h2h_winrate"],
        signals["h2h_sample"],
        signals["league_tier"],
    )
    stake = _kelly_stake(true_prob, market_prob)

    candidate = DotaBetCandidate(
        market_id    = FAKE_MARKET["id"],
        condition_id = FAKE_MARKET["conditionId"],
        question     = FAKE_MARKET["question"],
        outcome      = "Aurora",
        outcome_index= 0,
        token_id     = "tok-a",
        probability  = market_prob,
        score        = round(composite, 4),
        volume_24h   = FAKE_MARKET["volume24hr"],
        spread       = FAKE_MARKET["spread"],
        team_a       = "Aurora",
        team_b       = "Team Liquid",
        tournament   = "DreamLeague Season 25",
        edge         = round(edge, 4),
        true_prob    = signals["true_prob"],
        elo_prob     = signals["elo_prob"],
        form_a       = signals["form_a"],
        form_b       = signals["form_b"],
        h2h_winrate  = signals["h2h_winrate"],
        h2h_sample   = signals["h2h_sample"],
        league_tier  = signals["league_tier"],
        kelly_stake  = round(stake, 2),
    )

    print(f"  Composite score: {composite:.4f}  (MIN_SCORE={config.MIN_SCORE})")
    print(f"  Kelly stake: ${stake:.2f}")

    # 6. Simulate placement
    print("\n  Placing dry bet…")
    placed = simulator.place_dry_bet(candidate)
    print(f"✓ Bet placed: {placed}")

    # 7. Read back from DB
    bets = database.get_all_bets()
    test_bets = [b for b in bets if b["market_id"] == FAKE_MARKET["id"]]
    if test_bets:
        b = test_bets[0]
        print(f"\n  DB row #{b['id']}:")
        print(f"    question:    {b['question']}")
        print(f"    team_a/b:    {b['team_a']} vs {b['team_b']}")
        print(f"    outcome:     {b['outcome']} @ {b['price_at_bet']:.2%}")
        print(f"    true_prob:   {b['true_prob']:.2%}")
        print(f"    edge:        {b['edge']:+.2%}")
        print(f"    score:       {b['score']:.4f}")
        print(f"    stake:       ${b['virtual_amount']:.2f}")
        print(f"    payout:      ${b['potential_payout']:.2f}")
        print(f"    league_tier: {b['league_tier']}")
        print(f"    status:      {b['status']}")
    else:
        print("  ERROR: bet not found in DB")

    # 8. Cleanup (unless --keep)
    if not keep:
        import sqlite3
        with database.get_connection() as conn:
            conn.execute("DELETE FROM bets WHERE market_id=?", (FAKE_MARKET["id"],))
        print(f"\n  Test bet cleaned up (use --keep to retain it)")
    else:
        print(f"\n  Test bet retained in DB — visible at http://localhost:5002")

    stats = database.get_stats()
    print(f"\n✓ Stats: {stats}")
    print("\n=== Smoke test complete ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="Keep the test bet in the DB")
    args = parser.parse_args()
    main(keep=args.keep)
