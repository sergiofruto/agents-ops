import json
from datetime import datetime, timedelta

import pytest

import config
from status.official import parse_aws, parse_betterstack, parse_statusio, parse_statuspage
from status.service import check_all, combine, current, history

NOW = datetime(2026, 10, 24, 12, 0)


def test_parse_statuspage(fixture):
    assert parse_statuspage(json.loads(fixture("statuspage_ok.json"))) == ("up", None)
    state, inc = parse_statuspage(json.loads(fixture("statuspage_minor.json")))
    assert state == "degraded" and inc == "Incident with Actions"


def test_parse_betterstack_and_statusio():
    assert parse_betterstack({"data": {"attributes": {"aggregate_state": "operational"}}}) == ("up", None)
    assert parse_betterstack({"data": {"attributes": {"aggregate_state": "downtime"}}})[0] == "down"
    ok = {"result": {"status_overall": {"status_code": 100}, "incidents": []}}
    bad = {"result": {"status_overall": {"status_code": 500}, "incidents": [{"name": "API outage"}]}}
    assert parse_statusio(ok) == ("up", None) and parse_statusio(bad) == ("down", "API outage")


def test_parse_aws_ignores_stale_regional_events():
    stale = {"region_name": "UAE", "service_name": "Multiple services", "summary": "x",
             "event_log": [{"timestamp": str(int((NOW - timedelta(days=30)).timestamp()))}]}
    fresh = {"region_name": "N. Virginia", "service_name": "Amazon EC2", "summary": "Increased error rates",
             "event_log": [{"timestamp": str(int((NOW - timedelta(hours=2)).timestamp()))}]}
    assert parse_aws([stale], NOW) == ("up", None)
    state, inc = parse_aws([stale, fresh], NOW)
    assert state == "degraded" and "Amazon EC2" in inc and "N. Virginia" in inc


@pytest.mark.parametrize("official,probe,expected", [
    ("down", True, "down"), ("degraded", True, "degraded"), ("up", False, "degraded"),
    ("unknown", False, "down"), ("unknown", True, "up"), ("up", True, "up")])
def test_combine(official, probe, expected):
    assert combine(official, probe)[0] == expected


def test_up_but_probe_failed_explains():
    assert combine("up", False) == ("degraded", "Provider says up, but our check failed")


def test_check_all_stores_every_service(db):
    rows = check_all(db, fetch=lambda p: ("up", None), https=lambda u: (True, 50), dns=lambda ip: (True, 10), now=NOW)
    assert len(rows) == len(config.PROVIDERS) + len(config.DNS_RESOLVERS) == 10
    assert {r["state"] for r in rows} == {"up"}
    assert [r["service"] for r in current(db)] == [r["service"] for r in rows]


def test_all_probes_failing_records_offline_not_outage(db):
    rows = check_all(db, fetch=lambda p: ("unknown", None), https=lambda u: (False, None),
                     dns=lambda ip: (False, None), now=NOW)
    assert {r["state"] for r in rows} == {"no_data"} and len(rows) == 10


def test_one_dns_down_is_down(db):
    rows = check_all(db, fetch=lambda p: ("up", None), https=lambda u: (True, 5),
                     dns=lambda ip: (ip != "9.9.9.9", None), now=NOW)
    assert {r["service"]: r["state"] for r in rows}["dns-quad9"] == "down"


def test_history_marks_gaps_no_data(db):
    db.execute("INSERT INTO status_checks VALUES ('github', ?, 'down', 'down', 0, NULL, 'x')",
               ((NOW - timedelta(minutes=30)).isoformat(),))
    h = history(db, "github", NOW, days=1)
    assert len(h) == 24 and h[-1]["state"] == "down" and h[0]["state"] == "no_data"


def test_history_keeps_worst_state_in_bucket(db):
    for minutes, state in [(50, "up"), (40, "degraded"), (10, "up")]:
        db.execute("INSERT INTO status_checks VALUES ('github', ?, ?, ?, 1, 5, NULL)",
                   ((NOW - timedelta(minutes=minutes)).isoformat(), state, state))
    assert history(db, "github", NOW, days=1)[-1]["state"] == "degraded"


def test_old_rows_pruned(db):
    db.execute("INSERT INTO status_checks VALUES ('github', ?, 'up', 'up', 1, 5, NULL)",
               ((NOW - timedelta(days=9)).isoformat(),))
    check_all(db, fetch=lambda p: ("up", None), https=lambda u: (True, 5), dns=lambda ip: (True, 5), now=NOW)
    assert db.execute("SELECT COUNT(*) FROM status_checks WHERE checked_at < ?",
                      ((NOW - timedelta(days=8)).isoformat(),)).fetchone()[0] == 0


def test_statuspage_major_is_partial_outage_not_down():
    page = {"status": {"indicator": "major", "description": "Partial System Outage"}, "incidents": []}
    assert parse_statuspage(page) == ("degraded", "Partial System Outage")
    assert parse_statuspage({"status": {"indicator": "critical", "description": "Major System Outage"}, "incidents": []})[0] == "down"
