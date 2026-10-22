import { CircleAlert, CircleCheck, CircleMinus, CircleX, type LucideIcon } from "lucide-react";
import { FINDINGS } from "@/lib/posture/config";
import { formatCm, formatDeg, measuredSentence } from "@/lib/posture/copy";
import { LIBRARY } from "@/lib/posture/exercises";
import type { Finding, PostureStatus } from "@/lib/posture/findings";

const STATUS: Record<PostureStatus, { Icon: LucideIcon; text: string; className: string }> = {
  aligned: { Icon: CircleCheck, text: "aligned", className: "text-pass" },
  slight: { Icon: CircleAlert, text: "slight", className: "text-partial" },
  needs_work: { Icon: CircleX, text: "needs work", className: "text-fail" },
  not_measured: { Icon: CircleMinus, text: "not measured", className: "text-fg-subtle" },
};

function valueText(f: Finding): string {
  if (f.value === null) return "-";
  return f.unit === "cm" ? formatCm(f.value) : formatDeg(f.value);
}

export function FindingRow({ finding }: { finding: Finding }) {
  const s = STATUS[finding.status];
  const off = finding.status === "slight" || finding.status === "needs_work";
  const entry = LIBRARY[finding.id];
  const cva = finding.id === "forwardHead" ? finding.extra?.earShoulderAngle : null;

  const header = (
    <span className="flex flex-1 items-center justify-between gap-3">
      <span className="font-medium text-fg-strong">{FINDINGS[finding.id].label}</span>
      <span className="flex items-center gap-3">
        <span className="font-mono text-xs text-fg-muted">{valueText(finding)}</span>
        <span className={`inline-flex items-center gap-1 font-mono text-xs ${s.className}`}>
          <s.Icon aria-hidden="true" className="size-3.5" />
          {s.text}
        </span>
      </span>
    </span>
  );

  if (!off) {
    return (
      <li className="flex items-center gap-3 px-4 py-3">
        {header}
      </li>
    );
  }

  return (
    <li className="px-4 py-4">
      <details open>
        <summary className="flex cursor-pointer list-none items-center">{header}</summary>
        <div className="mt-3 space-y-3 text-sm">
          <p className="text-fg-strong">{measuredSentence(finding)}</p>
          {finding.disagree && (
            <p className="text-partial">Front and back photos disagree; retake for a reliable reading.</p>
          )}
          <p className="text-fg-muted">{entry.explanation(finding)}</p>
          {cva !== null && cva !== undefined && (
            <p className="font-mono text-xs text-fg-subtle">ear-shoulder angle (approximates CVA): {formatDeg(cva)}</p>
          )}
          <ul className="grid gap-3 md:grid-cols-3">
            {entry.exercises(finding).map((e) => (
              <li key={e.name} className="rounded-md border border-line-strong p-3">
                <p className="font-medium text-fg-strong">{e.name}</p>
                <ol className="mt-2 list-decimal space-y-1 pl-4 text-fg-muted">
                  {e.steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
                <p className="mt-2 font-mono text-xs text-accent">{e.dosage}</p>
              </li>
            ))}
          </ul>
        </div>
      </details>
    </li>
  );
}
