import json

from conftest import F
from models import CheckResult
from scan import run_scan


def summary(db):
    rows = db.execute("SELECT * FROM solaris_summary").fetchall()
    assert len(rows) == 1
    return dict(rows[0])


def test_summary_view_has_only_counts_and_title(db):
    run_scan(db, [("secrets", lambda: CheckResult("secrets", [F("secrets:x", sev="medium", title="Wallet or private key stored in a plain file", evidence="polymarket-agent/.env: wallet_private_key on line 6")]))])
    row = summary(db)
    assert row["medium"] == 1 and row["worst_title"] == "Wallet or private key stored in a plain file"
    assert ".env" not in json.dumps(row)


def test_worst_title_is_highest_severity(db):
    run_scan(db, [("ports", lambda: CheckResult("ports", [F("a", sev="low", title="low one"), F("b", sev="high", title="high one"), F("c", sev="medium", title="mid")]))])
    row = summary(db)
    assert (row["high"], row["medium"], row["low"], row["info"]) == (1, 1, 1, 0)
    assert row["worst_title"] == "high one"


def test_empty_db_still_has_one_row(db):
    row = summary(db)
    assert row["id"] == 1 and row["last_scan_at"] is None and row["high"] == 0 and row["providers_not_up"] == 0


def test_providers_and_digest_counts_use_latest_rows(db):
    db.executemany("INSERT INTO status_checks (service, checked_at, state) VALUES (?, ?, ?)", [
        ("Vercel", "2026-10-24T08:00:00", "down"), ("Vercel", "2026-10-24T09:00:00", "up"),
        ("GitHub", "2026-10-24T09:00:00", "degraded"), ("AWS", "2026-10-24T09:00:00", "no_data")])
    db.execute("INSERT INTO digests (id, day, built_at) VALUES (1, '2026-10-23', 'x'), (2, '2026-10-24', 'y')")
    db.executemany("INSERT INTO digest_entries (digest_id, rank, title, affects_json) VALUES (?, ?, ?, ?)", [
        (1, 1, "old", '["chrome"]'), (2, 1, "a", '["chrome"]'), (2, 2, "b", "[]"), (2, 3, "c", '["next.js"]')])
    row = summary(db)
    assert row["providers_not_up"] == 1 and row["digest_affecting"] == 2
