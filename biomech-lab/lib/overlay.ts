import { toBody } from "./body";
import { ALL_JOINTS, type Joint, type RawLandmark } from "./landmarks";

export const BONES: [Joint, Joint][] = [
  ["leftShoulder", "rightShoulder"],
  ["leftShoulder", "leftElbow"],
  ["leftElbow", "leftWrist"],
  ["rightShoulder", "rightElbow"],
  ["rightElbow", "rightWrist"],
  ["leftShoulder", "leftHip"],
  ["rightShoulder", "rightHip"],
  ["leftHip", "rightHip"],
  ["leftHip", "leftKnee"],
  ["leftKnee", "leftAnkle"],
  ["rightHip", "rightKnee"],
  ["rightKnee", "rightAnkle"],
  ["leftAnkle", "leftHeel"],
  ["leftHeel", "leftFootIndex"],
  ["leftAnkle", "leftFootIndex"],
  ["rightAnkle", "rightHeel"],
  ["rightHeel", "rightFootIndex"],
  ["rightAnkle", "rightFootIndex"],
];

/** Joints drawn as dots (ears are omitted to keep the head uncluttered). */
export const OVERLAY_JOINTS: Joint[] = ALL_JOINTS.filter((j) => j !== "leftEar" && j !== "rightEar");

export type OverlayGeometry = {
  width: number;
  height: number;
  bones: { x1: number; y1: number; x2: number; y2: number }[];
  joints: { id: Joint; x: number; y: number }[];
};

/** Pixel-space skeleton geometry; only usable landmarks (visible, inside the frame) are drawn. */
export function overlayGeometry(raw: RawLandmark[], width: number, height: number): OverlayGeometry {
  const body = toBody(raw, width, height);
  const bones = BONES.filter(([a, b]) => body.usable(a) && body.usable(b)).map(([a, b]) => {
    const p = body.point(a);
    const q = body.point(b);
    return { x1: p.x, y1: p.y, x2: q.x, y2: q.y };
  });
  const joints = OVERLAY_JOINTS.filter((j) => body.usable(j)).map((j) => ({ id: j, ...body.point(j) }));
  return { width, height, bones, joints };
}
