import { tiltFromHorizontal, tiltFromVertical } from "@/lib/geometry";
import { joint, other } from "@/lib/landmarks";
import { CORE_JOINTS } from "@/lib/view";
import { frontSide, kneeAngle, legJoints } from "./helpers";
import type { PoseDef } from "./types";

export const warrior2: PoseDef = {
  id: "warrior2",
  label: "Warrior II",
  view: "front",
  assignRoles: (b) => {
    const front = frontSide(b);
    return { front, back: other(front) };
  },
  checks: [
    {
      id: "frontKneeBend",
      label: "Front knee bend",
      cue: "Bend your front knee toward a right angle.",
      unit: "deg",
      weight: 30,
      bounds: [0, 180],
      kind: "range",
      target: 90,
      tol: 10,
      source: "frame",
      required: (r) => legJoints(r.front),
      measure: (b, r) => kneeAngle(b, r.front),
    },
    {
      id: "kneeOverAnkle",
      label: "Front knee over ankle",
      cue: "Stack your front knee directly over your ankle.",
      unit: "ratio",
      weight: 20,
      bounds: [0, 5],
      kind: "range",
      target: 0,
      tol: 0.1,
      source: "frame",
      required: (r) => [joint(r.front, "Knee"), joint(r.front, "Ankle"), ...CORE_JOINTS],
      measure: (b, r) =>
        Math.abs(b.point(joint(r.front, "Knee")).x - b.point(joint(r.front, "Ankle")).x) /
        b.torsoLength,
    },
    {
      id: "backLegStraight",
      label: "Back leg straight",
      cue: "Straighten your back leg.",
      unit: "deg",
      weight: 15,
      bounds: [0, 180],
      kind: "range",
      target: 180,
      tol: 10,
      source: "frame",
      required: (r) => legJoints(r.back),
      measure: (b, r) => kneeAngle(b, r.back),
    },
    {
      id: "armsLevel",
      label: "Arms level",
      cue: "Level your arms at shoulder height.",
      unit: "deg",
      weight: 20,
      bounds: [0, 90],
      kind: "range",
      target: 0,
      tol: 10,
      source: "frame",
      required: () => ["leftWrist", "rightWrist"],
      measure: (b) => tiltFromHorizontal(b.point("leftWrist"), b.point("rightWrist")),
    },
    {
      id: "torsoUpright",
      label: "Torso upright",
      cue: "Keep your torso upright, centered over your hips.",
      unit: "deg",
      weight: 15,
      bounds: [0, 90],
      kind: "range",
      target: 0,
      tol: 10,
      source: "frame",
      required: () => CORE_JOINTS,
      measure: (b) => tiltFromVertical(b.hipMid, b.shoulderMid),
    },
  ],
};
