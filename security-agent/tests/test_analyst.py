import json
from datetime import date
from types import SimpleNamespace

from analyst import NO_BUDGET, NO_KEY, Claude, chat, run_tool, scan_overview
from budget import Budget
from checks.secrets import scan_secrets
from conftest import PLANTED, F
from fakes import FakeClaudeClient, fake_text, tool_use
from models import CheckResult
from scan import run_scan


def claude_text(db, text):
    return Claude(FakeClaudeClient([fake_text(text)]), Budget(db))


def test_overview_strips_unknown_keys(db):
    sid = run_scan(db, [("ports", lambda: CheckResult("ports", [F("port:5000:Python")]))])
    text = scan_overview(db, claude_text(db, "Fix [port:5000:Python] first, then [made:up]."), sid)
    assert "[port:5000:Python]" in text and "made:up" not in text
    assert db.execute("SELECT overview FROM scans WHERE id=?", (sid,)).fetchone()[0] == text


def test_overview_without_claude_is_none(db):
    sid = run_scan(db, [])
    assert scan_overview(db, Claude(None, Budget(db)), sid) is None


def test_chat_runs_tool_and_answers(db):
    fake = FakeClaudeClient([tool_use("get_status", {}), fake_text("All providers are up.")])
    assert chat(db, Claude(fake, Budget(db)), [{"role": "user", "content": "anything down?"}]) == "All providers are up."
    assert fake.calls[1]["messages"][-1]["content"][0]["type"] == "tool_result"
    assert all(t["name"] in {"lookup_cve", "get_scan", "get_digest", "get_status"} for t in fake.calls[0]["tools"])


def test_unknown_tool_and_bad_cve_are_errors(db):
    assert run_tool(db, "rm_rf", {}) == {"error": "unknown tool"}
    assert "error" in run_tool(db, "lookup_cve", {"cve_id": "not-a-cve"})


def test_lookup_cve_uses_nvd_and_kev(db):
    nvd = {"vulnerabilities": [{"cve": {"id": "CVE-2026-1234", "published": "2026-10-20T00:00:00",
                                        "descriptions": [{"lang": "en", "value": "Type confusion"}],
                                        "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 8.8}}]}}}]}
    kev = {"vulnerabilities": [{"cveID": "CVE-2026-1234"}]}
    def get(url, params=None, timeout=None, headers=None):
        body = nvd if "nvd" in url else kev
        return SimpleNamespace(json=lambda: body, raise_for_status=lambda: None)
    out = run_tool(db, "lookup_cve", {"cve_id": "cve-2026-1234"}, get=get)
    assert out == {"cve_id": "CVE-2026-1234", "description": "Type confusion", "cvss": 8.8,
                   "published": "2026-10-20T00:00:00", "actively_exploited_kev": True}


def test_chat_when_budget_spent(db):
    db.execute("INSERT INTO ai_usage VALUES (?,?,?,?,?,?)", (date.today().isoformat(), "chat", "m", 0, 0, 9))
    db.commit()
    assert chat(db, Claude(FakeClaudeClient([]), Budget(db)), [{"role": "user", "content": "q"}]) == NO_BUDGET


def test_chat_without_key(db):
    assert chat(db, Claude(None, Budget(db)), [{"role": "user", "content": "q"}]) == NO_KEY


def test_chat_stops_after_five_tool_rounds(db):
    fake = FakeClaudeClient([tool_use("get_status", {}, id=f"t{i}") for i in range(5)])
    reply = chat(db, Claude(fake, Budget(db)), [{"role": "user", "content": "loop"}])
    assert len(fake.calls) == 5 and "couldn't finish" in reply


def test_no_secret_reaches_claude(db, tmp_path, git_repo):
    (git_repo / ".env").write_text(f"POLY_PRIVATE_KEY={PLANTED}\n")
    (git_repo / ".env").chmod(0o600)
    sid = run_scan(db, [("secrets", lambda: scan_secrets(tmp_path / "Projects", home=tmp_path))])
    fake = FakeClaudeClient([fake_text("ok"), tool_use("get_scan", {}), fake_text("ok")])
    c = Claude(fake, Budget(db))
    scan_overview(db, c, sid)
    chat(db, c, [{"role": "user", "content": "what did you find?"}])
    sent = json.dumps(fake.calls, default=str)
    assert "secrets:" in sent  # the finding itself did reach Claude
    assert PLANTED not in sent and "ab" * 32 not in sent
    assert PLANTED not in "\n".join(str(tuple(r)) for r in db.execute("SELECT * FROM findings"))


def test_chat_api_failure_is_not_reported_as_budget(db):
    class Down:
        messages = None
        def __init__(self):
            self.messages = self
        def create(self, **kw):
            raise ConnectionError("down")
    reply = chat(db, Claude(Down(), Budget(db)), [{"role": "user", "content": "q"}])
    assert reply != NO_BUDGET and "couldn't reach" in reply
