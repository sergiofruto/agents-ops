import {
  JOINT_INDEX,
  LANDMARK_COUNT,
  type Joint,
  type RawLandmark,
} from "@/lib/landmarks";

export const W = 1600;
export const H = 900;

/** [x, y] in pixels, optionally [x, y, visibility]. */
export type PxSpec = Partial<Record<Joint, [number, number] | [number, number, number]>>;

export function rawFromPixels(
  spec: PxSpec,
  opts: { width?: number; height?: number; visibility?: number } = {},
): RawLandmark[] {
  const width = opts.width ?? W;
  const height = opts.height ?? H;
  const raw: RawLandmark[] = Array.from({ length: LANDMARK_COUNT }, () => ({
    x: 0.5,
    y: 0.5,
    z: 0,
    visibility: 0,
  }));
  for (const [j, p] of Object.entries(spec) as [Joint, number[]][]) {
    raw[JOINT_INDEX[j]] = {
      x: p[0] / width,
      y: p[1] / height,
      z: 0,
      visibility: p[2] ?? opts.visibility ?? 1,
    };
  }
  return raw;
}

/** Horizontal flip (x → 1 − x) with left/right labels swapped, like a selfie-mirrored input. */
export function mirror(raw: RawLandmark[]): RawLandmark[] {
  const out = raw.map((l) => ({ ...l, x: 1 - l.x }));
  for (const j of Object.keys(JOINT_INDEX) as Joint[]) {
    if (!j.startsWith("left")) continue;
    const r = `right${j.slice(4)}` as Joint;
    const li = JOINT_INDEX[j];
    const ri = JOINT_INDEX[r];
    [out[li], out[ri]] = [out[ri], out[li]];
  }
  return out;
}

export function occlude(raw: RawLandmark[], joints: Joint[]): RawLandmark[] {
  const out = raw.map((l) => ({ ...l }));
  for (const j of joints) out[JOINT_INDEX[j]].visibility = 0;
  return out;
}

/** Shrinks (f < 1) or grows (f > 1) the figure around the image center. */
export function scaleAbout(raw: RawLandmark[], f: number): RawLandmark[] {
  return raw.map((l) => ({ ...l, x: 0.5 + (l.x - 0.5) * f, y: 0.5 + (l.y - 0.5) * f }));
}

const HEAD_FRONT: PxSpec = {
  nose: [800, 240],
  leftEar: [780, 230],
  rightEar: [820, 230],
};

const TORSO_FRONT: PxSpec = {
  leftShoulder: [720, 300],
  rightShoulder: [880, 300],
  leftHip: [740, 480],
  rightHip: [860, 480],
};

/** Facing the camera; front leg = left (knee 90°, knee over ankle); back leg straight; arms level. */
export const WARRIOR2_PX: PxSpec = {
  ...HEAD_FRONT,
  ...TORSO_FRONT,
  leftElbow: [600, 300],
  leftWrist: [480, 300],
  rightElbow: [1000, 300],
  rightWrist: [1120, 300],
  leftKnee: [580, 480],
  leftAnkle: [580, 700],
  rightKnee: [960, 590],
  rightAnkle: [1060, 700],
};

/** Same, but the front knee opens to 105° and the knee drifts 0.316 torso-lengths past the ankle. */
export const WARRIOR2_105_PX: PxSpec = {
  ...WARRIOR2_PX,
  leftAnkle: [523.06, 692.5],
};

/** Facing the camera; standing leg = right; left foot on the inner thigh above the knee; hands overhead. */
export const TREE_PX: PxSpec = {
  ...HEAD_FRONT,
  ...TORSO_FRONT,
  leftElbow: [740, 200],
  leftWrist: [790, 120],
  rightElbow: [860, 200],
  rightWrist: [810, 120],
  leftKnee: [640, 580],
  leftAnkle: [840, 560],
  rightKnee: [860, 620],
  rightAnkle: [860, 760],
  leftHeel: [845, 550],
  leftFootIndex: [835, 590],
  rightHeel: [855, 770],
  rightFootIndex: [890, 775],
};

/** Tree with the raised foot pressed on the standing knee: heel–toe span 590..640 straddles the knee (y 620). */
export const TREE_FOOT_ON_KNEE_PX: PxSpec = {
  ...TREE_PX,
  leftAnkle: [845, 600],
  leftHeel: [850, 590],
  leftFootIndex: [840, 640],
};

/** Side view facing image-left; near side = left (visibility 1); far side offset 15 px, visibility 0.6. */
export const DOWNDOG_PX: PxSpec = {
  nose: [490, 680],
  leftEar: [505, 660],
  rightEar: [520, 660, 0.6],
  leftShoulder: [550, 600],
  rightShoulder: [565, 600, 0.6],
  leftElbow: [475, 700],
  rightElbow: [490, 700, 0.6],
  leftWrist: [400, 800],
  rightWrist: [415, 800, 0.6],
  leftHip: [775, 300],
  rightHip: [790, 300, 0.6],
  leftKnee: [946, 482.5],
  rightKnee: [961, 482.5, 0.6],
  leftAnkle: [1117, 665],
  rightAnkle: [1132, 665, 0.6],
};

/** Standing neutrally, arms down — matches no supported pose. */
export const NEUTRAL_PX: PxSpec = {
  ...HEAD_FRONT,
  ...TORSO_FRONT,
  leftElbow: [710, 400],
  leftWrist: [705, 490],
  rightElbow: [890, 400],
  rightWrist: [895, 490],
  leftKnee: [745, 620],
  leftAnkle: [750, 760],
  rightKnee: [855, 620],
  rightAnkle: [850, 760],
};
