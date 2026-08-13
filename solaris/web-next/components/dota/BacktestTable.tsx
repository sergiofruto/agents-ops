import { Badge } from "@tremor/react";
import type { BacktestRow } from "@/lib/types";

interface BacktestTableProps {
  rows: BacktestRow[];
}

export default function BacktestTable({ rows }: BacktestTableProps) {
  if (rows.length === 0) {
    return (
      <p className="text-sm text-zinc-500 italic py-4 text-center">
        No backtest history available.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-white/10">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10 bg-white/5">
            <th className="px-4 py-2 text-left text-[11px] uppercase tracking-wide text-zinc-500">Run At</th>
            <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wide text-zinc-500">Days</th>
            <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wide text-zinc-500">Teams</th>
            <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wide text-zinc-500">Matches</th>
            <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wide text-zinc-500">Model Acc</th>
            <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wide text-zinc-500">Elo Acc</th>
            <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wide text-zinc-500">Model Brier</th>
            <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wide text-zinc-500">Elo Brier</th>
            <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wide text-zinc-500">Calib.</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className={`border-b border-white/5 hover:bg-white/[0.03] transition-colors ${
                i === 0 ? "bg-violet-500/5" : ""
              }`}
            >
              <td className="px-4 py-2.5 text-zinc-300 text-xs">
                {row.run_at.slice(0, 16)}
                {i === 0 && (
                  <Badge color="violet" className="ml-2 text-[10px]">
                    latest
                  </Badge>
                )}
              </td>
              <td className="px-4 py-2.5 text-right text-zinc-400">{row.days}</td>
              <td className="px-4 py-2.5 text-right text-zinc-400">{row.n_teams}</td>
              <td className="px-4 py-2.5 text-right text-zinc-400">{row.n_matches}</td>
              <td className="px-4 py-2.5 text-right font-medium text-zinc-200">
                {(row.model_accuracy * 100).toFixed(1)}%
              </td>
              <td className="px-4 py-2.5 text-right font-medium text-zinc-200">
                {(row.elo_accuracy * 100).toFixed(1)}%
              </td>
              <td className="px-4 py-2.5 text-right text-zinc-400">
                {row.model_brier.toFixed(4)}
              </td>
              <td className="px-4 py-2.5 text-right text-zinc-400">
                {row.elo_brier.toFixed(4)}
              </td>
              <td className="px-4 py-2.5 text-right text-zinc-400">
                {row.calibration_factor.toFixed(3)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
