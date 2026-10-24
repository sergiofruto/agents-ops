"""What we see from this Mac: does the API host answer, does DNS resolve."""
import time

import requests


def probe_https(url: str, get=requests.get) -> tuple[bool, int | None]:
    start = time.monotonic()
    try:
        resp = get(url, timeout=5, allow_redirects=False)
    except Exception:
        return False, None
    ms = int((time.monotonic() - start) * 1000)
    return resp.status_code < 500, ms


def probe_dns(ip: str, resolve=None) -> tuple[bool, int | None]:
    start = time.monotonic()
    try:
        if resolve is None:
            import dns.resolver
            r = dns.resolver.Resolver(configure=False)
            r.nameservers = [ip]
            r.lifetime = 3
            r.resolve("example.com", "A")
        else:
            resolve(ip)
    except Exception:
        return False, None
    return True, int((time.monotonic() - start) * 1000)
