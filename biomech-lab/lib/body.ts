import { distance, midpoint, type Point } from "./geometry";
import {
  ALL_JOINTS,
  JOINT_INDEX,
  LANDMARK_COUNT,
  type Joint,
  type RawLandmark,
} from "./landmarks";

export const MIN_VISIBILITY = 0.5;
export const EDGE_MARGIN = 0.02;

export type BBox = { minX: number; minY: number; maxX: number; maxY: number };

export type Body = {
  width: number;
  height: number;
  point: (j: Joint) => Point;
  visibility: (j: Joint) => number;
  usable: (j: Joint) => boolean;
  shoulderMid: Point;
  hipMid: Point;
  torsoLength: number;
  shoulderWidth: number;
  bbox: BBox;
};

export function toBody(raw: RawLandmark[], width: number, height: number): Body {
  if (raw.length < LANDMARK_COUNT) {
    throw new Error(`expected ${LANDMARK_COUNT} landmarks, got ${raw.length}`);
  }
  const lm = (j: Joint) => raw[JOINT_INDEX[j]];
  const point = (j: Joint): Point => ({ x: lm(j).x * width, y: lm(j).y * height });
  const visibility = (j: Joint) => lm(j).visibility ?? 0;
  const inFrame = (j: Joint) => {
    const { x, y } = lm(j);
    return x >= EDGE_MARGIN && x <= 1 - EDGE_MARGIN && y >= EDGE_MARGIN && y <= 1 - EDGE_MARGIN;
  };
  const usable = (j: Joint) => visibility(j) >= MIN_VISIBILITY && inFrame(j);

  const shoulderMid = midpoint(point("leftShoulder"), point("rightShoulder"));
  const hipMid = midpoint(point("leftHip"), point("rightHip"));

  const pts = ALL_JOINTS.map(point);
  const bbox: BBox = {
    minX: Math.min(...pts.map((p) => p.x)),
    minY: Math.min(...pts.map((p) => p.y)),
    maxX: Math.max(...pts.map((p) => p.x)),
    maxY: Math.max(...pts.map((p) => p.y)),
  };

  return {
    width,
    height,
    point,
    visibility,
    usable,
    shoulderMid,
    hipMid,
    torsoLength: distance(shoulderMid, hipMid),
    shoulderWidth: distance(point("leftShoulder"), point("rightShoulder")),
    bbox,
  };
}
