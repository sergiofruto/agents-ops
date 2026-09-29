import type { Body } from "./body";
import { distance, midpoint } from "./geometry";
import { joint, other, type Joint } from "./landmarks";
import { kneeAngle, meanVisibility, standingSide } from "./poses/helpers";
import type { PoseId } from "./poses";

export const MIN_CONFIDENCE = 0.6;

export type Classification = { pose: PoseId | "unknown"; confidence: number };

type Rule = { pose: PoseId; joints: Joint[]; matches: (b: Body) => boolean };

const DOWNDOG: Rule = {
  pose: "downdog",
  joints: [
    "leftShoulder", "rightShoulder", "leftHip", "rightHip",
    "leftWrist", "rightWrist", "leftAnkle", "rightAnkle",
  ],
  matches: (b) => {
    const ankleMid = midpoint(b.point("leftAnkle"), b.point("rightAnkle"));
    const cut = b.bbox.maxY - 0.35 * (b.bbox.maxY - b.bbox.minY);
    const nearFloor = (["leftWrist", "rightWrist", "leftAnkle", "rightAnkle"] as Joint[]).every(
      (j) => b.point(j).y >= cut,
    );
    return b.hipMid.y < b.shoulderMid.y && b.hipMid.y < ankleMid.y && nearFloor;
  },
};

const TREE: Rule = {
  pose: "tree",
  joints: ["leftHip", "rightHip", "leftKnee", "rightKnee", "leftAnkle", "rightAnkle"],
  matches: (b) => {
    const s = standingSide(b);
    const standingAnkle = b.point(joint(s, "Ankle"));
    const raisedAnkle = b.point(joint(other(s), "Ankle"));
    const legLength = distance(b.point(joint(s, "Hip")), standingAnkle);
    return (
      Math.abs(standingAnkle.y - raisedAnkle.y) > 0.25 * legLength && kneeAngle(b, s) > 160
    );
  },
};

const WARRIOR2: Rule = {
  pose: "warrior2",
  joints: [
    "leftShoulder", "rightShoulder", "leftHip", "rightHip",
    "leftWrist", "rightWrist", "leftAnkle", "rightAnkle",
  ],
  matches: (b) => {
    const stance = Math.abs(b.point("leftAnkle").x - b.point("rightAnkle").x);
    const wristsAtShoulders = (["leftWrist", "rightWrist"] as Joint[]).every(
      (j) => Math.abs(b.point(j).y - b.shoulderMid.y) <= 0.15 * b.torsoLength,
    );
    return stance > 1.2 * b.shoulderWidth && wristsAtShoulders;
  },
};

/** Order matters: the first rule whose conditions all hold wins. */
const RULES: Rule[] = [DOWNDOG, TREE, WARRIOR2];

export function classify(b: Body): Classification {
  for (const rule of RULES) {
    if (!rule.matches(b)) continue;
    const confidence = meanVisibility(b, rule.joints);
    return confidence >= MIN_CONFIDENCE ? { pose: rule.pose, confidence } : { pose: "unknown", confidence };
  }
  return { pose: "unknown", confidence: 0 };
}
