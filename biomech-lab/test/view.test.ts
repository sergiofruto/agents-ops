import { describe, expect, test } from "vitest";
import { toBody } from "@/lib/body";
import { framingOk, inferView, shoulderRatio } from "@/lib/view";
import {
  DOWNDOG_PX,
  H,
  TREE_PX,
  W,
  WARRIOR2_PX,
  occlude,
  rawFromPixels,
  scaleAbout,
} from "./helpers/synthetic";

const body = (raw: ReturnType<typeof rawFromPixels>) => toBody(raw, W, H);

describe("inferView", () => {
  test("front-facing poses", () => {
    expect(inferView(body(rawFromPixels(WARRIOR2_PX)))).toBe("front");
    expect(inferView(body(rawFromPixels(TREE_PX)))).toBe("front");
  });

  test("side view", () => {
    const b = body(rawFromPixels(DOWNDOG_PX));
    expect(shoulderRatio(b)).toBeCloseTo(0.04, 2);
    expect(inferView(b)).toBe("side");
  });

  test("three-quarter view is ambiguous", () => {
    // shoulder width 63 px vs torso 180 px → ratio 0.35
    const b = body(
      rawFromPixels({ ...WARRIOR2_PX, leftShoulder: [768.5, 300], rightShoulder: [831.5, 300] }),
    );
    expect(shoulderRatio(b)).toBeCloseTo(0.35, 2);
    expect(inferView(b)).toBe("ambiguous");
  });
});

describe("framingOk", () => {
  test("well-framed synthetic poses", () => {
    expect(framingOk(body(rawFromPixels(WARRIOR2_PX)))).toBe(true);
    expect(framingOk(body(rawFromPixels(TREE_PX)))).toBe(true);
    expect(framingOk(body(rawFromPixels(DOWNDOG_PX)))).toBe(true);
  });

  test("too small in frame", () => {
    expect(framingOk(body(scaleAbout(rawFromPixels(WARRIOR2_PX), 0.3)))).toBe(false);
  });

  test("core joint missing fails framing", () => {
    expect(framingOk(body(occlude(rawFromPixels(WARRIOR2_PX), ["leftHip"])))).toBe(false);
  });

  test("non-core joint missing does not fail framing (coverage handles it)", () => {
    expect(framingOk(body(occlude(rawFromPixels(WARRIOR2_PX), ["leftKnee"])))).toBe(true);
  });
});
