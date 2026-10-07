import Image from "next/image";
import type { RawLandmark } from "@/lib/landmarks";
import { overlayGeometry } from "@/lib/overlay";

export function SkeletonOverlay({
  src,
  alt,
  width,
  height,
  landmarks,
  sizes,
}: {
  src: string;
  alt: string;
  width: number;
  height: number;
  landmarks: RawLandmark[];
  sizes: string;
}) {
  const g = overlayGeometry(landmarks, width, height);
  return (
    <div className="relative overflow-hidden rounded-md border border-line bg-bg">
      <Image
        src={src}
        alt={alt}
        width={width}
        height={height}
        sizes={sizes}
        className="block h-auto w-full brightness-[0.6] saturate-[0.4]"
      />
      <svg viewBox={`0 0 ${width} ${height}`} className="absolute inset-0 h-full w-full" aria-hidden="true">
        <g className="stroke-accent" strokeWidth={4} strokeLinecap="round">
          {g.bones.map((b, i) => (
            <line key={i} x1={b.x1} y1={b.y1} x2={b.x2} y2={b.y2} />
          ))}
        </g>
        <g className="fill-bg stroke-accent" strokeWidth={3}>
          {g.joints.map((j) => (
            <circle key={j.id} cx={j.x} cy={j.y} r={7} />
          ))}
        </g>
      </svg>
    </div>
  );
}
