import Link from "next/link";
import { getDotaStats, getDotaBets, getDotaAnalytics } from "@/lib/queries";
import { Section } from "@/components/Section";
import BetsTable from "@/components/dota/BetsTable";
import BacktestTable from "@/components/dota/BacktestTable";
import EloTable from "@/components/dota/EloTable";

export const metadata = {
  title: "Dota 2 — Solaris",
};

function Chip({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-md bg-white/5 px-3 py-2 min-w-[64px]">
      <span className="text-[10px] uppercase tracking-wide text-zinc-500">{label}</span>
      <span className="mt-0.5 text-sm font-semibold text-zinc-100">{value}</span>
    </div>
  );
}

export default async function DotaPage() {
  const [stats, bets, analytics] = await Promise.all([
    getDotaStats().catch(() => ({ available: false } as const)),
    getDotaBets().catch(() => []),
    getDotaAnalytics().catch(() => ({
      backtest_history: [],
      team_rankings: [],
      roster_available: false,
    })),
  ]);

  return (
    <div className="space-y-4">
      <nav className="flex items-center gap-2 text-sm text-zinc-500">
        <Link href="/" className="hover:text-zinc-200 transition-colors">← Dashboard</Link>
        <span>/</span>
        <span className="text-zinc-300">Dota 2</span>
      </nav>

      <h1 className="text-xl font-semibold text-zinc-100">🎮 Dota 2 Bets</h1>

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
          {stats.model_accuracy != null && <Chip label="Model Acc" value={`${stats.model_accuracy}%`} />}
          {stats.elo_accuracy != null && <Chip label="Elo Acc" value={`${stats.elo_accuracy}%`} />}
        </div>
      )}

      <Section title={`Bet History (${bets.length})`}>
        <BetsTable bets={bets} />
      </Section>

      <Section title="Backtest History">
        <BacktestTable rows={analytics.backtest_history} />
      </Section>

      <Section title="Team Elo Rankings">
        <EloTable rankings={analytics.team_rankings} available={analytics.roster_available} />
      </Section>
    </div>
  );
}
