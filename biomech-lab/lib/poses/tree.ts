import { distance, tiltFromHorizontal, tiltFromVertical } from "@/lib/geometry";
import { joint, other } from "@/lib/landmarks";
import { CORE_JOINTS } from "@/lib/view";
import { kneeAngle, legJoints, standingSide } from "./helpers";
import type { PoseDef } from "./types";

export const tree: PoseDef = {
  id: "tree",
  label: "Tree",
  view: "front",
  assignRoles: (b) => {
    const standing = standingSide(b);
    return { standing, raised: other(standing) };
  },
  checks: [
    {
      id: "standingLeg",
      label: "Standing leg straight",
      cue: "Straighten your standing leg without locking the knee.",
      unit: "deg",
      weight: 25,
      bounds: [0, 180],
      kind: "range",
      target: 180,
      tol: 8,
      source: "frame",
      required: (r) => legJoints(r.standing),
      measure: (b, r) => kneeAngle(b, r.standing),
    },
    {
      id: "footOffKnee",
      label: "Foot off the knee",
      cue: "Place your foot above or below the knee, never on it.",
      unit: "ratio",
      weight: 20,
      bounds: [0, 5],
      kind: "min",
      min: 0.15,
      source: "frame",
      required: (r) => [
        joint(r.raised, "Heel"),
        joint(r.raised, "Ankle"),
        joint(r.raised, "FootIndex"),
        joint(r.standing, "Knee"),
        joint(r.standing, "Ankle"),
      ],
      // Vertical gap between the standing knee and the raised foot's heel–toe span,
      // in shin lengths. 0 when any part of the foot overlaps the knee.
      measure: (b, r) => {
        const knee = b.point(joint(r.standing, "Knee"));
        const shin = distance(knee, b.point(joint(r.standing, "Ankle")));
        const ys = (["Heel", "Ankle", "FootIndex"] as const).map(
          (p) => b.point(joint(r.raised, p)).y,
        );
        const top = Math.min(...ys);
        const bottom = Math.max(...ys);
        const clearance = knee.y < top ? top - knee.y : knee.y > bottom ? knee.y - bottom : 0;
        return clearance / shin;
      },
    },
    {
      id: "hipsLevel",
      label: "Hips level",
      cue: "Level your hips.",
      unit: "deg",
      weight: 20,
      bounds: [0, 90],
      kind: "range",
      target: 0,
      tol: 6,
      source: "frame",
      required: () => ["leftHip", "rightHip"],
      measure: (b) => tiltFromHorizontal(b.point("leftHip"), b.point("rightHip")),
    },
    {
      id: "torsoUpright",
      label: "Torso upright",
      cue: "Lengthen your spine and keep your torso over your hips.",
      unit: "deg",
      weight: 15,
      bounds: [0, 90],
      kind: "range",
      target: 0,
      tol: 8,
      source: "frame",
      required: () => CORE_JOINTS,
      measure: (b) => tiltFromVertical(b.hipMid, b.shoulderMid),
    },
    {
      id: "stability",
      label: "Stability",
      cue: "Fix your gaze on one point and steady your balance.",
      unit: "ratio",
      weight: 20,
      bounds: [0, 5],
      kind: "range",
      target: 0,
      tol: 0.02,
      source: "window",
      required: () => ["leftHip", "rightHip"],
    },
  ],
};
