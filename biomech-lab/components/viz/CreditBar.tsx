import type { CheckStatus } from "@/lib/score";

const FILL: Record<CheckStatus, string> = {
  pass: "bg-pass",
  partial: "bg-partial",
  fail: "bg-fail",
  not_measured: "bg-line-strong",
};

export function CreditBar({ earned, weight, status }: { earned: number; weight: number; status: CheckStatus }) {
  const pct = weight === 0 ? 0 : Math.round((earned / weight) * 100);
  return (
    <div className="h-1.5 w-full rounded-full bg-line" role="img" aria-label={`${earned} of ${weight} points`}>
      <div className={`h-full rounded-full ${FILL[status]}`} style={{ width: `${pct}%` }} />
    </div>
  );
}
