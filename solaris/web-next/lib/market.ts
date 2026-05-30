import type { BtcData, StockItem, FearGreed } from "./types";

const REVALIDATE = 300; // 5 min

export async function getBtc(): Promise<BtcData> {
  try {
    const r = await fetch(
      "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
      { next: { revalidate: REVALIDATE } });
    const d = (await r.json()).bitcoin;
    let sparkline: number[] = [];
    try {
      const r2 = await fetch(
        "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=7&interval=daily",
        { next: { revalidate: REVALIDATE } });
      sparkline = ((await r2.json()).prices ?? []).slice(-7).map((p: number[]) => Math.round(p[1]));
    } catch {}
    return { price: d.usd, change_24h: Math.round((d.usd_24h_change ?? 0) * 100) / 100, sparkline };
  } catch {
    return { price: null, change_24h: null, sparkline: [] };
  }
}

export async function getFearGreed(): Promise<FearGreed> {
  try {
    const r = await fetch("https://api.alternative.me/fng/", { next: { revalidate: REVALIDATE } });
    const item = (await r.json()).data[0];
    return { value: parseInt(item.value, 10), label: item.value_classification };
  } catch {
    return { value: null, label: "Unknown" };
  }
}

// yfinance has no public JSON API; use Yahoo's quote endpoint for the watchlist.
export async function getStocks(tickers = ["SPY", "QQQ", "NVDA"]): Promise<StockItem[]> {
  try {
    const r = await fetch(
      `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${tickers.join(",")}`,
      { next: { revalidate: REVALIDATE }, headers: { "User-Agent": "Mozilla/5.0" } });
    const result = (await r.json()).quoteResponse?.result ?? [];
    return tickers.map(t => {
      const q = result.find((x: { symbol: string }) => x.symbol === t);
      return {
        ticker: t,
        price: q?.regularMarketPrice != null ? Math.round(q.regularMarketPrice * 100) / 100 : null,
        change_pct: q?.regularMarketChangePercent != null ? Math.round(q.regularMarketChangePercent * 100) / 100 : null,
      };
    });
  } catch {
    return tickers.map(t => ({ ticker: t, price: null, change_pct: null }));
  }
}
