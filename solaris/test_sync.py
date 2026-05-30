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
