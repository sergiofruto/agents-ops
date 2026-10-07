import { POSE_ORDER, POSES, type PoseId } from "@/lib/poses";
import type { IterationPoint } from "@/lib/sample-reports";

const SERIES: Record<PoseId, string> = {
  warrior2: "text-accent",
  tree: "text-partial",
  downdog: "text-fg-strong",
};

const W = 560;
const H = 220;
const PAD = { l: 36, r: 130, t: 12, b: 30 };

export function IterationChart({ points }: { points: IterationPoint[] }) {
  if (points.length === 0) return null;
  const xs = (i: number) =>
    points.length === 1 ? PAD.l + (W - PAD.l - PAD.r) / 2 : PAD.l + (i * (W - PAD.l - PAD.r)) / (points.length - 1);
  const ys = (v: number) => PAD.t + ((100 - v) * (H - PAD.t - PAD.b)) / 100;
  const last = points[points.length - 1];

  // Direct labels at the last point, nudged apart so they never overlap.
  const labels = POSE_ORDER.map((id) => ({ id, y: ys(last.scores[id]) })).sort((a, b) => a.y - b.y);
  for (let i = 1; i < labels.length; i++) {
    if (labels[i].y - labels[i - 1].y < 14) labels[i].y = labels[i - 1].y + 14;
  }

  const description = points
    .map((p) => `iteration ${p.iteration}: ${POSE_ORDER.map((id) => `${POSES[id].label} ${p.scores[id]}`).join(", ")}`)
    .join("; ");

  return (
    <figure>
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full min-w-[480px] max-w-xl"
          role="img"
          aria-label={`Score by iteration. ${description}`}
        >
          {[0, 25, 50, 75, 100].map((v) => (
            <g key={v}>
              <line x1={PAD.l} x2={W - PAD.r} y1={ys(v)} y2={ys(v)} className="stroke-line" />
              <text x={PAD.l - 8} y={ys(v) + 4} textAnchor="end" className="fill-fg-subtle font-mono text-[10px]">
                {v}
              </text>
            </g>
          ))}
          {points.map((p, i) => (
            <text key={p.iteration} x={xs(i)} y={H - 8} textAnchor="middle" className="fill-fg-subtle font-mono text-[10px]">
              it.{p.iteration} · {p.date}
            </text>
          ))}
          {POSE_ORDER.map((id) => (
            <g key={id} className={SERIES[id]}>
              {points.length > 1 && (
                <polyline
                  points={points.map((p, i) => `${xs(i)},${ys(p.scores[id])}`).join(" ")}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                />
              )}
              {points.map((p, i) => (
                <circle key={p.iteration} cx={xs(i)} cy={ys(p.scores[id])} r={4} fill="currentColor" />
              ))}
            </g>
          ))}
          {labels.map(({ id, y }) => (
            <text key={id} x={xs(points.length - 1) + 12} y={y + 4} className={`${SERIES[id]} font-mono text-[11px]`} fill="currentColor">
              {POSES[id].label} {last.scores[id]}
            </text>
          ))}
        </svg>
      </div>
      {points.length === 1 && (
        <figcaption className="mt-2 font-mono text-xs text-fg-subtle">1 iteration so far · next shoot pending</figcaption>
      )}
    </figure>
  );
}
