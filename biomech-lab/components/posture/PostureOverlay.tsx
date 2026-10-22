import type { RawLandmark } from "@/lib/landmarks";
import { overlayGeometry } from "@/lib/overlay";
import type { PostureStatus } from "@/lib/posture/findings";
import type { PostureOverlayGeometry } from "@/lib/posture/overlay";

const STROKE: Record<PostureStatus, string> = {
  aligned: "stroke-pass",
  slight: "stroke-partial",
  needs_work: "stroke-fail",
  not_measured: "stroke-fg-subtle",
};

const FILL: Record<PostureStatus, string> = {
  aligned: "fill-pass",
  slight: "fill-partial",
  needs_work: "fill-fail",
  not_measured: "fill-fg-subtle",
};

/**
 * A downscaled photo (blob URL, so a plain <img>, not next/image) with the skeleton and,
 * when given, the posture lines and dots on top.
 */
export function PostureOverlay({
  url,
  alt,
  width,
  height,
  landmarks,
  posture,
}: {
  url: string;
  alt: string;
  width: number;
  height: number;
  landmarks: RawLandmark[];
  posture?: PostureOverlayGeometry;
}) {
  const g = overlayGeometry(landmarks, width, height);
  const unit = Math.max(width, height) / 400;
  return (
    <div className="relative overflow-hidden rounded-md border border-line bg-bg">
      {/* eslint-disable-next-line @next/next/no-img-element -- local blob URL */}
      <img src={url} alt={alt} width={width} height={height} className="block h-auto w-full brightness-[0.6] saturate-[0.4]" />
      <svg viewBox={`0 0 ${width} ${height}`} className="absolute inset-0 h-full w-full" aria-hidden="true">
        <g className="stroke-line-strong" strokeWidth={unit * 1.5} strokeLinecap="round">
          {g.bones.map((b, i) => (
            <line key={i} x1={b.x1} y1={b.y1} x2={b.x2} y2={b.y2} />
          ))}
        </g>
        {posture?.lines.map((l, i) => (
          <line
            key={`l${i}`}
            x1={l.x1}
            y1={l.y1}
            x2={l.x2}
            y2={l.y2}
            className={STROKE[l.status]}
            strokeWidth={unit * (l.dashed ? 1.2 : 2)}
            strokeDasharray={l.dashed ? `${unit * 4} ${unit * 3}` : undefined}
            strokeLinecap="round"
          />
        ))}
        {posture?.dots.map((d, i) => (
          <circle key={`d${i}`} cx={d.x} cy={d.y} r={unit * 3} className={`${FILL[d.status]} stroke-bg`} strokeWidth={unit} />
        ))}
        {!posture &&
          g.joints.map((j) => <circle key={j.id} cx={j.x} cy={j.y} r={unit * 2.5} className="fill-bg stroke-accent" strokeWidth={unit} />)}
      </svg>
    </div>
  );
}
