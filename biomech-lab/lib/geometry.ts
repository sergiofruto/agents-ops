export type Point = { x: number; y: number };

const DEG = 180 / Math.PI;

export function distance(a: Point, b: Point): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

export function midpoint(a: Point, b: Point): Point {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}

/** Unsigned angle at `b` in degrees, range [0, 180]. NaN if a segment has zero length. */
export function angle(a: Point, b: Point, c: Point): number {
  const v1x = a.x - b.x;
  const v1y = a.y - b.y;
  const v2x = c.x - b.x;
  const v2y = c.y - b.y;
  const mag = Math.hypot(v1x, v1y) * Math.hypot(v2x, v2y);
  if (mag === 0) return NaN;
  const cos = Math.min(1, Math.max(-1, (v1x * v2x + v1y * v2y) / mag));
  return Math.acos(cos) * DEG;
}

/** Unsigned angle between segment p→q and the horizontal axis, degrees, range [0, 90]. */
export function tiltFromHorizontal(p: Point, q: Point): number {
  const dx = Math.abs(q.x - p.x);
  const dy = Math.abs(q.y - p.y);
  if (dx === 0 && dy === 0) return NaN;
  return Math.atan2(dy, dx) * DEG;
}

/** Unsigned angle between segment p→q and the vertical axis, degrees, range [0, 90]. */
export function tiltFromVertical(p: Point, q: Point): number {
  const t = tiltFromHorizontal(p, q);
  return Number.isNaN(t) ? NaN : 90 - t;
}

/** Perpendicular distance from p to the line through a and b, in pixels. NaN if a == b. */
export function distanceToLine(p: Point, a: Point, b: Point): number {
  const len = distance(a, b);
  if (len === 0) return NaN;
  return Math.abs((b.x - a.x) * (a.y - p.y) - (a.x - p.x) * (b.y - a.y)) / len;
}
