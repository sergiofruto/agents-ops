"use client";

import { AreaChart, ProgressBar } from "@tremor/react";
import type { FearGreed } from "@/lib/types";

type TremorColor = "red" | "orange" | "yellow" | "lime" | "emerald";

function fngColor(v: number | null): TremorColor {
  if (v === null) return "lime";
  if (v <= 25) return "red";
  if (v <= 45) return "orange";
  if (v <= 55) return "yellow";
  if (v <= 75) return "lime";
  return "emerald";
}

function fngLabel(v: number | null): { text: string; color: string } {
  if (v === null)  return { text: "Unknown",      color: "text-[#475569]" };
  if (v <= 25)     return { text: "Extreme Fear",  color: "text-[#f87171]" };
  if (v <= 45)     return { text: "Fear",          color: "text-[#fb923c]" };
  if (v <= 55)     return { text: "Neutral",       color: "text-[#facc15]" };
  if (v <= 75)     return { text: "Greed",         color: "text-[#34d399]" };
  return             { text: "Extreme Greed",  color: "text-[#34d399]" };
}

export default function FearGreedCard({ fearGreed }: { fearGreed: FearGreed }) {
  const label = fngLabel(fearGreed.value);
  const chartData = fearGreed.history.map((v, i) => ({ i: String(i), value: v }));

  return (
    <div className="bg-[#0f1a2e] border border-[#1e3a5f] rounded-lg p-4 flex flex-col gap-3">
      <span className="text-[11.5px] font-medium text-[#60a5fa] tracking-[0.06em] uppercase">
        Fear & Greed
      </span>

      <div>
        <div className="text-[25px] font-bold leading-none text-[#f1f5f9]">
          {fearGreed.value ?? "—"}
        </div>
        <div className={`text-[11.5px] mt-1 ${label.color}`}>{label.text}</div>
      </div>

      {fearGreed.value !== null && (
        <div>
          <ProgressBar value={fearGreed.value} color={fngColor(fearGreed.value)} />
          <div className="flex justify-between mt-1">
            <span className="text-[10.5px] text-[#475569]">FEAR</span>
            <span className="text-[10.5px] text-[#475569]">GREED</span>
          </div>
        </div>
      )}

      {chartData.length > 0 && (
        <div>
          <div className="text-[10.5px] text-[#475569] mb-1">14-DAY TREND</div>
          <AreaChart
            data={chartData}
            index="i"
            categories={["value"]}
            colors={[fngColor(fearGreed.value)]}
            showXAxis={false}
            showYAxis={false}
            showLegend={false}
            showGridLines={false}
            className="h-14"
          />
        </div>
      )}
    </div>
  );
}
