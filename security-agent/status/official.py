"""What each provider says about itself, from its machine-readable status feed."""
import json
from datetime import datetime, timedelta
from typing import Literal

import requests

State = Literal["up", "degraded", "down", "unknown", "no_data"]
AWS_FRESH = timedelta(hours=48)


def parse_statuspage(summary: dict) -> tuple[State, str | None]:
    # Statuspage: "major" is a partial outage (often a few edge locations), "critical" is a full one
    status = summary.get("status", {})
    indicator = status.get("indicator", "")
    state = {"none": "up", "minor": "degraded", "maintenance": "degraded",
             "major": "degraded", "critical": "down"}.get(indicator, "unknown")
    open_incidents = [i for i in summary.get("incidents", []) if i.get("status") not in ("resolved", "postmortem")]
    if open_incidents:
        return state, open_incidents[0]["name"]
    return state, (status.get("description") if state != "up" else None)


def parse_betterstack(data: dict) -> tuple[State, str | None]:
    agg = data.get("data", {}).get("attributes", {}).get("aggregate_state", "")
    return {"operational": "up", "degraded": "degraded", "maintenance": "degraded",
            "downtime": "down"}.get(agg, "unknown"), None


def parse_statusio(data: dict) -> tuple[State, str | None]:
    result = data.get("result", {})
    code = result.get("status_overall", {}).get("status_code")
    state = "up" if code == 100 else "degraded" if code in (200, 300, 400) else "down" if code in (500, 600) else "unknown"
    incidents = result.get("incidents") or []
    return state, (incidents[0].get("name") if incidents else None)


def parse_aws(events: list, now: datetime) -> tuple[State, str | None]:
    """AWS keeps some regional events open for months; only recently updated ones count."""
    fresh = []
    for e in events:
        stamps = [int(l.get("timestamp", 0)) for l in e.get("event_log", [])] + [int(e.get("date", 0) or 0)]
        last = datetime.fromtimestamp(max(stamps))
        if now - last <= AWS_FRESH:
            fresh.append((last, e))
    if not fresh:
        return "up", None
    _, e = max(fresh, key=lambda x: x[0])
    return "degraded", f"{e.get('service_name', 'AWS')} ({e.get('region_name', '?')}): {e.get('summary', '')}".strip()


def _json(resp) -> object:
    raw = resp.content
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
    return json.loads(text)


def fetch_official(provider: dict, get=requests.get, now: datetime | None = None) -> tuple[State, str | None]:
    official = provider.get("official")
    if not official:
        return "unknown", None
    kind, url = official
    try:
        resp = get(url, timeout=10)
        resp.raise_for_status()
        data = _json(resp)
        if kind == "statuspage":
            return parse_statuspage(data)
        if kind == "betterstack":
            return parse_betterstack(data)
        if kind == "statusio":
            return parse_statusio(data)
        if kind == "aws":
            return parse_aws(data, now or datetime.now())
    except Exception:
        pass
    return "unknown", None
