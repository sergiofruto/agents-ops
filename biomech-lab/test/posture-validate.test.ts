import { describe, expect, test } from "vitest";
import type { PhotoInput } from "@/lib/posture/findings";
import { REJECTION_MESSAGE, validHeight, validateStep } from "@/lib/posture/validate";
import { occlude, rawFromPixels, type PxSpec } from "./helpers/synthetic";

const W = 1000;
const HT = 1200;

const FRONT: PxSpec = {
  nose: [500, 120, 1, -0.4],
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

/** Seen from behind: MediaPipe's left/right labels swap image sides and the nose sits behind the ears. */
const fromBehind = (spec: PxSpec): PxSpec => ({
  ...spec,
  nose: [500, 120, 1, 0.4],
  leftEar: spec.rightEar,
  rightEar: spec.leftEar,
  leftShoulder: spec.rightShoulder,
  rightShoulder: spec.leftShoulder,
  leftHip: spec.rightHip,
  rightHip: spec.leftHip,
});

const photo = (spec: PxSpec): PhotoInput => ({
  people: [rawFromPixels(spec, { width: W, height: HT })],
  width: W,
  height: HT,
});

describe("validateStep", () => {
  test("a front photo passes the front step and is flagged on the back step", () => {
    expect(validateStep("front", photo(FRONT))).toEqual({ ok: true });
    expect(validateStep("back", photo(FRONT))).toEqual({ ok: false, reason: "looks_like_front" });
  });

  test("a back photo passes the back step and is flagged on the front step", () => {
    expect(validateStep("back", photo(fromBehind(FRONT)))).toEqual({ ok: true });
    expect(validateStep("front", photo(fromBehind(FRONT)))).toEqual({ ok: false, reason: "looks_like_back" });
  });

  test("mixed orientation signals are rejected on both steps", () => {
    const mixed: PxSpec = { ...FRONT, nose: [500, 120, 1, 0.4] };
    expect(validateStep("front", photo(mixed))).toEqual({ ok: false, reason: "looks_like_back" });
    expect(validateStep("back", photo(mixed))).toEqual({ ok: false, reason: "looks_like_front" });
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

  test("a photo too small to measure precisely is rejected", () => {
    const half = Object.fromEntries(
      Object.entries(FRONT).map(([j, p]) => [j, [p![0] / 2, p![1] / 2, ...p!.slice(2)]]),
    ) as PxSpec;
    const small: PhotoInput = { people: [rawFromPixels(half, { width: W / 2, height: HT / 2 })], width: W / 2, height: HT / 2 };
    expect(validateStep("front", small)).toEqual({ ok: false, reason: "too_small" });
  });

  test("people count comes first", () => {
    expect(validateStep("front", { ...photo(FRONT), people: [] })).toEqual({ ok: false, reason: "no_person" });
    const p = photo(FRONT);
    expect(validateStep("front", { ...p, people: [p.people[0], p.people[0]] })).toEqual({ ok: false, reason: "multiple_people" });
  });

  test("the same file on two steps is rejected", () => {
    expect(validateStep("back", photo(fromBehind(FRONT)), { fingerprint: "abc", otherFingerprints: ["abc"] })).toEqual({
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
