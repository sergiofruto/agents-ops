import {
  CircleAlert,
  CircleCheck,
  CircleMinus,
  CircleX,
  Info,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import type { Assessment } from "@/lib/assess";
import { POSES } from "@/lib/poses";
import type { CheckResult, CheckStatus } from "@/lib/score";

const STATUS: Record<CheckStatus, { Icon: LucideIcon; text: string; className: string }> = {
  pass: { Icon: CircleCheck, text: "Pass", className: "text-pass" },
  partial: { Icon: CircleAlert, text: "Partial", className: "text-partial" },
  fail: { Icon: CircleX, text: "Needs work", className: "text-fail" },
  not_measured: { Icon: CircleMinus, text: "Not measured", className: "text-ink-subtle" },
};

function formatValue(c: CheckResult): string {
  if (c.value === null) return "—";
  return c.unit === "deg" ? `${Math.round(c.value)}°` : c.value.toFixed(2);
}

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div role="status" className="flex gap-3 rounded-2xl border border-line bg-white p-5">
      <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-accent" />
      <p>{children}</p>
    </div>
  );
}

export function AssessmentView({ assessment }: { assessment: Assessment }) {
  switch (assessment.kind) {
    case "no_person":
      return <Notice>We couldn&apos;t find a person. Step back so your whole body is in frame.</Notice>;
    case "multiple_people":
      return <Notice>Make sure you&apos;re alone in the frame.</Notice>;
    case "unknown_pose":
      return (
        <Notice>
          We didn&apos;t recognize the pose. Try Warrior II or Tree facing the camera, or Downward
          Dog from the side.
        </Notice>
      );
    case "not_ready":
      return (
        <section role="status" className="rounded-2xl border border-partial/30 bg-white p-6">
          <div className="flex items-center gap-2">
            <TriangleAlert aria-hidden="true" className="size-5 text-partial" />
            <h3 className="font-semibold">
              {POSES[assessment.pose].label} detected — we can&apos;t score it yet
            </h3>
          </div>
          <ul className="mt-3 list-disc space-y-1 pl-6 text-ink-muted">
            {assessment.messages.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </section>
      );
    case "scored": {
      const { result, readiness } = assessment;
      if (result.score === null) {
        return (
          <Notice>
            We couldn&apos;t measure enough of your pose to score it. Adjust your position or
            lighting.
          </Notice>
        );
      }
      return (
        <section role="status" className="rounded-2xl border border-line bg-white p-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h3 className="text-sm font-medium text-ink-subtle">{POSES[assessment.pose].label}</h3>
              <p className="font-display text-6xl leading-none">
                {result.score}
                <span className="ml-1 font-sans text-base text-ink-subtle">/ 100</span>
              </p>
            </div>
            <p className="text-sm text-ink-subtle">
              Measurement confidence {Math.round(readiness.coverage * 100)}%
            </p>
          </div>
          <ul className="mt-6 divide-y divide-line">
            {result.checks.map((c) => {
              const s = STATUS[c.status];
              return (
                <li key={c.id} className="flex items-start gap-3 py-3">
                  <s.Icon aria-hidden="true" className={`mt-0.5 size-5 shrink-0 ${s.className}`} />
                  <div className="flex-1">
                    <p className="font-medium">{c.label}</p>
                    {c.status !== "pass" && c.status !== "not_measured" && (
                      <p className="text-sm text-ink-muted">{c.cue}</p>
                    )}
                  </div>
                  <div className="text-right text-sm">
                    <p className="tabular-nums">
                      {formatValue(c)} <span className="text-ink-subtle">/ {c.targetText}</span>
                    </p>
                    <p className={s.className}>{s.text}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      );
    }
    default: {
      const _exhaustive: never = assessment;
      return _exhaustive;
    }
  }
}
