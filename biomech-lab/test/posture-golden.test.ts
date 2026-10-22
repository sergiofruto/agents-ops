import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, test } from "vitest";
import { assessPosture, type PhotoInput } from "@/lib/posture/findings";
import type { PostureView } from "@/lib/posture/frame";
import { validateStep } from "@/lib/posture/validate";
import { mirror } from "./helpers/synthetic";

/**
 * MediaPipe landmarks of the three local posture photos (public/user-1-assets/posture,
 * gitignored), extracted at production size via /dev/extract. Three different men, so
 * front/back disagreement is expected; these are regression fixtures, not one client.
 */
const load = (view: PostureView): PhotoInput =>
  JSON.parse(readFileSync(path.join(process.cwd(), "data", "samples", "posture", `${view}.json`), "utf8"));

const front = load("front");
const side = load("side");
const back = load("back");

/** Recorded on first extraction (2026-10-22) as observed score ± 5, height 180 cm. */
const EXPECTED = { min: 40, max: 50 }; // observed 45

describe("golden posture photos", () => {
  test.each([
    ["front", front],
    ["side", side],
    ["back", back],
  ] as const)("the %s photo passes its own step", (view, photo) => {
    expect(validateStep(view, photo)).toEqual({ ok: true });
  });

  test("swapped or wrong photos are rejected", () => {
    expect(validateStep("back", front)).toEqual({ ok: false, reason: "looks_like_front" });
    expect(validateStep("front", back)).toEqual({ ok: false, reason: "looks_like_back" });
    expect(validateStep("front", side)).toEqual({ ok: false, reason: "wrong_view_front" });
    expect(validateStep("side", front)).toEqual({ ok: false, reason: "wrong_view_side" });
  });

  test("a selfie-mirrored front photo still counts as front", () => {
    expect(validateStep("front", { ...front, people: [mirror(front.people[0])] })).toEqual({ ok: true });
  });

  test("the assessment scores within the recorded range", () => {
    const r = assessPosture({ heightCm: 180, front, side, back });
    console.info(
      `[posture golden] score ${r.score}`,
      r.findings.map((f) => `${f.id}=${f.value?.toFixed(2)}:${f.status}`).join(" "),
    );
    expect(r.score).not.toBeNull();
    expect(r.score!).toBeGreaterThanOrEqual(EXPECTED.min);
    expect(r.score!).toBeLessThanOrEqual(EXPECTED.max);
  });
});
