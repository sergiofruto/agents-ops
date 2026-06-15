import { financeMock } from "@/lib/finance.mock";

export function FinanceCard() {
  const f = financeMock;
  return (
    <div className="bg-[#0f1a2e] border border-[#1e3a5f] rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11.5px] font-medium text-[#60a5fa] tracking-[0.06em] uppercase">
          Finance
        </span>
        <span className="rounded bg-[#0a1628] border border-[#1e3a5f] px-1.5 py-0.5 text-[10.5px] text-[#475569]">
          SAMPLE
        </span>
      </div>
      <div className="text-[25px] font-bold text-[#f1f5f9]">
        ${f.net_worth_usd.toLocaleString()}
      </div>
      <div className="mt-1 text-[11.5px] text-[#475569]">
        {f.goal_name}: {f.goal_progress_pct}% of ${f.goal_target_usd.toLocaleString()}
      </div>
      <ul className="mt-3 flex flex-col gap-1">
        {f.allocation.map((a) => (
          <li key={a.label} className="flex justify-between text-[11.5px] text-[#94a3b8]">
            <span>{a.label}</span>
            <span>${a.usd.toLocaleString()}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
