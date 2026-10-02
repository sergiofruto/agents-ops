import type { Assessment } from "@/lib/assess";
import { POSES } from "@/lib/poses";
import type { CheckResult, CheckStatus } from "@/lib/score";

const STATUS: Record<CheckStatus, { icon: string; text: string; className: string }> = {
  pass: { icon: "✓", text: "Pass", className: "text-emerald-400" },
  partial: { icon: "◐", text: "Partial", className: "text-amber-400" },
  fail: { icon: "✗", text: "Needs work", className: "text-rose-400" },
  not_measured: { icon: "—", text: "Not measured", className: "text-neutral-400" },
};

function formatValue(c: CheckResult): string {
  if (c.value === null) return "—";
  return c.unit === "deg" ? `${Math.round(c.value)}°` : c.value.toFixed(2);
}

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <p role="status" className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
      {children}
    </p>
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
        <section role="status" className="space-y-2 rounded-lg border border-amber-900 bg-neutral-900 p-4">
          <h2 className="font-semibold">
            {POSES[assessment.pose].label} detected — we can&apos;t score it yet
          </h2>
          <ul className="list-disc pl-5">
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
        <section role="status" className="space-y-4 rounded-lg border border-neutral-800 bg-neutral-900 p-4">
          <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
            <h2 className="text-lg font-semibold">{POSES[assessment.pose].label}</h2>
            <p>
              <span className="text-4xl font-bold">{result.score}</span>
              <span className="text-neutral-400"> / 100 posture score</span>
            </p>
            <p className="text-sm text-neutral-400">
              Measurement confidence: {Math.round(readiness.coverage * 100)}%
            </p>
          </div>
          <table className="w-full text-left text-sm">
            <thead className="text-neutral-400">
              <tr>
                <th className="py-1">Check</th>
                <th>Measured</th>
                <th>Target</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {result.checks.map((c) => (
                <tr key={c.id} className="border-t border-neutral-800 align-top">
                  <td className="py-2">
                    <div>{c.label}</div>
                    {c.status !== "pass" && c.status !== "not_measured" && (
                      <div className="text-neutral-400">{c.cue}</div>
                    )}
                  </td>
                  <td className="py-2">{formatValue(c)}</td>
                  <td className="py-2">{c.targetText}</td>
                  <td className={`py-2 ${STATUS[c.status].className}`}>
                    <span aria-hidden="true">{STATUS[c.status].icon} </span>
                    {STATUS[c.status].text}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      );
    }
    default: {
      const _exhaustive: never = assessment;
      return _exhaustive;
    }
  }
}
