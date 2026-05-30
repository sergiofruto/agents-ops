import { Suspense } from "react";
import { getPolymarketStats, getDotaStats, getJobs, getPipeline } from "@/lib/queries";
import { getBtc, getStocks, getFearGreed } from "@/lib/market";
import CollapsibleSection from "@/components/CollapsibleSection";
import AgentCard from "@/components/AgentCard";
import MarketSection from "@/components/MarketSection";
import RebrandingChecklist from "@/components/RebrandingChecklist";
import { JobsList } from "@/components/JobsList";
import { FinanceCard } from "@/components/FinanceCard";

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
    getFearGreed().catch(() => ({ value: null, label: "Unknown" })),
  ]);

  return (
    <div className="space-y-4">
      <CollapsibleSection title="Agents">
        <div className="flex flex-col sm:flex-row gap-4">
          <AgentCard name="Polymarket" href="/polymarket" stats={polymarket} icon="📈" />
          <AgentCard name="Dota 2" href="/dota" stats={dota} icon="🎮" />
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Markets">
        <MarketSection btc={btc} stocks={stocks} fearGreed={fearGreed} />
      </CollapsibleSection>

      <CollapsibleSection title="Finance">
        <FinanceCard />
      </CollapsibleSection>

      <CollapsibleSection title="Rebranding Checklist">
        <Suspense fallback={null}>
          <RebrandingChecklist />
        </Suspense>
      </CollapsibleSection>

      <CollapsibleSection title="Job Tracker">
        <JobsList jobs={jobs} pipeline={pipeline} />
      </CollapsibleSection>
    </div>
  );
}
