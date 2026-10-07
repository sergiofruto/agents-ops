import { describe, expect, test } from "vitest";
import { poseSummaries, viewLabel } from "@/lib/pose-summaries";

describe("poseSummaries", () => {
  const s = poseSummaries();
  const pose = (id: string) => {
    const p = s.find((x) => x.id === id);
    if (!p) throw new Error(`missing ${id}`);
    return p;
  };

  test("three poses in display order", () => {
    expect(s.map((p) => p.id)).toEqual(["warrior2", "tree", "downdog"]);
  });

  test("lists photo-mode checks only (live-only stability excluded)", () => {
    expect(pose("tree").checks.map((c) => c.id)).toEqual([
      "standingLeg",
      "footOffKnee",
      "hipsLevel",
      "torsoUpright",
    ]);
    expect(pose("warrior2").checks).toHaveLength(5);
    expect(pose("downdog").checks).toHaveLength(5);
  });

  test("degree targets are human-readable; ratio targets are hidden", () => {
    expect(pose("warrior2").checks[0]).toEqual({
      id: "frontKneeBend",
      label: "Front knee bend",
      target: "90° ± 10°",
    });
    expect(pose("tree").checks.find((c) => c.id === "footOffKnee")?.target).toBeNull();
    expect(pose("downdog").checks.find((c) => c.id === "headAligned")?.target).toBeNull();
  });

  test("view labels", () => {
    expect(viewLabel("front")).toBe("Facing the camera");
    expect(pose("downdog").viewLabel).toBe("Side view");
  });
});
