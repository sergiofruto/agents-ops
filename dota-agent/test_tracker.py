"""
Unit test: tracker must look markets up by Gamma's numeric market id.
Gamma's /markets/{id} rejects condition ids with 422, which left bets open forever.

Usage:  python -m pytest test_tracker.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import fetcher
import tracker


def test_check_single_fetches_by_market_id(monkeypatch):
    calls = []
    monkeypatch.setattr(fetcher, "fetch_market_detail", lambda mid: calls.append(mid) or {})

    tracker._check_single({"market_id": "2001563", "condition_id": "0xf7d9"})

    assert calls == ["2001563"]
