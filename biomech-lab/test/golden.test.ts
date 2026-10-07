import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, test } from "vitest";
import { assessPhoto } from "@/lib/assess";
import { toBody } from "@/lib/body";
import { joint } from "@/lib/landmarks";
import type { RawLandmark } from "@/lib/landmarks";
import { POSES } from "@/lib/poses";
import type { PoseId } from "@/lib/poses";
import { mirror, occlude, scaleAbout } from "./helpers/synthetic";

type Fixture = { sample: string; width: number; height: number; people: RawLandmark[][] };

/**
 * Documented expected score ranges for Sergio's sample photos.
 * Recorded on first extraction as observed score ± 5 (see Task 10, Step 7).
 * tree re-recorded after Task 10b (footOffKnee measures the heel–toe span).
 */
const EXPECTED: Record<PoseId, { min: number; max: number }> = {
  warrior2: { min: 45, max: 55 },
  tree: { min: 50, max: 60 },
  downdog: { min: 41, max: 51 },
};

const load = (id: PoseId): Fixture => {
  const file = path.join(process.cwd(), "data", "samples", `${id}.json`);
  if (!existsSync(file)) throw new Error(`missing fixture data/samples/${id}.json`);
  return JSON.parse(readFileSync(file, "utf8")) as Fixture;
};

describe.each(Object.keys(EXPECTED) as PoseId[])("golden sample: %s", (id) => {
  const fx = load(id);

  test("is recognized, ready, and scored within the documented range", () => {
    const r = assessPhoto(fx.people, fx.width, fx.height);
    if (r.kind !== "scored") throw new Error(`expected scored, got ${JSON.stringify(r, null, 2)}`);
    console.info(`[golden] ${id}: score ${r.result.score}, coverage ${r.readiness.coverage}`);
    expect(r.pose).toBe(id);
    expect(r.result.score).toBeGreaterThanOrEqual(EXPECTED[id].min);
    expect(r.result.score).toBeLessThanOrEqual(EXPECTED[id].max);
  });

  test("mirrored input gives the same score", () => {
    const a = assessPhoto(fx.people, fx.width, fx.height);
    const b = assessPhoto(fx.people.map(mirror), fx.width, fx.height);
    expect(b.kind).toBe(a.kind);
    if (a.kind === "scored" && b.kind === "scored") expect(b.result.score).toBe(a.result.score);
  });

  test("a second person is rejected", () => {
    const p = fx.people[0];
    expect(assessPhoto([p, p], fx.width, fx.height).kind).toBe("multiple_people");
  });

  test("hidden knees and ankles never produce a score", () => {
    const hidden = occlude(fx.people[0], [
      "leftKnee", "rightKnee", "leftAnkle", "rightAnkle",
    ]);
    expect(assessPhoto([hidden], fx.width, fx.height).kind).not.toBe("scored");
  });

  test("a tiny figure in frame never produces a score", () => {
    const small = scaleAbout(fx.people[0], 0.3);
    expect(assessPhoto([small], fx.width, fx.height).kind).not.toBe("scored");
  });
});

describe("golden sample: warrior2 readiness gate", () => {
  /**
   * The "hidden knees and ankles" variant above likely fails via unknown_pose
   * (occlusion drops classifier confidence), not via the coverage gate itself.
   * This isolates the gate: occlude only the front knee, which drops exactly
   * frontKneeBend (weight 30) and kneeOverAnkle (weight 20) from the measured
   * total — coverage 50/100 = 0.5, below MIN_COVERAGE (0.7) — while leaving
   * everything the classifier and view/framing checks use untouched.
   */
  test("hiding only the front knee triggers the low_coverage gate directly", () => {
    const fx = load("warrior2");
    const body = toBody(fx.people[0], fx.width, fx.height);
    const roles = POSES.warrior2.assignRoles(body);
    const hidden = occlude(fx.people[0], [joint(roles.front, "Knee")]);

    const r = assessPhoto([hidden], fx.width, fx.height);
    if (r.kind !== "not_ready") {
      throw new Error(`expected not_ready, got ${JSON.stringify(r, null, 2)}`);
    }
    expect(r.kind).toBe("not_ready");
    expect(r.readiness.reasons).toContain("low_coverage");
    expect(r.readiness.coverage).toBeCloseTo(0.5, 6);
  });
});
