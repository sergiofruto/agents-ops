import BtcSparkline from "./BtcSparkline";
import { Progress } from "@/components/ui/progress";
import type { BtcData, StockItem, FearGreed } from "@/lib/types";

interface MarketSectionProps {
  btc: BtcData;
  stocks: StockItem[];
  fearGreed: FearGreed;
}

function fngColor(value: number | null) {
  if (value === null) return "bg-zinc-500";
  if (value <= 25) return "bg-red-500";
  if (value <= 45) return "bg-orange-400";
  if (value <= 55) return "bg-yellow-400";
  if (value <= 75) return "bg-lime-400";
  return "bg-emerald-500";
}

export default function MarketSection({ btc, stocks, fearGreed }: MarketSectionProps) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-3">
        <BtcSparkline data={btc} />

        {/* Fear & Greed */}
        <div className="flex flex-col justify-center rounded-lg bg-white/5 px-4 py-3 min-w-[160px]">
          <span className="text-[11px] uppercase tracking-wide text-zinc-500">Fear & Greed</span>
          <div className="mt-1 flex items-center gap-2">
            <span className="text-2xl font-bold text-zinc-100">
              {fearGreed.value ?? "—"}
            </span>
            <span className="text-xs text-zinc-400">{fearGreed.label}</span>
          </div>
          {fearGreed.value !== null && (
            <div className="mt-2">
              <Progress
                value={fearGreed.value}
                className={`h-1.5 ${fngColor(fearGreed.value)}`}
              />
            </div>
          )}
        </div>
      </div>

      {/* Stocks */}
      {stocks.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {stocks.map((s) => {
            const chgColor =
              s.change_pct == null
                ? "text-zinc-400"
                : s.change_pct >= 0
                ? "text-emerald-400"
                : "text-red-400";
            return (
              <div
                key={s.ticker}
                className="flex flex-col rounded-md bg-white/5 px-3 py-2 min-w-[80px]"
              >
                <span className="text-[10px] uppercase tracking-wide text-zinc-500">
                  {s.ticker}
                </span>
                <span className="mt-0.5 text-sm font-semibold text-zinc-100">
                  {s.price != null ? `$${s.price.toFixed(2)}` : "—"}
                </span>
                <span className={`text-[11px] font-medium ${chgColor}`}>
                  {s.change_pct != null
                    ? `${s.change_pct >= 0 ? "+" : ""}${s.change_pct}%`
                    : "—"}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
