import { angle, distanceToLine } from "@/lib/geometry";
import { joint } from "@/lib/landmarks";
import { CORE_JOINTS } from "@/lib/view";
import { kneeAngle, legJoints, nearSide } from "./helpers";
import type { PoseDef } from "./types";

export const downdog: PoseDef = {
  id: "downdog",
  label: "Downward Dog",
  view: "side",
  assignRoles: (b) => ({ near: nearSide(b) }),
  checks: [
    {
      id: "armsStraight",
      label: "Arms straight",
      cue: "Straighten your arms and press the floor away.",
      unit: "deg",
      weight: 20,
      bounds: [0, 180],
      kind: "range",
      target: 180,
      tol: 10,
      source: "frame",
      required: (r) => [joint(r.near, "Shoulder"), joint(r.near, "Elbow"), joint(r.near, "Wrist")],
      measure: (b, r) =>
        angle(
          b.point(joint(r.near, "Shoulder")),
          b.point(joint(r.near, "Elbow")),
          b.point(joint(r.near, "Wrist")),
        ),
    },
    {
      id: "legsStraight",
      label: "Legs straight",
      cue: "Straighten your legs as far as is comfortable.",
      unit: "deg",
      weight: 20,
      bounds: [0, 180],
      kind: "range",
      target: 180,
      tol: 15,
      source: "frame",
      required: (r) => legJoints(r.near),
      measure: (b, r) => kneeAngle(b, r.near),
    },
    {
      id: "hipAngle",
      label: "Hip angle (inverted V)",
      cue: "Lift your hips up and back to form an inverted V.",
      unit: "deg",
      weight: 25,
      bounds: [0, 180],
      kind: "range",
      target: 80,
      tol: 15,
      source: "frame",
      required: (r) => [joint(r.near, "Shoulder"), joint(r.near, "Hip"), joint(r.near, "Ankle")],
      measure: (b, r) =>
        angle(
          b.point(joint(r.near, "Shoulder")),
          b.point(joint(r.near, "Hip")),
          b.point(joint(r.near, "Ankle")),
        ),
    },
    {
      id: "flatBack",
      label: "Long, flat back",
      cue: "Press your chest toward your thighs to lengthen your back.",
      unit: "deg",
      weight: 25,
      bounds: [0, 180],
      kind: "range",
      target: 180,
      tol: 12,
      source: "frame",
      required: (r) => [joint(r.near, "Wrist"), joint(r.near, "Shoulder"), joint(r.near, "Hip")],
      measure: (b, r) =>
        angle(
          b.point(joint(r.near, "Wrist")),
          b.point(joint(r.near, "Shoulder")),
          b.point(joint(r.near, "Hip")),
        ),
    },
    {
      id: "headAligned",
      label: "Head between arms",
      cue: "Let your head hang in line with your arms.",
      unit: "ratio",
      weight: 10,
      bounds: [0, 5],
      kind: "range",
      target: 0,
      tol: 0.1,
      source: "frame",
      required: (r) => [
        joint(r.near, "Ear"),
        joint(r.near, "Shoulder"),
        joint(r.near, "Wrist"),
        ...CORE_JOINTS,
      ],
      measure: (b, r) =>
        distanceToLine(
          b.point(joint(r.near, "Ear")),
          b.point(joint(r.near, "Shoulder")),
          b.point(joint(r.near, "Wrist")),
        ) / b.torsoLength,
    },
  ],
};
