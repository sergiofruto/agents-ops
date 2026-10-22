import { useMemo } from "react";
import { toBody } from "@/lib/body";
import { REGION_LABEL, REGION_ORDER } from "@/lib/posture/config";
import { assessPosture } from "@/lib/posture/findings";
import type { PhotoState } from "@/lib/posture/flow";
import { makeFrame, type PostureView } from "@/lib/posture/frame";
import { coronalOverlay, sagittalOverlay } from "@/lib/posture/overlay";
import { buttonSecondary, panel } from "../ui/styles";
import { FindingRow } from "./FindingRow";
import { PostureOverlay } from "./PostureOverlay";

export const DISCLAIMER =
  "This is a screening, not a diagnosis. Spine curves and pelvic tilt aren't measured. If you have pain or numbness, see a kinesiologist or physiotherapist.";

const VIEWS: PostureView[] = ["front", "side", "back"];

export function PostureResults({
  heightCm,
  photos,
  onEdit,
  onReset,
}: {
  heightCm: number;
  photos: Record<PostureView, PhotoState>;
  onEdit: (step: "height" | PostureView) => void;
  onReset: () => void;
}) {
  const result = useMemo(
    () => assessPosture({ heightCm, front: photos.front.input, side: photos.side.input, back: photos.back.input }),
    [heightCm, photos],
  );

  const overlays = useMemo(
    () =>
      Object.fromEntries(
        VIEWS.map((v) => {
          const p = photos[v].input;
          const frame = makeFrame(v, toBody(p.people[0], p.width, p.height), heightCm);
          return [v, v === "side" ? sagittalOverlay(frame, result.findings) : coronalOverlay(frame, result.findings)];
        }),
      ) as Record<PostureView, ReturnType<typeof coronalOverlay>>,
    [photos, heightCm, result],
  );

  return (
    <section role="status" aria-label="Posture results" className={`${panel} space-y-8 p-6`}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.14em] text-fg-subtle">posture score · 3 of 3 views</p>
          <p className="font-mono text-5xl font-semibold leading-none text-fg-strong">
            {result.score ?? "-"}
            <span className="ml-1 text-base text-fg-subtle">/100</span>
          </p>
        </div>
        <button type="button" className="font-mono text-xs text-fg-subtle hover:text-fg-strong" onClick={() => onEdit("height")}>
          height {heightCm} cm · edit
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {VIEWS.map((v) => (
          <figure key={v} className="space-y-1">
            <PostureOverlay
              url={photos[v].url}
              alt={`Your ${v} photo with posture lines`}
              width={photos[v].input.width}
              height={photos[v].input.height}
              landmarks={photos[v].input.people[0]}
              posture={overlays[v]}
            />
            <figcaption className="flex justify-between font-mono text-[11px] text-fg-subtle">
              {v}
              <button type="button" className="hover:text-fg-strong" onClick={() => onEdit(v)}>
                replace
              </button>
            </figcaption>
          </figure>
        ))}
      </div>

      {REGION_ORDER.map((region) => (
        <div key={region}>
          <p className="font-mono text-xs uppercase tracking-[0.14em] text-accent">{REGION_LABEL[region]}</p>
          <ul className="mt-2 divide-y divide-line rounded-md border border-line">
            {result.findings
              .filter((f) => f.region === region)
              .map((f) => (
                <FindingRow key={f.id} finding={f} />
              ))}
          </ul>
        </div>
      ))}

      <p className="rounded-md border border-line-strong p-4 text-sm text-fg-muted">{DISCLAIMER}</p>

      <button type="button" className={buttonSecondary} onClick={onReset}>
        Start over
      </button>
    </section>
  );
}
