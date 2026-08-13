import { Suspense } from "react";
import { getPolymarketStats, getDotaStats, getJobs, getPipeline } from "@/lib/queries";
import { getBtc, getStocks, getFearGreed } from "@/lib/market";
import AgentCard from "@/components/AgentCard";
import BtcCard from "@/components/BtcCard";
import FearGreedCard from "@/components/FearGreedCard";
import { JobsList } from "@/components/JobsList";
import { FinanceCard } from "@/components/FinanceCard";
import RebrandingChecklist from "@/components/RebrandingChecklist";
import type { StockItem } from "@/lib/types";

function StocksStrip({ stocks }: { stocks: StockItem[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {stocks.map((s) => {
        const isPositive = (s.change_pct ?? 0) >= 0;
        const chgColor = s.change_pct == null
          ? "text-[#475569]"
          : isPositive ? "text-[#34d399]" : "text-[#f87171]";
        return (
          <div
            key={s.ticker}
            className="bg-[#0f1a2e] border border-[#1e3a5f] rounded-lg px-3 py-2 min-w-[80px]"
          >
            <div className="text-[11.5px] font-medium text-[#60a5fa]">{s.ticker}</div>
            <div className="text-[14px] font-semibold text-[#f1f5f9] mt-0.5">
              {s.price != null ? `$${s.price.toFixed(2)}` : "—"}
            </div>
            <div className={`text-[11.5px] ${chgColor}`}>
              {s.change_pct != null
                ? `${isPositive ? "+" : ""}${s.change_pct}%`
                : "—"}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default async function DashboardPage() {
  const [polymarket, dota, jobs, pipeline, btc, stocks, fearGreed] = await Promise.all([
    getPolymarketStats().catch(() => ({ available: false } as const)),
    getDotaStats().catch(() => ({ available: false } as const)),
    getJobs().catch(() => []),
    getPipeline().catch(() => ({
      bookmarked: 0, applied: 0, phone: 0, technical: 0, final: 0, offer: 0, rejected: 0,
    })),
    getBtc().catch(() => ({ price: null, change_24h: null, sparkline: [] })),
    getStocks().catch(() => []),
    getFearGreed().catch(() => ({ value: null, label: "Unknown", history: [] })),
  ]);

  return (
    <div className="flex flex-col gap-6">
      {/* 2×2 KPI grid */}
      <div className="grid grid-cols-2 gap-4">
        <AgentCard name="Polymarket" href="/polymarket" stats={polymarket} />
        <BtcCard btc={btc} />
        <AgentCard name="Dota 2" href="/dota" stats={dota} />
        <FearGreedCard fearGreed={fearGreed} />
      </div>

      {/* Stocks strip */}
      {stocks.length > 0 && <StocksStrip stocks={stocks} />}

      {/* Full-width sections */}
      <JobsList jobs={jobs} pipeline={pipeline} />
      <FinanceCard />
      <Suspense fallback={null}>
        <RebrandingChecklist />
      </Suspense>
    </div>
  );
}
