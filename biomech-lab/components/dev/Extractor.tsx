"use client";

import { useEffect, useState } from "react";
import { SAMPLES } from "@/components/PhotoLab";

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
          <h2 className="font-semibold">test/fixtures/{r.id}.json</h2>
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
