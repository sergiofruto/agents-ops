import { describe, expect, test } from "vitest";
import { toBody } from "@/lib/body";
import type { RawLandmark } from "@/lib/landmarks";
import { readinessMessages } from "@/lib/messages";
import { POSES } from "@/lib/poses";
import { assessReadiness } from "@/lib/readiness";
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

const ready = (
  raw: RawLandmark[],
  poseId: keyof typeof POSES,
  opts: { peopleCount?: number; mode?: "photo" | "live" } = {},
) =>
  assessReadiness({
    peopleCount: opts.peopleCount ?? 1,
    body: toBody(raw, W, H),
    pose: POSES[poseId],
    mode: opts.mode ?? "photo",
  });

describe("assessReadiness", () => {
  test("synthetic poses are ready with full coverage", () => {
    for (const [px, id] of [
      [WARRIOR2_PX, "warrior2"],
      [TREE_PX, "tree"],
      [DOWNDOG_PX, "downdog"],
    ] as const) {
      const r = ready(rawFromPixels(px), id);
      expect(r).toMatchObject({ canScore: true, coverage: 1, reasons: [], missing: [] });
    }
  });

  test("no body → no_person", () => {
    const r = assessReadiness({ peopleCount: 0, body: null, pose: POSES.tree, mode: "photo" });
    expect(r).toMatchObject({ canScore: false, reasons: ["no_person"] });
  });

  test("two people → multiple_people", () => {
    expect(ready(rawFromPixels(WARRIOR2_PX), "warrior2", { peopleCount: 2 }).reasons).toContain(
      "multiple_people",
    );
  });

  test("side-view body for a front pose → wrong_view", () => {
    const r = ready(rawFromPixels(DOWNDOG_PX), "warrior2");
    expect(r.view).toBe("side");
    expect(r.reasons).toContain("wrong_view");
    expect(r.canScore).toBe(false);
  });

  test("too small in frame → bad_framing", () => {
    expect(ready(scaleAbout(rawFromPixels(WARRIOR2_PX), 0.3), "warrior2").reasons).toContain(
      "bad_framing",
    );
  });

  test("hidden front knee → low_coverage (50%) with the knee listed as missing", () => {
    const r = ready(occlude(rawFromPixels(WARRIOR2_PX), ["leftKnee"]), "warrior2");
    expect(r.coverage).toBeCloseTo(0.5, 6);
    expect(r.reasons).toEqual(["low_coverage"]);
    expect(r.missing).toEqual(["leftKnee"]);
  });

  test("hidden arm alone keeps coverage above 70%", () => {
    const r = ready(occlude(rawFromPixels(WARRIOR2_PX), ["leftWrist"]), "warrior2");
    expect(r.coverage).toBeCloseTo(0.8, 6);
    expect(r.canScore).toBe(true);
  });
});

describe("readinessMessages", () => {
  test("wrong view for a side pose asks to turn sideways", () => {
    const r = ready(rawFromPixels(WARRIOR2_PX), "downdog");
    expect(readinessMessages(r, POSES.downdog)).toContain(
      "Turn sideways to the camera for Downward Dog.",
    );
  });

  test("low coverage names the missing body parts without left/right", () => {
    const r = ready(occlude(rawFromPixels(WARRIOR2_PX), ["leftKnee", "leftAnkle"]), "warrior2");
    expect(readinessMessages(r, POSES.warrior2)).toEqual([
      "We can't clearly see your knees and ankles. Adjust your position or lighting.",
    ]);
  });
});
