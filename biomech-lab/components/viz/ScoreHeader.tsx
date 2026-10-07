export function ScoreHeader({
  label,
  score,
  coverage,
  meta,
}: {
  label: string;
  score: number;
  coverage: number;
  meta?: string;
}) {
  const pct = Math.round(coverage * 100);
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="font-mono text-xs uppercase tracking-[0.14em] text-fg-subtle">{label}</p>
        <p className="font-mono text-5xl font-semibold leading-none text-fg-strong">
          {score}
          <span className="ml-1 text-base text-fg-subtle">/100</span>
        </p>
      </div>
      <div className="w-44">
        <p className="font-mono text-xs text-fg-subtle">
          confidence {pct}%{meta ? ` · ${meta}` : ""}
        </p>
        <div className="mt-1 h-1.5 rounded-full bg-line" role="img" aria-label={`Measurement confidence ${pct}%`}>
          <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
        </div>
      </div>
    </div>
  );
}
