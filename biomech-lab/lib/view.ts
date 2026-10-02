import type { Body } from "./body";
import type { Joint } from "./landmarks";

export type View = "front" | "side" | "ambiguous";

export const FRONT_MIN_RATIO = 0.45;
export const SIDE_MAX_RATIO = 0.25;
export const MIN_BODY_SPAN = 0.4;

export const CORE_JOINTS: Joint[] = ["leftShoulder", "rightShoulder", "leftHip", "rightHip"];

export function shoulderRatio(b: Body): number {
  return b.torsoLength === 0 ? NaN : b.shoulderWidth / b.torsoLength;
}

export function inferView(b: Body): View {
  const r = shoulderRatio(b);
  if (!Number.isFinite(r)) return "ambiguous";
  if (r >= FRONT_MIN_RATIO) return "front";
  if (r <= SIDE_MAX_RATIO) return "side";
  return "ambiguous";
}

export function framingOk(b: Body): boolean {
  if (!CORE_JOINTS.every((j) => b.usable(j))) return false;
  const { minX, minY, maxX, maxY } = b.bbox;
  const span = Math.max((maxX - minX) / b.width, (maxY - minY) / b.height);
  return span >= MIN_BODY_SPAN;
}
