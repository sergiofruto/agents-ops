export const GAUGE_MAX_DEG = 180;

export type GaugeGeometry = { value: number; band: [number, number]; partial: [number, number] };

const unit = (deg: number) => Math.min(GAUGE_MAX_DEG, Math.max(0, deg)) / GAUGE_MAX_DEG;

/** Positions along a 0..180° track (0..1): full-credit band, partial-credit band, measured marker. */
export function gaugeGeometry(target: number, tol: number, value: number): GaugeGeometry {
  return {
    value: unit(value),
    band: [unit(target - tol), unit(target + tol)],
    partial: [unit(target - 2 * tol), unit(target + 2 * tol)],
  };
}
