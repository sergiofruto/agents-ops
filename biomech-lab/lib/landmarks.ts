export type RawLandmark = { x: number; y: number; z?: number; visibility?: number };

/** MediaPipe Pose landmark indices for the joints Biomech Lab uses. */
export const JOINT_INDEX = {
  nose: 0,
  leftEar: 7,
  rightEar: 8,
  leftShoulder: 11,
  rightShoulder: 12,
  leftElbow: 13,
  rightElbow: 14,
  leftWrist: 15,
  rightWrist: 16,
  leftHip: 23,
  rightHip: 24,
  leftKnee: 25,
  rightKnee: 26,
  leftAnkle: 27,
  rightAnkle: 28,
} as const;

export const LANDMARK_COUNT = 33;

export type Joint = keyof typeof JOINT_INDEX;
export type Side = "left" | "right";
export type Part = "Ear" | "Shoulder" | "Elbow" | "Wrist" | "Hip" | "Knee" | "Ankle";

export const ALL_JOINTS = Object.keys(JOINT_INDEX) as Joint[];

export function joint(side: Side, part: Part): Joint {
  return `${side}${part}` as Joint;
}

export function other(side: Side): Side {
  return side === "left" ? "right" : "left";
}

export function sideOf(j: Joint): Side | null {
  if (j.startsWith("left")) return "left";
  if (j.startsWith("right")) return "right";
  return null;
}

export function partOf(j: Joint): Part | null {
  const side = sideOf(j);
  return side ? (j.slice(side.length) as Part) : null;
}
