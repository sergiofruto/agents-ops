import { gaugeGeometry } from "@/lib/gauge";

const TRACK = 200;

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
  const x = (f: number) => f * TRACK;
  const description =
    value === null
      ? `${label}: not measured; target ${target}° ± ${tol}°`
      : `${label}: measured ${Math.round(value)}°, target ${target}° ± ${tol}°`;
  return (
    <svg viewBox={`0 0 ${TRACK} 24`} className="h-6 w-full" role="img" aria-label={description}>
      <rect x={0} y={9} width={TRACK} height={6} rx={3} className="fill-line" />
      <rect x={x(g.partial[0])} y={9} width={x(g.partial[1]) - x(g.partial[0])} height={6} className="fill-partial/25" />
      <rect x={x(g.band[0])} y={9} width={Math.max(2, x(g.band[1]) - x(g.band[0]))} height={6} className="fill-accent/50" />
      {value !== null && (
        <rect x={Math.min(TRACK - 3, Math.max(0, x(g.value) - 1.5))} y={3} width={3} height={18} rx={1.5} className="fill-fg-strong" />
      )}
    </svg>
  );
}
