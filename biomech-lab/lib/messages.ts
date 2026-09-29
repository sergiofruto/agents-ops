import { partOf, type Joint, type Part } from "./landmarks";
import type { PoseDef } from "./poses";
import type { AssessmentReadiness, ReadinessReason } from "./readiness";

const PART_NAMES: Record<Part, string> = {
  Ear: "head",
  Shoulder: "shoulders",
  Elbow: "elbows",
  Wrist: "wrists",
  Hip: "hips",
  Knee: "knees",
  Ankle: "ankles",
};

function partList(joints: Joint[]): string {
  const names = [
    ...new Set(joints.map((j) => partOf(j)).filter((p): p is Part => p !== null).map((p) => PART_NAMES[p])),
  ];
  if (names.length === 0) return "body";
  if (names.length === 1) return names[0];
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

function message(reason: ReadinessReason, r: AssessmentReadiness, pose: PoseDef): string {
  switch (reason) {
    case "no_person":
      return "We couldn't find a person. Step back so your whole body is in frame.";
    case "multiple_people":
      return "Make sure you're alone in the frame.";
    case "wrong_view":
      return pose.view === "side"
        ? `Turn sideways to the camera for ${pose.label}.`
        : `Face the camera for ${pose.label}.`;
    case "bad_framing":
      return "Step back so your whole body is in frame.";
    case "low_coverage":
      return `We can't clearly see your ${partList(r.missing)}. Adjust your position or lighting.`;
  }
}

export function readinessMessages(r: AssessmentReadiness, pose: PoseDef): string[] {
  return [...new Set(r.reasons.map((reason) => message(reason, r, pose)))];
}
