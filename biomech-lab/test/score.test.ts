import { describe, expect, test } from "vitest";
import { toBody } from "@/lib/body";
import { POSES } from "@/lib/poses";
import { checkCredit, measureFrame, scoreMeasurements } from "@/lib/score";
import type { RawLandmark } from "@/lib/landmarks";
import {
  DOWNDOG_PX,
  H,
  TREE_FOOT_ON_KNEE_PX,
  TREE_PX,
  W,
  WARRIOR2_105_PX,
  WARRIOR2_PX,
  mirror,
  occlude,
  rawFromPixels,
} from "./helpers/synthetic";

const score = (poseId: keyof typeof POSES, raw: RawLandmark[], mode: "photo" | "live" = "photo") => {
  const pose = POSES[poseId];
  const measurements = measureFrame(pose, toBody(raw, W, H), mode);
  return scoreMeasurements(pose, measurements, mode);
};
const check = (r: ReturnType<typeof score>, id: string) => {
  const c = r.checks.find((x) => x.id === id);
  if (!c) throw new Error(`missing check ${id}`);
  return c;
};

describe("checkCredit", () => {
  const range = POSES.warrior2.checks.find((c) => c.id === "frontKneeBend")!; // 90 ± 10
  const min = POSES.tree.checks.find((c) => c.id === "footOffKnee")!; // ≥ 0.15

  test("full credit inside tolerance", () => {
    expect(checkCredit(range, 90)).toBe(1);
    expect(checkCredit(range, 100)).toBe(1);
  });
  test("linear falloff between tol and 2·tol", () => {
    expect(checkCredit(range, 105)).toBeCloseTo(0.5, 6);
    expect(checkCredit(range, 75)).toBeCloseTo(0.5, 6);
  });
  test("zero at or beyond 2·tol", () => {
    expect(checkCredit(range, 110)).toBe(0);
    expect(checkCredit(range, 130)).toBe(0);
  });
  test("min checks are binary", () => {
    expect(checkCredit(min, 0.15)).toBe(1);
    expect(checkCredit(min, 0.1)).toBe(0);
  });
});

describe("Warrior II", () => {
  test("ideal form scores 100", () => {
    const r = score("warrior2", rawFromPixels(WARRIOR2_PX));
    expect(r.score).toBe(100);
    expect(check(r, "frontKneeBend").value).toBeCloseTo(90, 4);
    expect(r.checks.every((c) => c.status === "pass")).toBe(true);
  });

  test("105° front knee drifting past the ankle scores 65", () => {
    const r = score("warrior2", rawFromPixels(WARRIOR2_105_PX));
    expect(check(r, "frontKneeBend").value).toBeCloseTo(105, 2);
    expect(check(r, "frontKneeBend").status).toBe("partial");
    expect(check(r, "kneeOverAnkle").value).toBeCloseTo(0.316, 3);
    expect(check(r, "kneeOverAnkle").status).toBe("fail");
    expect(r.score).toBe(65);
  });

  test("mirrored input gives the same score and values", () => {
    const original = score("warrior2", rawFromPixels(WARRIOR2_105_PX));
    const mirrored = score("warrior2", mirror(rawFromPixels(WARRIOR2_105_PX)));
    expect(mirrored.score).toBe(original.score);
    for (const c of original.checks) {
      expect(check(mirrored, c.id).value).toBeCloseTo(c.value!, 6);
    }
  });

  test("unmeasurable checks are excluded, not failed", () => {
    const r = score("warrior2", occlude(rawFromPixels(WARRIOR2_105_PX), ["leftKnee"]));
    expect(check(r, "frontKneeBend").status).toBe("not_measured");
    expect(check(r, "kneeOverAnkle").status).toBe("not_measured");
    expect(r.score).toBe(100);
  });
});

describe("Tree", () => {
  test("photo mode excludes the live-only stability check", () => {
    const r = score("tree", rawFromPixels(TREE_PX), "photo");
    expect(r.checks.map((c) => c.id)).not.toContain("stability");
    expect(check(r, "footOffKnee").value).toBeCloseTo(0.214, 3);
    expect(r.score).toBe(100);
  });

  test("live mode lists stability as not measured until the window provides it", () => {
    const r = score("tree", rawFromPixels(TREE_PX), "live");
    expect(check(r, "stability").status).toBe("not_measured");
    expect(r.score).toBe(100);
  });

  test("foot pressed on the knee fails footOffKnee (heel–toe span overlaps the knee)", () => {
    const r = score("tree", rawFromPixels(TREE_FOOT_ON_KNEE_PX), "photo");
    expect(check(r, "footOffKnee").value).toBe(0);
    expect(check(r, "footOffKnee").status).toBe("fail");
    expect(r.score).toBe(75);
    expect(score("tree", mirror(rawFromPixels(TREE_FOOT_ON_KNEE_PX)), "photo").score).toBe(75);
  });
});

describe("Downward Dog", () => {
  test("ideal form scores 100 using the near side", () => {
    const r = score("downdog", rawFromPixels(DOWNDOG_PX));
    expect(check(r, "hipAngle").value).toBeCloseTo(80, 0);
    expect(check(r, "flatBack").value).toBeCloseTo(180, 2);
    expect(check(r, "headAligned").value).toBeCloseTo(0, 3);
    expect(r.score).toBe(100);
  });

  test("mirrored input gives the same score", () => {
    expect(score("downdog", mirror(rawFromPixels(DOWNDOG_PX))).score).toBe(100);
  });
});

describe("scoreMeasurements (server-safe)", () => {
  test("ignores unknown check ids and scores only known ones", () => {
    const r = scoreMeasurements(
      POSES.warrior2,
      [
        { checkId: "frontKneeBend", value: 90 },
        { checkId: "bogus", value: 1 },
      ],
      "photo",
    );
    expect(r.checks.map((c) => c.id)).not.toContain("bogus");
    expect(r.score).toBe(100);
    expect(check(r, "armsLevel").status).toBe("not_measured");
  });

  test("no measured checks → null score", () => {
    expect(scoreMeasurements(POSES.warrior2, [], "photo").score).toBeNull();
  });

  test("a non-finite value is treated as not_measured, other checks still score", () => {
    const r = scoreMeasurements(
      POSES.warrior2,
      [
        { checkId: "frontKneeBend", value: NaN },
        { checkId: "armsLevel", value: 0 },
      ],
      "photo",
    );
    expect(check(r, "frontKneeBend").status).toBe("not_measured");
    expect(check(r, "frontKneeBend").value).toBeNull();
    expect(r.score).toBe(100);
  });

  test("only a non-finite measurement → null score", () => {
    const r = scoreMeasurements(
      POSES.warrior2,
      [{ checkId: "frontKneeBend", value: Infinity }],
      "photo",
    );
    expect(r.score).toBeNull();
  });
});

describe("CheckResult.range", () => {
  test("a range check's result carries { target, tol } matching its CheckDef", () => {
    const def = POSES.warrior2.checks.find((c) => c.id === "frontKneeBend")!;
    if (def.kind !== "range") throw new Error("expected frontKneeBend to be a range check");
    const r = score("warrior2", rawFromPixels(WARRIOR2_PX));
    expect(check(r, "frontKneeBend").range).toEqual({ target: def.target, tol: def.tol });
  });

  test("a min check's result has range: null", () => {
    const r = score("tree", rawFromPixels(TREE_PX));
    expect(check(r, "footOffKnee").range).toBeNull();
  });
});
