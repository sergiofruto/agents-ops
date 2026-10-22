import { describe, expect, test } from "vitest";
import { toBody } from "@/lib/body";
import { FINDINGS } from "@/lib/posture/config";
import { anatomicalRight, earToFloorPx, faceVisibility, facing, makeFrame } from "@/lib/posture/frame";
import { H, W, mirror, occlude, rawFromPixels, type PxSpec } from "./helpers/synthetic";

const FRONT: PxSpec = {
  nose: [800, 120],
  leftEye: [790, 112],
  rightEye: [810, 112],
  leftEar: [780, 100],
  rightEar: [820, 100],
  leftShoulder: [880, 200],
  rightShoulder: [720, 200],
  leftHip: [860, 480],
  rightHip: [740, 480],
  leftKnee: [855, 700],
  rightKnee: [745, 700],
  leftAnkle: [850, 1000],
  rightAnkle: [750, 1000],
  leftHeel: [850, 1036],
  rightHeel: [750, 1036],
};

const body = (spec: PxSpec) => toBody(rawFromPixels(spec, { width: W, height: 1200 }), W, 1200);

describe("posture config", () => {
  test("weights sum to 100", () => {
    expect(Object.values(FINDINGS).reduce((s, f) => s + f.weight, 0)).toBe(100);
  });
});

describe("posture frame", () => {
  test("earToFloorPx uses mean ear y to mean heel y", () => {
    expect(earToFloorPx(body(FRONT))).toBeCloseTo(936, 6);
    expect(makeFrame("front", body(FRONT), 180).cmPerPx).toBeCloseTo((180 * 0.936) / 936, 9);
  });

  test("earToFloorPx falls back to ankles when heels are unusable", () => {
    const raw = occlude(rawFromPixels(FRONT, { width: W, height: 1200 }), ["leftHeel", "rightHeel"]);
    expect(earToFloorPx(toBody(raw, W, 1200))).toBeCloseTo(900, 6);
  });

  test("no usable heels or ankles gives no scale", () => {
    const raw = occlude(rawFromPixels(FRONT, { width: W, height: 1200 }), [
      "leftHeel", "rightHeel", "leftAnkle", "rightAnkle",
    ]);
    const b = toBody(raw, W, 1200);
    expect(earToFloorPx(b)).toBeNull();
    expect(makeFrame("front", b, 180).cmPerPx).toBeNull();
  });

  test("anatomicalRight: front picks the smaller x as right, back the larger x", () => {
    const a = { x: 100, y: 0 };
    const b = { x: 300, y: 0 };
    expect(anatomicalRight("front", a, b).right).toBe(a);
    expect(anatomicalRight("front", b, a).right).toBe(a);
    expect(anatomicalRight("back", a, b).right).toBe(b);
    expect(anatomicalRight("back", a, b).left).toBe(a);
  });

  test("facing follows the nose relative to the near ear", () => {
    const side: PxSpec = { nose: [600, 120], leftEar: [560, 110, 0.9], rightEar: [560, 110, 0.1] };
    const raw = rawFromPixels(side, { width: W, height: H });
    expect(facing(toBody(raw, W, H))).toBe(1);
    expect(facing(toBody(mirror(raw), W, H))).toBe(-1);
    expect(facing(toBody(occlude(raw, ["nose"]), W, H))).toBeNull();
  });

  test("faceVisibility averages nose and eyes", () => {
    const raw = rawFromPixels({ nose: [800, 120, 0.9], leftEye: [790, 112, 0.6], rightEye: [810, 112, 0.3] });
    expect(faceVisibility(toBody(raw, W, H))).toBeCloseTo(0.6, 9);
  });
});
