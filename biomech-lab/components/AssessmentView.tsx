import { Info, TriangleAlert } from "lucide-react";
import type { Assessment } from "@/lib/assess";
import { POSES } from "@/lib/poses";
import { CheckRow } from "./viz/CheckRow";
import { ScoreHeader } from "./viz/ScoreHeader";

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div role="status" className="flex gap-3 rounded-lg border border-line bg-surface p-5">
      <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-accent" />
      <p className="text-fg-strong">{children}</p>
    </div>
  );
}

export function AssessmentView({ assessment, meta }: { assessment: Assessment; meta?: string }) {
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
        <section role="status" className="rounded-lg border border-partial/40 bg-surface p-6">
          <div className="flex items-center gap-2">
            <TriangleAlert aria-hidden="true" className="size-5 text-partial" />
            <h3 className="font-semibold text-fg-strong">
              {POSES[assessment.pose].label} detected — we can&apos;t score it yet
            </h3>
          </div>
          <ul className="mt-3 list-disc space-y-1 pl-6 text-fg-muted">
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
        <section role="status" className="rounded-lg border border-line bg-surface p-6">
          <h3 className="sr-only">{POSES[assessment.pose].label} result</h3>
          <ScoreHeader label={POSES[assessment.pose].label} score={result.score} coverage={readiness.coverage} meta={meta} />
          <ul className="mt-4 divide-y divide-line">
            {result.checks.map((c) => (
              <CheckRow key={c.id} check={c} />
            ))}
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
