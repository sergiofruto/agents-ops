import { LANDMARK_COUNT } from "@/lib/landmarks";
import { MIN_COVERAGE } from "@/lib/readiness";
import { container, label, panel, sectionShell, sectionTitle } from "./ui/styles";

const STEPS = [
  { key: "input", text: "photo" },
  { key: "detect", text: `MediaPipe · ${LANDMARK_COUNT} landmarks` },
  { key: "project", text: "pixel space (aspect-correct)" },
  { key: "frame", text: "view + framing" },
  { key: "classify", text: "rule-based pose" },
  { key: "gate", text: `readiness ≥ ${Math.round(MIN_COVERAGE * 100)}% coverage` },
  { key: "score", text: "weighted checks → 0–100" },
];

export function Pipeline() {
  return (
    <section id="pipeline" aria-labelledby="pipeline-title" className={sectionShell}>
      <div className={`${container} py-20`}>
        <p className={label}>03 · Pipeline</p>
        <h2 id="pipeline-title" className={sectionTitle}>
          How a score is computed
        </h2>
        <p className="mt-3 max-w-2xl text-fg-muted">
          Deterministic and explainable: the same photo always gets the same score. If the camera
          view, framing or landmark coverage isn&apos;t good enough, the gate returns a prompt
          instead of a number.
        </p>
        <ol className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-7">
          {STEPS.map((s, i) => (
            <li key={s.key} className={`${panel} p-4`}>
              <p className="font-mono text-[11px] text-accent">
                {String(i + 1).padStart(2, "0")} · {s.key}
              </p>
              <p className="mt-2 text-sm text-fg-strong">{s.text}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
