/** Posture check thresholds and constants. All thresholds are provisional (see docs/posture-check-design.md). */

export type FindingId =
  | "forwardHead"
  | "headTilt"
  | "shoulderLevel"
  | "trunkShift"
  | "hipLevel"
  | "hipsForward"
  | "kneeHyperextension"
  | "heelAlignment";

export type Region = "headNeck" | "shoulders" | "trunkHips" | "kneesFeet";

export type FindingDef = {
  label: string;
  region: Region;
  unit: "cm" | "deg";
  weight: number;
  /** |value| <= aligned → aligned; <= slight → slight; else needs work. */
  aligned: number;
  slight: number;
  /** One-sided findings only count in the positive direction; value <= 0 is aligned. */
  oneSided: boolean;
};

export const FINDINGS: Record<FindingId, FindingDef> = {
  forwardHead: { label: "Forward head", region: "headNeck", unit: "cm", weight: 20, aligned: 2.5, slight: 5, oneSided: true },
  headTilt: { label: "Head tilt", region: "headNeck", unit: "deg", weight: 10, aligned: 2, slight: 5, oneSided: false },
  shoulderLevel: { label: "Shoulder level", region: "shoulders", unit: "deg", weight: 15, aligned: 2, slight: 4, oneSided: false },
  trunkShift: { label: "Trunk shift", region: "trunkHips", unit: "cm", weight: 15, aligned: 1.5, slight: 3, oneSided: false },
  hipLevel: { label: "Hip level", region: "trunkHips", unit: "deg", weight: 15, aligned: 2, slight: 4, oneSided: false },
  hipsForward: { label: "Hips forward", region: "trunkHips", unit: "cm", weight: 10, aligned: 3, slight: 6, oneSided: true },
  kneeHyperextension: { label: "Knee hyperextension", region: "kneesFeet", unit: "deg", weight: 10, aligned: 5, slight: 10, oneSided: true },
  heelAlignment: { label: "Heel alignment", region: "kneesFeet", unit: "deg", weight: 5, aligned: 5, slight: 10, oneSided: false },
};

export const REGION_ORDER: Region[] = ["headNeck", "shoulders", "trunkHips", "kneesFeet"];

export const REGION_LABEL: Record<Region, string> = {
  headNeck: "Head & neck",
  shoulders: "Shoulders",
  trunkHips: "Trunk & hips",
  kneesFeet: "Knees & feet",
};

/** Photos are downscaled to this long side before detection. */
export const MAX_SIDE_PX = 1280;
/** Average ear (tragion) height as a fraction of standing height. */
export const TRAGION_RATIO = 0.936;
export const HEIGHT_MIN_CM = 120;
export const HEIGHT_MAX_CM = 220;
/** Heel→ankle segments shorter than this (px) can't support a heel angle; 1 px of error ≈ 1°. */
export const HEEL_MIN_SEGMENT_PX = 60;
/** Ear-to-floor span (px) below which tilts and offsets fall under landmark noise. */
export const MIN_EAR_TO_FLOOR_PX = 500;
