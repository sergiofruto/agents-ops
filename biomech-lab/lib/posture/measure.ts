import { angle, tiltFromHorizontal, tiltFromVertical, type Point } from "@/lib/geometry";
import { joint, type Joint } from "@/lib/landmarks";
import { nearSide } from "@/lib/poses/helpers";
import { anatomicalRight, facing, type PostureFrame } from "./frame";

export type CoronalMeasures = {
  /** Degrees, + = client's right ear lower. */
  headTilt: number | null;
  /** Degrees, + = client's right shoulder lower. */
  shoulderLevel: number | null;
  shoulderDropCm: number | null;
  /** Degrees, + = client's right hip lower. */
  hipLevel: number | null;
  hipDropCm: number | null;
  /** Cm, + = shoulders shifted to the client's right of the hips. */
  trunkShift: number | null;
  /** Back view only: the worse heel→ankle tilt from vertical, unsigned. */
  heelAlignment: { deg: number; side: "right" | "left" } | null;
};

export type SagittalMeasures = {
  /** Cm, + = ear ahead of the shoulder. */
  forwardHead: number | null;
  /** Degrees of the ear-shoulder line from horizontal; info only (approximates CVA). */
  earShoulderAngle: number | null;
  /** Cm, + = hip ahead of the ankle. */
  hipsForward: number | null;
  /** 180 − hip-knee-ankle angle, + when the knee sits behind the hip-ankle line. */
  kneeHyperextension: number | null;
};

const DEG = 180 / Math.PI;

function pair(frame: PostureFrame, a: Joint, b: Joint) {
  const { body } = frame;
  if (!body.usable(a) || !body.usable(b) || frame.view === "side") return null;
  return anatomicalRight(frame.view, body.point(a), body.point(b));
}

/** Signed tilt of the right→left line, + when the client's right point is lower (larger y). */
function signedTilt(p: { right: Point; left: Point }): number {
  return Math.atan2(p.right.y - p.left.y, Math.abs(p.right.x - p.left.x)) * DEG;
}

const toCm = (frame: PostureFrame, px: number) => (frame.cmPerPx === null ? null : px * frame.cmPerPx);

export function measureCoronal(frame: PostureFrame): CoronalMeasures {
  const ears = pair(frame, "leftEar", "rightEar");
  const shoulders = pair(frame, "leftShoulder", "rightShoulder");
  const hips = pair(frame, "leftHip", "rightHip");

  let trunkShift: number | null = null;
  if (shoulders && hips) {
    const dx = (shoulders.right.x + shoulders.left.x) / 2 - (hips.right.x + hips.left.x) / 2;
    // Front: the client's right is image-left, so a shift toward image-right is toward their left.
    trunkShift = toCm(frame, frame.view === "front" ? -dx : dx);
  }

  let heelAlignment: CoronalMeasures["heelAlignment"] = null;
  if (frame.view === "back") {
    const { body } = frame;
    const tilts: { deg: number; x: number }[] = [];
    for (const s of ["left", "right"] as const) {
      const heel = joint(s, "Heel");
      const ankle = joint(s, "Ankle");
      if (body.usable(heel) && body.usable(ankle)) {
        tilts.push({ deg: tiltFromVertical(body.point(heel), body.point(ankle)), x: body.point(ankle).x });
      }
    }
    if (tilts.length > 0) {
      const worst = tilts.reduce((a, b) => (b.deg > a.deg ? b : a));
      // Back view: the client's right is image-right of the hip midpoint.
      heelAlignment = { deg: worst.deg, side: worst.x >= body.hipMid.x ? "right" : "left" };
    }
  }

  return {
    headTilt: ears ? signedTilt(ears) : null,
    shoulderLevel: shoulders ? signedTilt(shoulders) : null,
    shoulderDropCm: shoulders ? toCm(frame, shoulders.right.y - shoulders.left.y) : null,
    hipLevel: hips ? signedTilt(hips) : null,
    hipDropCm: hips ? toCm(frame, hips.right.y - hips.left.y) : null,
    trunkShift,
    heelAlignment,
  };
}

export function measureSagittal(frame: PostureFrame): SagittalMeasures {
  const { body } = frame;
  const s = nearSide(body);
  const f = facing(body);
  const get = (part: "Ear" | "Shoulder" | "Hip" | "Knee" | "Ankle") => {
    const j = joint(s, part);
    return body.usable(j) ? body.point(j) : null;
  };
  const ear = get("Ear");
  const shoulder = get("Shoulder");
  const hip = get("Hip");
  const knee = get("Knee");
  const ankle = get("Ankle");

  const ahead = (a: Point | null, b: Point | null) =>
    a && b && f !== null ? toCm(frame, (a.x - b.x) * f) : null;

  let kneeHyperextension: number | null = null;
  if (hip && knee && ankle && f !== null) {
    const bend = 180 - angle(hip, knee, ankle);
    const t = (knee.y - hip.y) / (ankle.y - hip.y);
    const lineX = hip.x + t * (ankle.x - hip.x);
    const behind = (knee.x - lineX) * f < 0;
    kneeHyperextension = Number.isFinite(bend) ? (behind ? bend : -bend) : null;
  }

  return {
    forwardHead: ahead(ear, shoulder),
    earShoulderAngle: ear && shoulder ? tiltFromHorizontal(shoulder, ear) : null,
    hipsForward: ahead(hip, ankle),
    kneeHyperextension,
  };
}
