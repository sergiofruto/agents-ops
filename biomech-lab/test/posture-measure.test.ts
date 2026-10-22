import { describe, expect, test } from "vitest";
import { toBody } from "@/lib/body";
import type { PostureFrame, PostureView } from "@/lib/posture/frame";
import { measureCoronal, measureSagittal } from "@/lib/posture/measure";
import { mirror, occlude, rawFromPixels, type PxSpec } from "./helpers/synthetic";

const W = 1600;
const HT = 1200;
const DEG = Math.PI / 180;

const frame = (view: PostureView, raw: ReturnType<typeof rawFromPixels>, cmPerPx = 0.2): PostureFrame => ({
  view,
  body: toBody(raw, W, HT),
  cmPerPx,
});
const px = (spec: PxSpec) => rawFromPixels(spec, { width: W, height: HT });

const CORONAL: PxSpec = {
  leftEar: [780, 100],
  rightEar: [820, 100],
  rightShoulder: [700, 210], // image-left, 10 px lower
  leftShoulder: [900, 200],
  rightHip: [740, 480],
  leftHip: [860, 480],
};

describe("measureCoronal", () => {
  test("shoulder level is signed by the client's side and flips between front and back", () => {
    const expected = Math.atan(10 / 200) / DEG;
    expect(measureCoronal(frame("front", px(CORONAL))).shoulderLevel).toBeCloseTo(expected, 6);
    expect(measureCoronal(frame("back", px(CORONAL))).shoulderLevel).toBeCloseTo(-expected, 6);
    expect(measureCoronal(frame("front", px(CORONAL))).shoulderDropCm).toBeCloseTo(2, 6);
  });

  test("trunk shift is in cm toward the client's right", () => {
    const spec: PxSpec = {
      ...CORONAL,
      rightShoulder: [720, 200],
      leftShoulder: [920, 200], // shoulder mid x 820, hip mid x 800
    };
    expect(measureCoronal(frame("front", px(spec))).trunkShift).toBeCloseTo(-4, 6);
    expect(measureCoronal(frame("back", px(spec))).trunkShift).toBeCloseTo(4, 6);
  });

  test("heel alignment reports the worse heel on the back view only", () => {
    const off = (deg: number) => 80 * Math.tan(deg * DEG);
    const spec: PxSpec = {
      ...CORONAL,
      leftAnkle: [740, 1000],
      leftHeel: [740 - off(3), 1080],
      rightAnkle: [860, 1000], // back view: client's right is image-right
      rightHeel: [860 + off(8), 1080],
    };
    const back = measureCoronal(frame("back", px(spec))).heelAlignment;
    expect(back?.deg).toBeCloseTo(8, 6);
    expect(back?.side).toBe("right");
    expect(measureCoronal(frame("front", px(spec))).heelAlignment).toBeNull();
  });

  test("heel segments too short to measure reliably are not measured", () => {
    const spec: PxSpec = {
      ...CORONAL,
      leftAnkle: [740, 1000],
      leftHeel: [745, 1030],
      rightAnkle: [860, 1000],
      rightHeel: [868, 1030],
    };
    expect(measureCoronal(frame("back", px(spec))).heelAlignment).toBeNull();
  });

  test("no cm scale leaves cm measures null but keeps degrees", () => {
    const m = measureCoronal({ ...frame("front", px(CORONAL)), cmPerPx: null });
    expect(m.trunkShift).toBeNull();
    expect(m.shoulderDropCm).toBeNull();
    expect(m.shoulderLevel).not.toBeNull();
  });
});

const KNEE_OFFSET = 250 * Math.tan(3 * DEG); // knee this far off the hip-ankle line = 6° at the knee

const side = (kneeDx: number): PxSpec => ({
  nose: [640, 120],
  leftEar: [600, 110],
  leftShoulder: [575, 200], // ear 25 px ahead
  leftHip: [615, 500], // hip 15 px ahead of the ankle
  leftKnee: [600 + kneeDx, 750],
  leftAnkle: [600, 1000],
  leftHeel: [585, 1030],
  rightEar: [600, 110, 0.1],
  rightShoulder: [575, 200, 0.1],
  rightHip: [615, 500, 0.1],
  rightKnee: [600, 750, 0.1],
  rightAnkle: [600, 1000, 0.1],
});

// Hip-ankle line runs from (615,500) to (600,1000); at the knee's y (750) it sits at x 607.5.
const sideKnee = (kneeDxFromLine: number) => side(7.5 + kneeDxFromLine);

describe("measureSagittal", () => {
  test("forward head and hips forward in cm, the same when the photo is mirrored", () => {
    const raw = px(sideKnee(0));
    for (const r of [raw, mirror(raw)]) {
      const m = measureSagittal(frame("side", r));
      expect(m.forwardHead).toBeCloseTo(5, 6);
      expect(m.hipsForward).toBeCloseTo(3, 6);
    }
  });

  test("knee hyperextension is positive behind the line, negative when bent, mirror-invariant", () => {
    const behind = px(sideKnee(-KNEE_OFFSET));
    const bent = px(sideKnee(KNEE_OFFSET));
    expect(measureSagittal(frame("side", behind)).kneeHyperextension).toBeCloseTo(6, 1);
    expect(measureSagittal(frame("side", mirror(behind))).kneeHyperextension).toBeCloseTo(6, 1);
    expect(measureSagittal(frame("side", bent)).kneeHyperextension).toBeCloseTo(-6, 1);
  });

  test("hips forward is measured from the midfoot, falling back to the ankle", () => {
    const spec: PxSpec = {
      ...sideKnee(0),
      leftHip: [645, 500],
      leftHeel: [580, 1030],
      leftFootIndex: [680, 1030], // midfoot x 630
    };
    expect(measureSagittal(frame("side", px(spec))).hipsForward).toBeCloseTo(3, 6);
    expect(measureSagittal(frame("side", mirror(px(spec)))).hipsForward).toBeCloseTo(3, 6);
    const noFoot = occlude(px(spec), ["leftHeel", "leftFootIndex"]);
    expect(measureSagittal(frame("side", noFoot)).hipsForward).toBeCloseTo(9, 6);
  });

  test("an unusable near ear leaves forward head unmeasured", () => {
    const raw = occlude(px(sideKnee(0)), ["leftEar"]);
    expect(measureSagittal(frame("side", raw)).forwardHead).toBeNull();
  });
});
