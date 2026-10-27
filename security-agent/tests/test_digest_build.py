import json
from datetime import datetime

from analyst import Claude
from budget import Budget
from conftest import fake_run
from digest.build import build_digest, latest_digest
from digest.inventory import affects, collect_inventory
from fakes import FakeClaudeClient, fake_text
from test_digest_validate import it

NOW = datetime(2026, 10, 24, 12, 0)


def claude_returning_text(db, text):
    return Claude(FakeClaudeClient([fake_text(text)]), Budget(db), today=lambda: NOW.date())


def claude_returning(db, reply: dict):
    return claude_returning_text(db, json.dumps(reply))


def test_affects_matches_whole_words_and_aliases():
    terms = {"next.js", "chrome", "aws"}
    assert affects("Next.js middleware bypass", terms) == ["next.js"]
    assert affects("next week chrome update", terms) == ["chrome"]
    assert affects("chromecast and awsome", terms) == []


def test_collect_inventory(tmp_path):
    proj = tmp_path / "Projects" / "app"
    proj.mkdir(parents=True)
    (proj / "package.json").write_text(json.dumps({"dependencies": {"next": "16", "react": "19"}, "devDependencies": {"vitest": "3"}}))
    (proj / "requirements.txt").write_text("flask>=3.0\nrich==13\n# comment\nfeedparser\n")
    nm = proj / "node_modules" / "x"
    nm.mkdir(parents=True)
    (nm / "package.json").write_text(json.dumps({"dependencies": {"leftpad": "1"}}))
    apps = tmp_path / "Applications"
    (apps / "Google Chrome.app").mkdir(parents=True)
    terms = collect_inventory(tmp_path / "Projects", apps_dir=apps, run=fake_run({"sw_vers": "26.0.1\n"}))
    assert {"next.js", "react", "vitest", "flask", "feedparser", "google chrome", "chrome", "macos", "aws", "cloudflare"} <= terms
    assert "rich" not in terms and "leftpad" not in terms


def test_unconfirmed_single_outlet_dropped_even_if_claude_keeps_it(db):
    a = it("outlet", "https://a.com/1", "Rumor")
    p = it("primary", "https://msrc.microsoft.com/x", "Patch")
    reply = {"groups": [{"item_ids": [a.id], "title": "Rumor", "summary": "s", "who": "w", "action": "a"},
                        {"item_ids": [p.id], "title": "Patch", "summary": "s", "who": "w", "action": "a"}]}
    build_digest(db, [a, p], claude_returning(db, reply), set(), now=NOW)
    assert [e["title"] for e in latest_digest(db)["entries"]] == ["Patch"]


def test_two_outlets_merged_by_claude_confirm(db):
    a = it("outlet", "https://a.com/1", "Breach at X")
    b = it("outlet", "https://b.com/2", "X confirms breach")
    reply = {"groups": [{"item_ids": [a.id, b.id], "title": "X breach", "summary": "s", "who": "w", "action": "a"}]}
    build_digest(db, [a, b], claude_returning(db, reply), set(), now=NOW)
    e = latest_digest(db)["entries"][0]
    assert e["title"] == "X breach" and len(e["sources"]) == 2


def test_unknown_ids_dropped_and_sources_rebuilt(db):
    p = it("primary", "https://cisa.gov/x", "KEV add")
    reply = {"groups": [{"item_ids": [p.id, "deadbeef0000"], "title": "T", "summary": "s", "who": "w", "action": "a"}]}
    build_digest(db, [p], claude_returning(db, reply), set(), now=NOW)
    e = latest_digest(db)["entries"][0]
    assert [s["url"] for s in e["sources"]] == ["https://cisa.gov/x"]


def test_item_used_once_and_leftovers_kept(db):
    p = it("primary", "https://cisa.gov/x", "KEV add")
    q = it("primary", "https://cisa.gov/y", "Other")
    reply = {"groups": [{"item_ids": [p.id], "title": "A", "summary": "s", "who": "w", "action": "a"},
                        {"item_ids": [p.id], "title": "B", "summary": "s", "who": "w", "action": "a"}]}
    build_digest(db, [p, q], claude_returning(db, reply), set(), now=NOW)
    assert sorted(e["title"] for e in latest_digest(db)["entries"]) == ["A", "Other"]


def test_malformed_claude_output_falls_back(db):
    p = it("primary", "https://cisa.gov/x", "KEV add")
    build_digest(db, [p], claude_returning_text(db, "not json"), set(), now=NOW)
    d = latest_digest(db)
    assert d["used_ai"] == 0 and d["entries"][0]["title"] == "KEV add" and d["entries"][0]["summary"] is None


def test_affects_you_sorted_first_and_seen_recorded(db):
    x = it("primary", "https://a.gov/1", "Windows bug")
    y = it("primary", "https://a.gov/2", "Chrome bug")
    build_digest(db, [x, y], None, {"chrome"}, now=NOW)
    entries = latest_digest(db)["entries"]
    assert entries[0]["title"] == "Chrome bug" and entries[0]["affects"] == ["chrome"]
    assert db.execute("SELECT COUNT(*) FROM seen_items").fetchone()[0] == 2


def test_affects_ignores_claude_text(db):
    p = it("primary", "https://a.gov/1", "Windows bug")
    reply = {"groups": [{"item_ids": [p.id], "title": "Chrome users at risk", "summary": "chrome", "who": "w", "action": "a"}]}
    build_digest(db, [p], claude_returning(db, reply), {"chrome"}, now=NOW)
    assert latest_digest(db)["entries"][0]["affects"] == []


def test_no_digest_yet(db):
    assert latest_digest(db) is None


def test_inventory_drops_common_words_and_junk(tmp_path):
    apps = tmp_path / "Applications"
    for a in ("Microsoft Edge", "Google Drive", ".Hidden App", "Cursor"):
        (apps / f"{a}.app").mkdir(parents=True)
    proj = tmp_path / "Projects" / "p"
    proj.mkdir(parents=True)
    (proj / "requirements.txt").write_text("black\ngit+https://github.com/x/y.git\n")
    terms = collect_inventory(tmp_path / "Projects", apps_dir=apps, run=fake_run({}))
    assert "microsoft edge" in terms and "google drive" in terms
    assert not {"edge", "drive", "black", "cursor", ".hidden app"} & terms
    assert not any(t.startswith("git+") for t in terms)
