import time
import requests
import config

_cache: dict = {}


def _get(key: str):
    entry = _cache.get(key)
    if entry and time.time() - entry[1] < config.CACHE_TTL:
        return entry[0]
    return None


def _set(key: str, data):
    _cache[key] = (data, time.time())
    return data


def get_btc() -> dict:
    cached = _get("btc")
    if cached:
        return cached

    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd",
                    "include_24hr_change": "true"},
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()["bitcoin"]
        price = d["usd"]
        change_24h = round(d.get("usd_24h_change", 0), 2)
    except Exception:
        price = None
        change_24h = None

    sparkline = []
    try:
        r2 = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
            params={"vs_currency": "usd", "days": "7", "interval": "daily"},
            timeout=10,
        )
        r2.raise_for_status()
        prices = r2.json().get("prices", [])
        # one point per day (last 7)
        sparkline = [round(p[1], 0) for p in prices[-7:]]
    except Exception:
        pass

    data = {"price": price, "change_24h": change_24h, "sparkline": sparkline}
    return _set("btc", data)


def get_stocks() -> list:
    cached = _get("stocks")
    if cached:
        return cached

    results = []
    try:
        import yfinance as yf
        tickers = config.STOCK_WATCHLIST
        data = yf.download(
            tickers, period="2d", interval="1d",
            group_by="ticker", auto_adjust=True, progress=False, threads=True,
        )
        for t in tickers:
            try:
                if len(tickers) == 1:
                    closes = data["Close"].dropna()
                else:
                    closes = data[t]["Close"].dropna()
                if len(closes) >= 2:
                    prev, curr = float(closes.iloc[-2]), float(closes.iloc[-1])
                    chg = round((curr - prev) / prev * 100, 2)
                else:
                    curr = float(closes.iloc[-1]) if len(closes) else None
                    chg = None
                results.append({"ticker": t, "price": round(curr, 2) if curr else None, "change_pct": chg})
            except Exception:
                results.append({"ticker": t, "price": None, "change_pct": None})
    except Exception:
        for t in config.STOCK_WATCHLIST:
            results.append({"ticker": t, "price": None, "change_pct": None})

    return _set("stocks", results)


def get_fear_greed() -> dict:
    cached = _get("fng")
    if cached:
        return cached

    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=10)
        r.raise_for_status()
        item = r.json()["data"][0]
        value = int(item["value"])
        label = item["value_classification"]
        data = {"value": value, "label": label}
    except Exception:
        data = {"value": None, "label": "Unknown"}

    return _set("fng", data)
