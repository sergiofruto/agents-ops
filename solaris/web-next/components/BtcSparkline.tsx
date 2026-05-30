"use client";

import type { BtcData } from "@/lib/types";

interface BtcSparklineProps {
  data: BtcData;
}

export default function BtcSparkline({ data }: BtcSparklineProps) {
  const { price, change_24h, sparkline } = data;

  const width = 200;
  const height = 50;
  const pad = 4;

  let polyline = "";
  if (sparkline && sparkline.length > 1) {
    const min = Math.min(...sparkline);
    const max = Math.max(...sparkline);
    const range = max - min || 1;
    const points = sparkline.map((p, i) => {
      const x = pad + (i / (sparkline.length - 1)) * (width - pad * 2);
      const y = pad + (1 - (p - min) / range) * (height - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    polyline = points.join(" ");
  }

  const changeColor =
    change_24h === null || change_24h === undefined
      ? "text-zinc-400"
      : change_24h >= 0
      ? "text-emerald-400"
      : "text-red-400";

  return (
    <div className="flex items-center gap-4 rounded-lg bg-white/5 px-4 py-3">
      <div className="flex flex-col">
        <span className="text-[11px] uppercase tracking-wide text-zinc-500">BTC/USD</span>
        <span className="text-lg font-semibold text-zinc-100">
          {price != null ? `$${price.toLocaleString()}` : "—"}
        </span>
        <span className={`text-xs font-medium ${changeColor}`}>
          {change_24h != null
            ? `${change_24h >= 0 ? "+" : ""}${change_24h}% (24h)`
            : "—"}
        </span>
      </div>
      {polyline && (
        <svg
          width={width}
          height={height}
          className="shrink-0 opacity-80"
          viewBox={`0 0 ${width} ${height}`}
        >
          <polyline
            points={polyline}
            fill="none"
            stroke={
              (change_24h ?? 0) >= 0 ? "#34d399" : "#f87171"
            }
            strokeWidth="1.5"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        </svg>
      )}
    </div>
  );
}
