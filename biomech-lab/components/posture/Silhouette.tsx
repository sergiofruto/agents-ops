import type { PostureView } from "@/lib/posture/frame";

/** Simple outline showing how to stand for each view. */
export function Silhouette({ view }: { view: PostureView }) {
  return (
    <svg viewBox="0 0 80 180" className="h-44 w-auto text-line-strong" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      {view === "side" ? (
        <>
          <circle cx={42} cy={18} r={11} />
          <path d="M53 18 l4 2" />
          <path d="M40 30 C36 50 36 70 38 95 L40 128 L41 168 L54 170" />
          <path d="M44 30 C48 50 48 70 46 95" />
          <path d="M42 40 L44 92" />
          <line x1={42} y1={6} x2={42} y2={176} strokeDasharray="3 4" className="text-accent" stroke="currentColor" strokeWidth={1} />
        </>
      ) : (
        <>
          <circle cx={40} cy={18} r={11} />
          {view === "front" && <path d="M36 17 h1 M43 17 h1" />}
          <path d="M22 36 h36 M22 36 L18 92 M58 36 L62 92 M26 36 L28 96 h24 L54 36 M30 96 L32 168 M50 96 L48 168" />
          <line x1={40} y1={6} x2={40} y2={176} strokeDasharray="3 4" className="text-accent" stroke="currentColor" strokeWidth={1} />
        </>
      )}
    </svg>
  );
}
