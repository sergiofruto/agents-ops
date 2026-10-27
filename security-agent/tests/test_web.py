import json

import pytest

from analyst import Claude
from budget import Budget
from conftest import F
from fakes import FakeClaudeClient, fake_text
from models import CheckResult
from scan import SCAN_LOCK, run_scan
from web.app import create_app


def make_client(db, claude_client=None):
    app = create_app(db_factory=lambda: db, claude_factory=lambda conn: Claude(claude_client, Budget(conn)))
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def client(db):
    return make_client(db)


def insert_digest(db, title, summary=None):
    cur = db.execute("INSERT INTO digests (day, built_at, used_ai) VALUES ('2026-10-24', '2026-10-24T08:00:00', 0)")
    db.execute("INSERT INTO digest_entries VALUES (?,?,?,?,?,?,?,?,?)",
               (cur.lastrowid, 0, title, summary, None, None, "[]",
                json.dumps([{"source": "CISA KEV", "url": "https://cisa.gov/x", "title": title}]), 1))
    db.commit()


def test_pages_render_with_empty_db(client):
    for path in ("/", "/scan", "/digest", "/status"):
        assert client.get(path).status_code == 200


def test_scan_conflict(client):
    SCAN_LOCK.acquire()
    try:
        assert client.post("/api/scan").status_code == 409
        assert client.get("/api/scan/state").get_json()["running"] is True
    finally:
        SCAN_LOCK.release()


def test_feed_html_is_escaped(client, db):
    insert_digest(db, title="<script>alert(1)</script>")
    body = client.get("/digest").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in body and "&lt;script&gt;" in body


def test_digest_without_summary_says_so(client, db):
    insert_digest(db, title="KEV add")
    assert "Summary unavailable" in client.get("/digest").get_data(as_text=True)


def test_chat_rejects_oversized_input(client):
    assert client.post("/api/chat", json={"messages": [{"role": "user", "content": "x" * 5000}]}).status_code == 400
    assert client.post("/api/chat", json={"messages": [{"role": "user", "content": "q"}] * 21}).status_code == 400
    assert client.post("/api/chat", json={"messages": [{"role": "system", "content": "q"}]}).status_code == 400
    assert client.post("/api/chat", data="nope").status_code == 400


def test_chat_replies(db):
    c = make_client(db, FakeClaudeClient([fake_text("All good.")]))
    assert c.post("/api/chat", json={"messages": [{"role": "user", "content": "status?"}]}).get_json() == {"reply": "All good."}


def test_fix_guide_shown(client, db):
    run_scan(db, [("basics", lambda: CheckResult("basics", [F("basics:firewall", fix=["Open System Settings"])],
                                                  passed=["SIP: on"], skipped=["FileVault: couldn't check (permission)"]))])
    body = client.get("/scan").get_data(as_text=True)
    assert "Open System Settings" in body and "SIP: on" in body and "couldn&#39;t check" in body


def test_status_page_has_history_cells(client):
    body = client.get("/status").get_data(as_text=True)
    assert "Cloudflare DNS" in body and body.count('class="cell no_data"') >= 168
