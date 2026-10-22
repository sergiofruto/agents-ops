import type { Body } from "@/lib/body";
import type { Point } from "@/lib/geometry";
import { joint, type Joint } from "@/lib/landmarks";
import { nearSide } from "@/lib/poses/helpers";
import { TRAGION_RATIO } from "./config";

export type PostureView = "front" | "side" | "back";

/** One accepted photo: its body and the pixel-to-cm scale from the client's height (null if unknown). */
export type PostureFrame = { view: PostureView; body: Body; cmPerPx: number | null };

function meanY(body: Body, joints: Joint[]): number | null {
  const usable = joints.filter((j) => body.usable(j));
  if (usable.length === 0) return null;
  return usable.reduce((s, j) => s + body.point(j).y, 0) / usable.length;
}

/** Vertical pixels from the ears to the floor (heels, or ankles when heels aren't usable). */
export function earToFloorPx(body: Body): number | null {
  const ear = meanY(body, ["leftEar", "rightEar"]);
  const floor = meanY(body, ["leftHeel", "rightHeel"]) ?? meanY(body, ["leftAnkle", "rightAnkle"]);
  if (ear === null || floor === null || floor <= ear) return null;
  return floor - ear;
}

export function makeFrame(view: PostureView, body: Body, heightCm: number): PostureFrame {
  const px = earToFloorPx(body);
  return { view, body, cmPerPx: px === null ? null : (heightCm * TRAGION_RATIO) / px };
}

/**
 * Assigns the client's anatomical sides by image position (MediaPipe's labels assume a
 * person facing the camera). Front: the client's right is image-left. Back: image-right.
 */
export function anatomicalRight(view: "front" | "back", a: Point, b: Point): { right: Point; left: Point } {
  const [lo, hi] = a.x <= b.x ? [a, b] : [b, a];
  return view === "front" ? { right: lo, left: hi } : { right: hi, left: lo };
}

/** Which way a side-view person faces: +1 toward image right, -1 toward image left. */
export function facing(body: Body): 1 | -1 | null {
  const ear = joint(nearSide(body), "Ear");
  if (!body.usable("nose") || !body.usable(ear)) return null;
  const dx = body.point("nose").x - body.point(ear).x;
  return dx > 0 ? 1 : dx < 0 ? -1 : null;
}

/**
 * Whether the person faces the camera (front photo) or turns their back (back photo).
 * Shape alone can't tell, and MediaPipe reports the face as visible either way, so two
 * signals vote: MediaPipe's left/right labels (the left shoulder sits image-right when
 * facing the camera) and depth (the nose is closer to the camera than the ears).
 * Returns null when the signals disagree or neither is available.
 */
export function facesCamera(body: Body): boolean | null {
  const votes: boolean[] = [];
  if (body.usable("leftShoulder") && body.usable("rightShoulder")) {
    const dx = body.point("leftShoulder").x - body.point("rightShoulder").x;
    if (dx !== 0) votes.push(dx > 0);
  }
  if (body.usable("nose") && body.usable("leftEar") && body.usable("rightEar")) {
    const dz = body.depth("nose") - (body.depth("leftEar") + body.depth("rightEar")) / 2;
    if (dz !== 0) votes.push(dz < 0);
  }
  if (votes.length === 0 || votes.some((v) => v !== votes[0])) return null;
  return votes[0];
}
