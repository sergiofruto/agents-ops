import json
from unittest.mock import patch

import pytest

import btc_scanner as bs
from btc_scanner import is_btc_threshold
from analyzer import BetCandidate


# ── Pattern detector ────────────────────────────────────────────────────────

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


# ── Candidate finder ─────────────────────────────────────────────────────────

def _raw(question: str, market_id: str = "m1") -> dict:
    """Minimal raw-market dict mimicking fetcher.fetch_active_markets output."""
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
        _raw("Will Ethereum hit $4K in May?", "m2"),          # filtered out
        _raw("Will BTC hit $100K by end of year?", "m3"),
    ]

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

    with patch.object(bs, "fetch_active_markets", return_value=markets), \
         patch.object(bs, "score_markets", return_value=[a, b]) as mock_score:
        out = bs.find_btc_threshold_candidates(limit=10)

    # Sorted by edge * score descending: b (0.15 * 0.75 = 0.1125) > a (0.08 * 0.80 = 0.064)
    assert [c.market_id for c in out] == ["m3", "m1"]
    # ETH market filtered BEFORE scoring
    passed = mock_score.call_args.args[0]
    assert {m["id"] for m in passed} == {"m1", "m3"}


# ── Snapshot writer ──────────────────────────────────────────────────────────

def test_snapshot_writes_expected_shape(tmp_path):
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
