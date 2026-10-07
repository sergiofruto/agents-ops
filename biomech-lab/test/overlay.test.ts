import { expect, test } from "vitest";
import { LANDMARK_FILES } from "@/data/samples";
import { overlayGeometry } from "@/lib/overlay";
import { H, W, WARRIOR2_PX, occlude, rawFromPixels } from "./helpers/synthetic";

test("synthetic figure: pixel-space bones between usable joints only", () => {
  const g = overlayGeometry(rawFromPixels(WARRIOR2_PX), W, H);
  expect(g.width).toBe(W);
  expect(g.bones).toHaveLength(12); // no feet landmarks in the synthetic figure
  expect(g.joints).toHaveLength(13); // nose + 12 limb/torso joints (ears are not drawn)
  const shoulders = g.bones[0];
  expect(shoulders.x1).toBeCloseTo(720, 6);
  expect(shoulders.y1).toBeCloseTo(300, 6);
  expect(shoulders.x2).toBeCloseTo(880, 6);
});

test("occluded joints drop their bones", () => {
  const g = overlayGeometry(occlude(rawFromPixels(WARRIOR2_PX), ["leftKnee"]), W, H);
  expect(g.bones).toHaveLength(10);
  expect(g.joints.map((j) => j.id)).not.toContain("leftKnee");
});

test("real Warrior II sample: full skeleton including feet", () => {
  const f = LANDMARK_FILES.warrior2;
  const g = overlayGeometry(f.people[0], f.width, f.height);
  expect(g.bones).toHaveLength(18);
  expect(g.joints).toHaveLength(17);
});
