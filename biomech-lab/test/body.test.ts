import { describe, expect, test } from "vitest";
import { toBody } from "@/lib/body";
import { angle } from "@/lib/geometry";
import { JOINT_INDEX } from "@/lib/landmarks";
import { H, W, WARRIOR2_105_PX, WARRIOR2_PX, rawFromPixels } from "./helpers/synthetic";

describe("toBody", () => {
  test("converts normalized landmarks to pixel space", () => {
    const body = toBody(rawFromPixels(WARRIOR2_PX), W, H);
    expect(body.point("leftShoulder").x).toBeCloseTo(720, 6);
    expect(body.point("leftShoulder").y).toBeCloseTo(300, 6);
  });

  test("angles are measured in pixel space, not distorted by aspect ratio", () => {
    const raw = rawFromPixels(WARRIOR2_105_PX);
    const body = toBody(raw, W, H);
    const pixelAngle = angle(body.point("leftHip"), body.point("leftKnee"), body.point("leftAnkle"));
    expect(pixelAngle).toBeCloseTo(105, 1);

    const n = (j: keyof typeof JOINT_INDEX) => raw[JOINT_INDEX[j]];
    const naiveAngle = angle(n("leftHip"), n("leftKnee"), n("leftAnkle"));
    expect(Math.abs(naiveAngle - 105)).toBeGreaterThan(1);
  });

  test("derived lengths", () => {
    const body = toBody(rawFromPixels(WARRIOR2_PX), W, H);
    expect(body.shoulderWidth).toBeCloseTo(160, 6);
    expect(body.torsoLength).toBeCloseTo(180, 6);
    expect(body.shoulderMid).toEqual({ x: 800, y: 300 });
    expect(body.hipMid).toEqual({ x: 800, y: 480 });
  });

  test("bounding box covers the tracked joints", () => {
    const body = toBody(rawFromPixels(WARRIOR2_PX), W, H);
    expect(body.bbox.minX).toBeCloseTo(480, 6);
    expect(body.bbox.maxX).toBeCloseTo(1120, 6);
    expect(body.bbox.minY).toBeCloseTo(230, 6);
    expect(body.bbox.maxY).toBeCloseTo(700, 6);
  });

  test("usable requires visibility >= 0.5 and 2% edge margin", () => {
    const body = toBody(
      rawFromPixels({
        ...WARRIOR2_PX,
        leftWrist: [480, 300, 0.4],
        rightWrist: [10, 300],
        leftElbow: [600, 300, 0.5],
      }),
      W,
      H,
    );
    expect(body.usable("leftWrist")).toBe(false);
    expect(body.usable("rightWrist")).toBe(false);
    expect(body.usable("leftElbow")).toBe(true);
    expect(body.usable("leftShoulder")).toBe(true);
  });

  test("throws on incomplete landmark arrays", () => {
    expect(() => toBody([], W, H)).toThrow(/33 landmarks/);
  });
});
