"use client";

import { ImageUp, LoaderCircle, RotateCcw, TriangleAlert } from "lucide-react";
import type { ChangeEvent } from "react";
import type { PhotoState } from "@/lib/posture/flow";
import type { PostureView } from "@/lib/posture/frame";
import { buttonPrimary, buttonSecondary, panel } from "../ui/styles";
import { PostureOverlay } from "./PostureOverlay";
import { Silhouette } from "./Silhouette";

const STEP: Record<PostureView, { n: number; heading: string; extraTip?: string }> = {
  front: { n: 1, heading: "Face the camera" },
  side: { n: 2, heading: "Stand sideways to the camera", extraTip: "Either side is fine" },
  back: { n: 3, heading: "Turn your back to the camera", extraTip: "Hair off the neck if possible" },
};

const TIPS = [
  "Whole body in frame, feet visible",
  "Arms relaxed by your sides",
  "Camera at hip height, 2-3 m away",
  "Fitted clothes, plain wall",
];

export function PhotoStep({
  view,
  candidate,
  busy,
  error,
  onFile,
  onUse,
  onRetake,
  onBack,
}: {
  view: PostureView;
  candidate: PhotoState | null;
  busy: boolean;
  error: string | null;
  onFile: (file: File) => void;
  onUse: () => void;
  onRetake: () => void;
  onBack: () => void;
}) {
  const step = STEP[view];
  const tips = step.extraTip ? [...TIPS, step.extraTip] : TIPS;

  function change(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) onFile(file);
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-1.5" aria-hidden="true">
        {[1, 2, 3].map((i) => (
          <div key={i} className={`h-1 flex-1 rounded-full ${i <= step.n ? "bg-accent" : "bg-line"}`} />
        ))}
      </div>
      <div>
        <p className="font-mono text-xs uppercase tracking-[0.14em] text-fg-subtle">
          step {step.n} of 3 · {view} view
        </p>
        <h3 className="mt-1 text-xl font-semibold text-fg-strong">{step.heading}</h3>
      </div>

      {candidate ? (
        <div className={`${panel} grid gap-6 p-6 sm:grid-cols-[minmax(0,260px)_1fr]`}>
          <PostureOverlay
            url={candidate.url}
            alt={`Your ${view} photo with detected body points`}
            width={candidate.input.width}
            height={candidate.input.height}
            landmarks={candidate.input.people[0]}
          />
          <div className="flex flex-col justify-center gap-3">
            <p className="text-fg-strong">Looks good. We found your whole body in the right position.</p>
            <div className="flex flex-wrap gap-3">
              <button type="button" className={buttonPrimary} onClick={onUse}>
                Use this photo
              </button>
              <button type="button" className={buttonSecondary} onClick={onRetake}>
                <RotateCcw aria-hidden="true" className="size-4" />
                Retake
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className={`${panel} flex flex-col gap-6 p-6 sm:flex-row`}>
          <Silhouette view={view} />
          <div className="flex-1">
            <p className="font-mono text-xs uppercase tracking-[0.14em] text-fg-subtle">for a good photo</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-fg-muted">
              {tips.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
            <label className={`${buttonPrimary} mt-5 cursor-pointer has-[input:focus-visible]:outline-2`}>
              <ImageUp aria-hidden="true" className="size-4" />
              Upload {view} photo
              <input type="file" accept="image/*" onChange={change} className="sr-only" disabled={busy} />
            </label>
          </div>
        </div>
      )}

      {busy && (
        <p role="status" className="flex items-center gap-2 font-mono text-sm text-fg-muted">
          <LoaderCircle aria-hidden="true" className="size-4 animate-spin text-accent" />
          checking your photo… the first run downloads the pose model
        </p>
      )}
      {error && (
        <div role="alert" className={`${panel} flex items-center gap-3 border-fail/40 p-4`}>
          <TriangleAlert aria-hidden="true" className="size-5 shrink-0 text-fail" />
          <p className="text-fg-strong">{error}</p>
        </div>
      )}

      <button type="button" className="font-mono text-xs text-fg-subtle hover:text-fg-strong" onClick={onBack}>
        ← back
      </button>
    </div>
  );
}
