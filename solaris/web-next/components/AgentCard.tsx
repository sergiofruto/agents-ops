import Link from "next/link";
import type { PolymarketStats, DotaStats } from "@/lib/types";

type AgentStats = PolymarketStats | DotaStats;

interface AgentCardProps {
  name: string;
  href: string;
  stats: AgentStats;
  icon?: string;
}

function StatRow({ label, value, color }: { label: string; value: React.ReactNode; color?: string }) {
  return (
    <div className="flex items-center justify-between" style={{ padding: "8px 0", borderBottom: "1px solid #222222" }}>
      <span style={{ fontFamily: "var(--font-mono), monospace", fontSize: "11px", letterSpacing: "0.06em", color: "#666666" }}>
        {label.toUpperCase()}
      </span>
      <span style={{ fontFamily: "var(--font-mono), monospace", fontSize: "13px", color: color ?? "#E8E8E8" }}>
        {value}
      </span>
    </div>
  );
}

function pnlColor(pnl: number | undefined) {
  if (pnl === undefined) return "#E8E8E8";
  return pnl >= 0 ? "#4A9E5C" : "#D71921";
}

export default function AgentCard({ name, href, stats }: AgentCardProps) {
  const mode: "LIVE" | "DRY RUN" | "OFFLINE" = !stats.available
    ? "OFFLINE"
    : stats.is_live
    ? "LIVE"
    : "DRY RUN";

  const modeColor = mode === "LIVE" ? "#D71921" : mode === "DRY RUN" ? "#4A9E5C" : "#666666";

  return (
    <div className="flex-1" style={{ backgroundColor: "#111111", border: "1px solid #222222", borderRadius: "12px", padding: "20px" }}>
      {/* Header */}
      <div className="flex items-center justify-between" style={{ marginBottom: "16px" }}>
        <span style={{ fontFamily: "var(--font-mono), monospace", fontSize: "11px", letterSpacing: "0.08em", color: "#999999" }}>
          {name.toUpperCase()}
        </span>
        <span style={{ fontFamily: "var(--font-mono), monospace", fontSize: "11px", letterSpacing: "0.06em", color: modeColor }}>
          {mode === "LIVE" ? "● LIVE" : mode === "DRY RUN" ? "○ DRY RUN" : "○ OFFLINE"}
        </span>
      </div>

      {!stats.available ? (
        <p style={{ fontFamily: "var(--font-mono), monospace", fontSize: "12px", color: "#666666" }}>[OFFLINE]</p>
      ) : (
        <>
          {/* Hero P&L */}
          <div style={{ marginBottom: "16px" }}>
            <div style={{ fontFamily: "var(--font-mono), monospace", fontSize: "36px", fontWeight: 700, letterSpacing: "-0.02em", color: pnlColor(stats.pnl), lineHeight: 1 }}>
              {stats.pnl !== undefined ? `${stats.pnl >= 0 ? "+" : ""}$${stats.pnl.toFixed(2)}` : "$0.00"}
            </div>
            <div style={{ fontFamily: "var(--font-mono), monospace", fontSize: "11px", color: "#666666", letterSpacing: "0.06em", marginTop: "4px" }}>P&L</div>
          </div>

          {/* Stats */}
          <div>
            <StatRow label="Total" value={stats.total ?? 0} />
            <StatRow label="Open" value={stats.open ?? 0} />
            <StatRow label="Win %" value={`${stats.win_rate ?? 0}%`} />
            <StatRow label="ROI" value={`${stats.roi ?? 0}%`} />
          </div>

          <Link
            href={href}
            style={{ display: "block", fontFamily: "var(--font-mono), monospace", fontSize: "11px", letterSpacing: "0.06em", color: "#666666", marginTop: "16px", transition: "color 150ms" }}
            className="hover:text-white"
          >
            VIEW ALL →
          </Link>
        </>
      )}
    </div>
  );
}
