import json
from datetime import datetime
from types import SimpleNamespace

import feedparser

from digest.sources import Item, extract_cves, fetch_all, item_id
from digest.validate import confirmable, pre_cluster

NOW = datetime(2026, 10, 24, 12, 0)
NO_RSS = lambda url: {"entries": []}  # noqa: E731


def it(kind, url, title="t", text="", kev=False):
    return Item(item_id(url), kind, "s", url, title, NOW, text, extract_cves(title + " " + text), kev)


def fake_get(mapping: dict):
    """requests.get stand-in: the first key found in the URL picks the body."""
    def get(url, params=None, headers=None, timeout=None):
        body = next((v for k, v in mapping.items() if k in url), None)
        if body is None:
            raise ConnectionError(url)
        raw = body.encode() if isinstance(body, str) else body
        return SimpleNamespace(content=raw, status_code=200, json=lambda: json.loads(raw),
                               raise_for_status=lambda: None)
    return get


def test_single_outlet_is_not_confirmable():
    assert confirmable([it("outlet", "https://a.com/1")]) is False


def test_two_outlets_on_different_hosts_confirm():
    assert confirmable([it("outlet", "https://a.com/1"), it("outlet", "https://b.com/2")])
    assert not confirmable([it("outlet", "https://a.com/1"), it("outlet", "https://a.com/2")])


def test_primary_confirms():
    assert confirmable([it("primary", "https://cisa.gov/x")])


def test_extract_cves_normalises():
    assert extract_cves("cve-2026-1234 and CVE-2026-1234, CVE-2025-99999") == ("CVE-2025-99999", "CVE-2026-1234")


def test_pre_cluster_links_by_cve():
    a = it("outlet", "https://a.com/1", "Chrome zero-day CVE-2026-1234")
    b = it("primary", "https://chromereleases.googleblog.com/x", text="fixes cve-2026-1234")
    c = it("outlet", "https://b.com/z", "unrelated")
    clusters = pre_cluster([a, b, c])
    assert sorted(len(x) for x in clusters) == [1, 2]


def test_kev_parse_window_and_seen_items_skipped(db, fixture):
    get = fake_get({"known_exploited": fixture("kev.json"), "nvd.nist.gov": '{"vulnerabilities": []}'})
    items = fetch_all(db, get=get, parse=NO_RSS, now=NOW)
    assert {i.cve_ids for i in items} == {("CVE-2026-1234",), ("CVE-2026-5678",)}
    assert all(i.kind == "primary" and i.kev for i in items)
    db.executemany("INSERT INTO seen_items VALUES (?, ?)", [(i.url, NOW.isoformat()) for i in items])
    db.commit()
    assert fetch_all(db, get=get, parse=NO_RSS, now=NOW) == []


def test_rss_title_filter_and_window(db, fixture):
    feed = feedparser.parse(fixture("rss_sample.xml"))
    sources = [{"name": "Chrome Releases", "kind": "primary", "type": "rss", "url": "chrome",
                "title_filter": "Stable Channel Update"}]
    items = fetch_all(db, get=fake_get({}), parse=lambda url: feed, now=NOW, sources=sources)
    assert [i.url for i in items] == ["https://chromereleases.googleblog.com/2026/10/stable-1.html"]
    assert items[0].cve_ids == ("CVE-2026-1234",) and "<p>" not in items[0].text


def test_failing_source_is_skipped(db, fixture):
    sources = [{"name": "Down", "kind": "outlet", "type": "rss", "url": "x"},
               {"name": "CISA KEV", "kind": "primary", "type": "kev", "url": "known_exploited"}]
    def boom(url):
        raise OSError("offline")
    items = fetch_all(db, get=fake_get({"known_exploited": fixture("kev.json")}), parse=boom, now=NOW, sources=sources)
    assert len(items) == 2


def test_non_http_links_are_dropped(db):
    feed = {"entries": [{"title": "x", "link": "javascript:alert(1)", "summary": "", "published_parsed": NOW.utctimetuple()},
                        {"title": "y", "link": "https://ok.com/a", "summary": "", "published_parsed": NOW.utctimetuple()}]}
    sources = [{"name": "Feed", "kind": "outlet", "type": "rss", "url": "f"}]
    items = fetch_all(db, get=fake_get({}), parse=lambda url: feed, now=NOW, sources=sources)
    assert [i.url for i in items] == ["https://ok.com/a"]
