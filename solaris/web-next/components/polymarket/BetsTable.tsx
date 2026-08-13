import { StatusBadge } from "@/components/StatusBadge";
import type { PolymarketBet } from "@/lib/types";

interface BetsTableProps {
  bets: PolymarketBet[];
}

export default function BetsTable({ bets }: BetsTableProps) {
  if (bets.length === 0) {
    return (
      <p className="text-sm text-zinc-500 italic py-4 text-center">No bets found.</p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-white/10">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10 bg-white/5">
            <th className="px-4 py-2 text-left text-[11px] uppercase tracking-wide text-zinc-500">Question</th>
            <th className="px-4 py-2 text-left text-[11px] uppercase tracking-wide text-zinc-500">Outcome</th>
            <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wide text-zinc-500">Price</th>
            <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wide text-zinc-500">Stake</th>
            <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wide text-zinc-500">Edge</th>
            <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wide text-zinc-500">Payout</th>
            <th className="px-4 py-2 text-center text-[11px] uppercase tracking-wide text-zinc-500">Status</th>
            <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wide text-zinc-500">Date</th>
          </tr>
        </thead>
        <tbody>
          {bets.map((bet) => (
            <tr key={bet.id} className="border-b border-white/5 hover:bg-white/[0.03] transition-colors">
              <td className="px-4 py-2.5 max-w-[240px]">
                <span
                  className="block truncate text-zinc-200"
                  title={bet.question}
                >
                  {bet.question.length > 60
                    ? bet.question.slice(0, 60) + "…"
                    : bet.question}
                </span>
              </td>
              <td className="px-4 py-2.5 text-zinc-300">{bet.outcome}</td>
              <td className="px-4 py-2.5 text-right text-zinc-300">
                {(bet.price_at_bet * 100).toFixed(0)}¢
              </td>
              <td className="px-4 py-2.5 text-right text-zinc-300">
                ${bet.virtual_amount.toFixed(2)}
              </td>
              <td className="px-4 py-2.5 text-right">
                <span
                  className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                    bet.edge >= 0.05
                      ? "bg-emerald-500/20 text-emerald-300"
                      : bet.edge >= 0.02
                      ? "bg-yellow-500/20 text-yellow-300"
                      : "bg-zinc-500/20 text-zinc-400"
                  }`}
                >
                  {(bet.edge * 100).toFixed(1)}%
                </span>
              </td>
              <td className="px-4 py-2.5 text-right text-zinc-300">
                ${bet.potential_payout.toFixed(2)}
              </td>
              <td className="px-4 py-2.5 text-center">
                <StatusBadge status={bet.status} />
              </td>
              <td className="px-4 py-2.5 text-right text-xs text-zinc-500">
                {bet.timestamp.slice(0, 10)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
