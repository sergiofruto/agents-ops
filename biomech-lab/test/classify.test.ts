import { describe, expect, test } from "vitest";
import { toBody } from "@/lib/body";
import { classify } from "@/lib/classify";
import type { RawLandmark } from "@/lib/landmarks";
import {
  DOWNDOG_PX,
  H,
  NEUTRAL_PX,
  TREE_PX,
  W,
  WARRIOR2_105_PX,
  WARRIOR2_PX,
  mirror,
  rawFromPixels,
} from "./helpers/synthetic";

const cls = (raw: RawLandmark[]) => classify(toBody(raw, W, H));

describe("classify", () => {
  test("Warrior II", () => {
    expect(cls(rawFromPixels(WARRIOR2_PX))).toEqual({ pose: "warrior2", confidence: 1 });
    expect(cls(rawFromPixels(WARRIOR2_105_PX)).pose).toBe("warrior2");
  });

  test("Tree", () => {
    expect(cls(rawFromPixels(TREE_PX))).toEqual({ pose: "tree", confidence: 1 });
  });

  test("Downward Dog (confidence reflects the far side's lower visibility)", () => {
    const r = cls(rawFromPixels(DOWNDOG_PX));
    expect(r.pose).toBe("downdog");
    expect(r.confidence).toBeCloseTo(0.8, 6);
  });

  test("mirrored inputs classify the same", () => {
    expect(cls(mirror(rawFromPixels(WARRIOR2_PX))).pose).toBe("warrior2");
    expect(cls(mirror(rawFromPixels(TREE_PX))).pose).toBe("tree");
    expect(cls(mirror(rawFromPixels(DOWNDOG_PX))).pose).toBe("downdog");
  });

  test("neutral standing is unknown", () => {
    expect(cls(rawFromPixels(NEUTRAL_PX)).pose).toBe("unknown");
  });

  test("low landmark visibility is unknown", () => {
    expect(cls(rawFromPixels(WARRIOR2_PX, { visibility: 0.55 })).pose).toBe("unknown");
  });
});
