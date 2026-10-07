import { CircleAlert, CircleCheck, CircleMinus, CircleX, type LucideIcon } from "lucide-react";
import type { CheckStatus } from "@/lib/score";

export const STATUS: Record<CheckStatus, { Icon: LucideIcon; text: string; className: string }> = {
  pass: { Icon: CircleCheck, text: "pass", className: "text-pass" },
  partial: { Icon: CircleAlert, text: "partial", className: "text-partial" },
  fail: { Icon: CircleX, text: "fail", className: "text-fail" },
  not_measured: { Icon: CircleMinus, text: "not measured", className: "text-fg-subtle" },
};

export function StatusBadge({ status }: { status: CheckStatus }) {
  const s = STATUS[status];
  return (
    <span className={`inline-flex items-center gap-1 font-mono text-xs ${s.className}`}>
      <s.Icon aria-hidden="true" className="size-3.5" />
      {s.text}
    </span>
  );
}
