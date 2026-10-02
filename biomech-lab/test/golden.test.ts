import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, test } from "vitest";
import { assessPhoto } from "@/lib/assess";
import type { RawLandmark } from "@/lib/landmarks";
import type { PoseId } from "@/lib/poses";
import { mirror, occlude, scaleAbout } from "./helpers/synthetic";

type Fixture = { sample: string; width: number; height: number; people: RawLandmark[][] };

/**
 * Documented expected score ranges for Sergio's sample photos.
 * Recorded on first extraction as observed score ± 5 (see Task 10, Step 7).
 */
const EXPECTED: Record<PoseId, { min: number; max: number }> = {
  warrior2: { min: 45, max: 55 },
  tree: { min: 75, max: 85 },
  downdog: { min: 41, max: 51 },
};

const load = (id: PoseId): Fixture | null => {
  const file = path.join(process.cwd(), "test", "fixtures", `${id}.json`);
  return existsSync(file) ? (JSON.parse(readFileSync(file, "utf8")) as Fixture) : null;
};

describe.each(Object.keys(EXPECTED) as PoseId[])("golden sample: %s", (id) => {
  const fx = load(id);

  test.skipIf(!fx)("is recognized, ready, and scored within the documented range", () => {
    const r = assessPhoto(fx!.people, fx!.width, fx!.height);
    if (r.kind !== "scored") throw new Error(`expected scored, got ${JSON.stringify(r, null, 2)}`);
    console.info(`[golden] ${id}: score ${r.result.score}, coverage ${r.readiness.coverage}`);
    expect(r.pose).toBe(id);
    expect(r.result.score).toBeGreaterThanOrEqual(EXPECTED[id].min);
    expect(r.result.score).toBeLessThanOrEqual(EXPECTED[id].max);
  });

  test.skipIf(!fx)("mirrored input gives the same score", () => {
    const a = assessPhoto(fx!.people, fx!.width, fx!.height);
    const b = assessPhoto(fx!.people.map(mirror), fx!.width, fx!.height);
    expect(b.kind).toBe(a.kind);
    if (a.kind === "scored" && b.kind === "scored") expect(b.result.score).toBe(a.result.score);
  });

  test.skipIf(!fx)("a second person is rejected", () => {
    const p = fx!.people[0];
    expect(assessPhoto([p, p], fx!.width, fx!.height).kind).toBe("multiple_people");
  });

  test.skipIf(!fx)("hidden knees and ankles never produce a score", () => {
    const hidden = occlude(fx!.people[0], [
      "leftKnee", "rightKnee", "leftAnkle", "rightAnkle",
    ]);
    expect(assessPhoto([hidden], fx!.width, fx!.height).kind).not.toBe("scored");
  });

  test.skipIf(!fx)("a tiny figure in frame never produces a score", () => {
    const small = scaleAbout(fx!.people[0], 0.3);
    expect(assessPhoto([small], fx!.width, fx!.height).kind).not.toBe("scored");
  });
});
