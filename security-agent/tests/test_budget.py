from datetime import date, timedelta

import pytest

from analyst import Claude
from budget import Budget, cost_usd
from fakes import FakeClaudeClient, fake_text

D = date(2026, 10, 24)


def _spend(db, job, cost, day=D):
    db.execute("INSERT INTO ai_usage VALUES (?,?,?,?,?,?)", (day.isoformat(), job, "m", 0, 0, cost))
    db.commit()


def test_cost_uses_per_million_prices():
    assert cost_usd("claude-haiku-5-5", 1_000_000, 1_000_000) == pytest.approx(0.60)


def test_reserve_protects_digest(db):
    b = Budget(db, cap=1.0, reserve=0.33)
    _spend(db, "chat", 0.67)
    assert b.can_spend("chat", D) is False and b.can_spend("digest", D) is True


def test_reserve_released_after_digest(db):
    b = Budget(db, cap=1.0, reserve=0.33)
    _spend(db, "digest", 0.10)
    _spend(db, "chat", 0.60)
    assert b.can_spend("chat", D) is True
    _spend(db, "chat", 0.31)
    assert b.can_spend("chat", D) is False


def test_digest_stops_at_cap(db):
    _spend(db, "digest", 1.0)
    assert Budget(db, cap=1.0, reserve=0.33).can_spend("digest", D) is False


def test_new_day_resets(db):
    _spend(db, "chat", 5.0)
    assert Budget(db).can_spend("chat", D + timedelta(days=1))


def test_claude_records_usage_and_denies_without_client(db):
    fake = FakeClaudeClient([fake_text("hi", input_tokens=1000, output_tokens=200)])
    c = Claude(fake, Budget(db), today=lambda: D)
    assert c.ask("chat", model="claude-haiku-5-5", system="s", messages=[{"role": "user", "content": "q"}]) is not None
    assert Budget(db).spent_today(D) == pytest.approx(cost_usd("claude-haiku-5-5", 1000, 200))
    assert Claude(None, Budget(db)).ask("chat", model="m", system="s", messages=[]) is None


def test_claude_denied_over_budget_makes_no_call(db):
    _spend(db, "chat", 0.9)
    fake = FakeClaudeClient([])
    assert Claude(fake, Budget(db), today=lambda: D).ask("chat", model="claude-haiku-5-5", system="s", messages=[]) is None
    assert fake.calls == []
