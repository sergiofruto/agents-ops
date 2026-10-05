import Image from "next/image";
import { poseSummaries } from "@/lib/pose-summaries";
import { SAMPLES } from "@/lib/samples";
import { card, eyebrow } from "./ui/styles";

export function PoseChecks() {
  const poses = poseSummaries();
  return (
    <section id="poses" aria-labelledby="poses-title" className="scroll-mt-20 border-t border-line">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <p className={eyebrow}>The poses</p>
        <h2 id="poses-title" className="mt-3 font-display text-3xl md:text-4xl">
          What we check
        </h2>
        <p className="mt-3 max-w-2xl text-ink-muted">
          Every score comes from explicit, measurable checks. No black box: you see the angle we
          measured and the target.
        </p>
        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {poses.map((p) => {
            const sample = SAMPLES.find((s) => s.id === p.id);
            return (
              <article key={p.id} className={`${card} overflow-hidden`}>
                {sample && (
                  <Image
                    src={sample.src}
                    alt=""
                    width={640}
                    height={360}
                    sizes="(min-width: 768px) 360px, 100vw"
                    className="aspect-video w-full object-cover"
                  />
                )}
                <div className="p-6">
                  <h3 className="font-display text-xl">{p.label}</h3>
                  <p className="text-sm text-ink-subtle">{p.viewLabel}</p>
                  <ul className="mt-4 space-y-2 text-sm">
                    {p.checks.map((c) => (
                      <li key={c.id} className="flex justify-between gap-3 border-t border-line pt-2">
                        <span>{c.label}</span>
                        {c.target && <span className="tabular-nums text-ink-subtle">{c.target}</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
