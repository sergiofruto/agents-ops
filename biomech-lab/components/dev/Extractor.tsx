"use client";

import { useEffect, useState } from "react";
import { targetSize } from "@/lib/posture/image";
import { SAMPLES } from "@/lib/samples";

/** Local, gitignored posture photos (public/user-1-assets/posture), detected at production size. */
const POSTURE_PHOTOS = ["front", "side", "back"].map((view) => ({
  id: `posture/${view}`,
  src: `/user-1-assets/posture/posture-01-${view}.jpg`,
}));

async function downscaled(src: string): Promise<HTMLImageElement> {
  const img = new window.Image();
  img.src = src;
  await img.decode();
  const { width, height } = targetSize(img.naturalWidth, img.naturalHeight);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  canvas.getContext("2d")!.drawImage(img, 0, 0, width, height);
  const out = new window.Image();
  out.src = canvas.toDataURL("image/jpeg", 0.9);
  await out.decode();
  return out;
}

type Row = { id: string; json: string };

export function Extractor() {
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const { createImageEngine } = await import("@/lib/pose-engine");
      const engine = await createImageEngine();
      try {
        const out: Row[] = [];
        for (const s of SAMPLES) {
          const img = new window.Image();
          img.src = s.src;
          await img.decode();
          const d = engine.detectImage(img);
          out.push({
            id: s.id,
            json: JSON.stringify({ sample: s.id, width: d.width, height: d.height, people: d.people }, null, 2),
          });
        }
        for (const p of POSTURE_PHOTOS) {
          try {
            const d = engine.detectImage(await downscaled(p.src));
            out.push({
              id: p.id,
              json: JSON.stringify({ sample: p.id, width: d.width, height: d.height, people: d.people }, null, 2),
            });
          } catch {
            // The posture photos are local only; skip them when missing.
          }
        }
        if (!cancelled) setRows(out);
      } finally {
        engine.close();
      }
    })().catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <p role="alert">{error}</p>;
  if (rows.length === 0) return <p>Running MediaPipe on the samples…</p>;
  return (
    <div className="space-y-6">
      {rows.map((r) => (
        <section key={r.id} className="space-y-2">
          <h2 className="font-semibold">data/samples/{r.id}.json</h2>
          <button type="button" className="rounded bg-neutral-800 px-3 py-1 text-sm" onClick={() => void navigator.clipboard.writeText(r.json)}>
            Copy
          </button>
          <pre data-fixture={r.id} className="max-h-64 overflow-auto rounded bg-neutral-900 p-3 text-xs">
            {r.json}
          </pre>
        </section>
      ))}
    </div>
  );
}
