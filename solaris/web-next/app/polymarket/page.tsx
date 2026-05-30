import Link from "next/link";
import { getPolymarketStats, getPolymarketBets } from "@/lib/queries";
import CollapsibleSection from "@/components/CollapsibleSection";
import BetsTable from "@/components/polymarket/BetsTable";

export const metadata = {
  title: "Polymarket — Solaris",
};

function Chip({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-md bg-white/5 px-3 py-2 min-w-[64px]">
      <span className="text-[10px] uppercase tracking-wide text-zinc-500">{label}</span>
      <span className="mt-0.5 text-sm font-semibold text-zinc-100">{value}</span>
    </div>
  );
}

export default async function PolymarketPage() {
  const [stats, bets] = await Promise.all([
    getPolymarketStats().catch(() => ({ available: false } as const)),
    getPolymarketBets().catch(() => []),
  ]);

  return (
    <div className="space-y-4">
      <nav className="flex items-center gap-2 text-sm text-zinc-500">
        <Link href="/" className="hover:text-zinc-200 transition-colors">← Dashboard</Link>
        <span>/</span>
        <span className="text-zinc-300">Polymarket</span>
      </nav>

      <h1 className="text-xl font-semibold text-zinc-100">📈 Polymarket Bets</h1>

      {stats.available && (
        <div className="flex flex-wrap gap-2">
          <Chip label="Total" value={stats.total ?? 0} />
          <Chip label="Open" value={stats.open ?? 0} />
          <Chip label="Won" value={stats.won ?? 0} />
          <Chip label="Lost" value={stats.lost ?? 0} />
          <Chip label="Win %" value={`${stats.win_rate ?? 0}%`} />
          <Chip
            label="P&L"
            value={
              <span className={(stats.pnl ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}>
                ${stats.pnl?.toFixed(2) ?? "0.00"}
              </span>
            }
          />
          <Chip label="ROI" value={`${stats.roi ?? 0}%`} />
          <Chip label="Mode" value={stats.is_live ? "LIVE" : "DRY RUN"} />
        </div>
      )}

      <CollapsibleSection title={`All Bets (${bets.length})`}>
        <BetsTable bets={bets} />
      </CollapsibleSection>
    </div>
  );
}
