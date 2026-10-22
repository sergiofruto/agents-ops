import { describe, expect, test } from "vitest";
import type { PhotoInput } from "@/lib/posture/findings";
import { REJECTION_MESSAGE, validHeight, validateStep } from "@/lib/posture/validate";
import { occlude, rawFromPixels, type PxSpec } from "./helpers/synthetic";

const W = 1000;
const HT = 1200;

const FRONT: PxSpec = {
  nose: [500, 120, 0.95],
  leftEye: [490, 112, 0.95],
  rightEye: [510, 112, 0.95],
  leftEar: [480, 100],
  rightEar: [520, 100],
  leftShoulder: [580, 200],
  rightShoulder: [420, 200],
  leftHip: [560, 480],
  rightHip: [440, 480],
  leftKnee: [555, 750],
  rightKnee: [445, 750],
  leftAnkle: [550, 1000],
  rightAnkle: [450, 1000],
  leftHeel: [550, 1040],
  rightHeel: [450, 1040],
};

const SIDE: PxSpec = {
  ...FRONT,
  leftShoulder: [505, 200],
  rightShoulder: [495, 200],
  leftHip: [505, 480],
  rightHip: [495, 480],
};

const photo = (spec: PxSpec, faceVis?: number): PhotoInput => {
  const s: PxSpec = { ...spec };
  if (faceVis !== undefined) {
    s.nose = [500, 120, faceVis];
    s.leftEye = [490, 112, faceVis];
    s.rightEye = [510, 112, faceVis];
  }
  return { people: [rawFromPixels(s, { width: W, height: HT })], width: W, height: HT };
};

describe("validateStep", () => {
  test("a front-facing photo passes the front step and is flagged on the back step", () => {
    expect(validateStep("front", photo(FRONT))).toEqual({ ok: true });
    expect(validateStep("back", photo(FRONT))).toEqual({ ok: false, reason: "looks_like_front" });
  });

  test("a hidden face passes the back step and is flagged on the front step", () => {
    expect(validateStep("back", photo(FRONT, 0.2))).toEqual({ ok: true });
    expect(validateStep("front", photo(FRONT, 0.2))).toEqual({ ok: false, reason: "looks_like_back" });
  });

  test("an in-between face visibility is rejected on both steps", () => {
    expect(validateStep("front", photo(FRONT, 0.65))).toEqual({ ok: false, reason: "looks_like_back" });
    expect(validateStep("back", photo(FRONT, 0.65))).toEqual({ ok: false, reason: "looks_like_front" });
  });

  test("view must match the step", () => {
    expect(validateStep("front", photo(SIDE))).toEqual({ ok: false, reason: "wrong_view_front" });
    expect(validateStep("side", photo(FRONT))).toEqual({ ok: false, reason: "wrong_view_side" });
    expect(validateStep("side", photo(SIDE))).toEqual({ ok: true });
  });

  test("no usable heels or ankles is a framing problem", () => {
    const p = photo(FRONT);
    p.people = [occlude(p.people[0], ["leftHeel", "rightHeel", "leftAnkle", "rightAnkle"])];
    expect(validateStep("front", p)).toEqual({ ok: false, reason: "framing" });
  });

  test("people count comes first", () => {
    expect(validateStep("front", { ...photo(FRONT), people: [] })).toEqual({ ok: false, reason: "no_person" });
    const p = photo(FRONT);
    expect(validateStep("front", { ...p, people: [p.people[0], p.people[0]] })).toEqual({ ok: false, reason: "multiple_people" });
  });

  test("the same file on two steps is rejected", () => {
    expect(validateStep("back", photo(FRONT, 0.2), { fingerprint: "abc", otherFingerprints: ["abc"] })).toEqual({
      ok: false,
      reason: "duplicate",
    });
  });

  test("every rejection has a message without em dashes", () => {
    for (const m of Object.values(REJECTION_MESSAGE)) {
      expect(m.length).toBeGreaterThan(10);
      expect(m).not.toContain("—");
    }
  });
});

describe("validHeight", () => {
  test("accepts whole cm in range", () => expect(validHeight("175")).toBe(175));
  test.each(["119", "221", "175.5", "", "abc", " "])("rejects %j", (v) => expect(validHeight(v)).toBeNull());
});
