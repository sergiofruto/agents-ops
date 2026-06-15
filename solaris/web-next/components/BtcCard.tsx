"use client";

import { AreaChart } from "@tremor/react";
import type { BtcData } from "@/lib/types";

export default function BtcCard({ btc }: { btc: BtcData }) {
  const chartData = btc.sparkline.map((price, i) => ({ i: String(i), price }));
  const isPositive = (btc.change_24h ?? 0) >= 0;
  const changeColor = isPositive ? "text-[#34d399]" : "text-[#f87171]";
  const changePrefix = isPositive ? "↑" : "↓";

  return (
    <div className="bg-[#0f1a2e] border border-[#1e3a5f] rounded-lg p-4 flex flex-col gap-2">
      <span className="text-[11.5px] font-medium text-[#60a5fa] tracking-[0.06em] uppercase">
        Bitcoin
      </span>

      <div>
        <div className="text-[25px] font-bold leading-none text-[#f1f5f9]">
          {btc.price != null ? `$${btc.price.toLocaleString()}` : "—"}
        </div>
        {btc.change_24h != null && (
          <div className={`text-[11.5px] mt-1 ${changeColor}`}>
            {changePrefix} {Math.abs(btc.change_24h).toFixed(2)}% 24h
          </div>
        )}
      </div>

      {chartData.length > 0 && (
        <AreaChart
          data={chartData}
          index="i"
          categories={["price"]}
          colors={["blue"]}
          showXAxis={false}
          showYAxis={false}
          showLegend={false}
          showGridLines={false}
          className="h-14 mt-1"
        />
      )}
    </div>
  );
}
