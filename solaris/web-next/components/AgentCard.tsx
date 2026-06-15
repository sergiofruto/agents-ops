"use client";

import Link from "next/link";
import { StatusBadge } from "./StatusBadge";
import type { PolymarketStats, DotaStats } from "@/lib/types";

type AgentStats = PolymarketStats | DotaStats;

interface AgentCardProps {
  name: string;
  href: string;
  stats: AgentStats;
}

function pnlColor(pnl: number | undefined) {
  if (pnl === undefined) return "text-[#f1f5f9]";
  return pnl >= 0 ? "text-[#34d399]" : "text-[#f87171]";
}

function formatPnl(pnl: number | undefined) {
  if (pnl === undefined) return "$0.00";
  return `${pnl >= 0 ? "+" : ""}$${Math.abs(pnl).toFixed(2)}`;
}

export default function AgentCard({ name, href, stats }: AgentCardProps) {
  const mode = !stats.available ? "OFFLINE" : stats.is_live ? "LIVE" : "DRY RUN";

  return (
    <div className="bg-[#0f1a2e] border border-[#1e3a5f] rounded-lg p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-[11.5px] font-medium text-[#60a5fa] tracking-[0.06em] uppercase">
          {name}
        </span>
        <StatusBadge mode={mode} />
      </div>

      {!stats.available ? (
        <p className="text-[11.5px] text-[#475569]">Offline</p>
      ) : (
        <>
          <div>
            <div className={`text-[25px] font-bold leading-none ${pnlColor(stats.pnl)}`}>
              {formatPnl(stats.pnl)}
            </div>
            <div className="text-[11.5px] text-[#475569] mt-1">P&L all time</div>
          </div>

          <div className="flex flex-col">
            {(
              [
                { label: "TOTAL", value: stats.total ?? 0 },
                { label: "OPEN",  value: stats.open  ?? 0 },
                { label: "WIN %", value: `${stats.win_rate ?? 0}%` },
                { label: "ROI",   value: `${stats.roi ?? 0}%` },
              ] as const
            ).map(({ label, value }) => (
              <div
                key={label}
                className="flex justify-between items-center py-[5px] border-b border-[#1e3a5f] last:border-none"
              >
                <span className="text-[11.5px] text-[#475569]">{label}</span>
                <span className="text-[14px] font-medium text-[#f1f5f9]">{value}</span>
              </div>
            ))}
          </div>

          <Link
            href={href}
            className="text-[11.5px] text-[#475569] hover:text-[#f1f5f9] transition-colors tracking-[0.06em]"
          >
            VIEW ALL →
          </Link>
        </>
      )}
    </div>
  );
}
