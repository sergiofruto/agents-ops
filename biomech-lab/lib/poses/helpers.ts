import type { Body } from "@/lib/body";
import { angle } from "@/lib/geometry";
import { joint, type Joint, type Part, type Side } from "@/lib/landmarks";

export function legJoints(side: Side): Joint[] {
  return [joint(side, "Hip"), joint(side, "Knee"), joint(side, "Ankle")];
}

export function kneeAngle(b: Body, side: Side): number {
  return angle(
    b.point(joint(side, "Hip")),
    b.point(joint(side, "Knee")),
    b.point(joint(side, "Ankle")),
  );
}

export function meanVisibility(b: Body, joints: Joint[]): number {
  return joints.reduce((sum, j) => sum + b.visibility(j), 0) / joints.length;
}

/** Warrior II: the front leg is the more bent one. */
export function frontSide(b: Body): Side {
  return kneeAngle(b, "left") <= kneeAngle(b, "right") ? "left" : "right";
}

/** Tree: the standing leg's ankle is the lower one (larger y). */
export function standingSide(b: Body): Side {
  return b.point("leftAnkle").y >= b.point("rightAnkle").y ? "left" : "right";
}

const SIDE_PARTS: Part[] = ["Ear", "Shoulder", "Elbow", "Wrist", "Hip", "Knee", "Ankle"];

/** Side views: the near side is the one MediaPipe sees more clearly. */
export function nearSide(b: Body): Side {
  const vis = (s: Side) => meanVisibility(b, SIDE_PARTS.map((p) => joint(s, p)));
  return vis("left") >= vis("right") ? "left" : "right";
}
