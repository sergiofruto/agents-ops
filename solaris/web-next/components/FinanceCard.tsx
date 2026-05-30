import { financeMock } from "@/lib/finance.mock";

export function FinanceCard() {
  const f = financeMock;
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-950 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-neutral-300">Finance (demo data)</h3>
        <span className="rounded bg-neutral-800 px-1.5 py-0.5 text-[10px] text-neutral-400">SAMPLE</span>
      </div>
      <div className="mt-2 text-2xl font-semibold">${f.net_worth_usd.toLocaleString()}</div>
      <div className="mt-1 text-xs text-neutral-400">
        {f.goal_name}: {f.goal_progress_pct}% of ${f.goal_target_usd.toLocaleString()}
      </div>
      <ul className="mt-3 space-y-1 text-xs text-neutral-400">
        {f.allocation.map(a => (
          <li key={a.label} className="flex justify-between">
            <span>{a.label}</span><span>${a.usd.toLocaleString()}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
