import { gaugeGeometry } from "@/lib/gauge";

const pct = (f: number) => `${f * 100}%`;

export function AngleGauge({
  target,
  tol,
  value,
  label,
}: {
  target: number;
  tol: number;
  value: number | null;
  label: string;
}) {
  const g = gaugeGeometry(target, tol, value ?? target);
  const description =
    value === null
      ? `${label}: not measured; target ${target}° ± ${tol}°`
      : `${label}: measured ${Math.round(value)}°, target ${target}° ± ${tol}°`;
  return (
    <div className="relative h-6 w-full" role="img" aria-label={description}>
      <div className="absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-line" />
      <div
        className="absolute top-1/2 h-1.5 -translate-y-1/2 bg-partial/25"
        style={{ left: pct(g.partial[0]), width: pct(g.partial[1] - g.partial[0]) }}
      />
      <div
        className="absolute top-1/2 h-1.5 -translate-y-1/2 bg-accent/50"
        style={{ left: pct(g.band[0]), width: `max(2px, ${pct(g.band[1] - g.band[0])})` }}
      />
      {value !== null && (
        <div
          className="absolute top-0 h-full w-[3px] rounded-sm bg-fg-strong"
          style={{ left: `clamp(0px, calc(${pct(g.value)} - 1.5px), calc(100% - 3px))` }}
        />
      )}
    </div>
  );
}
