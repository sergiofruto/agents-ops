import type { TeamRanking } from "@/lib/types";

interface EloTableProps {
  rankings: TeamRanking[];
  available: boolean;
}

export default function EloTable({ rankings, available }: EloTableProps) {
  if (!available || rankings.length === 0) {
    return (
      <div className="rounded-lg bg-white/5 border border-white/10 px-4 py-6 text-center">
        <p className="text-sm text-zinc-500 italic">
          Elo rankings unavailable. Start the Dota agent to populate team data.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-white/10">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10 bg-white/5">
            <th className="px-4 py-2 text-left text-[11px] uppercase tracking-wide text-zinc-500">#</th>
            <th className="px-4 py-2 text-left text-[11px] uppercase tracking-wide text-zinc-500">Team</th>
            <th className="px-4 py-2 text-right text-[11px] uppercase tracking-wide text-zinc-500">Elo Rating</th>
          </tr>
        </thead>
        <tbody>
          {rankings.map((team, i) => (
            <tr
              key={team.name}
              className="border-b border-white/5 hover:bg-white/[0.03] transition-colors"
            >
              <td className="px-4 py-2.5 text-zinc-500 text-xs">{i + 1}</td>
              <td className="px-4 py-2.5 font-medium text-zinc-200">{team.name}</td>
              <td className="px-4 py-2.5 text-right">
                <span
                  className={`font-mono text-sm font-semibold ${
                    i < 3
                      ? "text-amber-300"
                      : i < 10
                      ? "text-zinc-200"
                      : "text-zinc-400"
                  }`}
                >
                  {Math.round(team.elo)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
