import type { CheckResult } from "@/lib/score";
import { AngleGauge } from "./AngleGauge";
import { CreditBar } from "./CreditBar";
import { StatusBadge } from "./StatusBadge";

export function formatValue(c: CheckResult): string {
  if (c.value === null) return "—";
  return c.unit === "deg" ? `${Math.round(c.value)}°` : c.value.toFixed(2);
}

export function earnedPoints(c: CheckResult): number {
  return c.credit === null ? 0 : Math.round(c.weight * c.credit * 10) / 10;
}

export function CheckRow({ check, showCue = true }: { check: CheckResult; showCue?: boolean }) {
  const earned = earnedPoints(check);
  const needsWork = check.status === "partial" || check.status === "fail";
  return (
    <li className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1.5 py-3">
      <div>
        <p className="text-sm font-medium text-fg-strong">{check.label}</p>
        {showCue && needsWork && <p className="text-xs text-fg-muted">{check.cue}</p>}
      </div>
      <div className="text-right">
        <p className="font-mono text-sm tabular-nums text-fg-strong">
          {formatValue(check)} <span className="text-fg-subtle">/ {check.targetText}</span>
        </p>
        <StatusBadge status={check.status} />
      </div>
      <div className="col-span-2">
        {check.unit === "deg" && check.range ? (
          <AngleGauge target={check.range.target} tol={check.range.tol} value={check.value} label={check.label} />
        ) : (
          <CreditBar earned={earned} weight={check.weight} status={check.status} />
        )}
      </div>
      <p className="col-span-2 font-mono text-[11px] text-fg-subtle">
        {earned} / {check.weight} pts
      </p>
    </li>
  );
}
