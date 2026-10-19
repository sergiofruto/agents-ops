import { describe, expect, test } from "vitest";
import { checkSpecRows } from "@/lib/check-spec";

describe("checkSpecRows", () => {
  const rows = checkSpecRows();

  test("one row per photo-mode check, in pose order", () => {
    expect(rows).toHaveLength(14);
    expect(rows[0]).toEqual({
      poseId: "warrior2",
      pose: "Warrior II",
      id: "frontKneeBend",
      label: "Front knee bend",
      unit: "deg",
      target: "90°",
      tolerance: "± 10°",
      weight: 30,
    });
    expect(rows.map((r) => r.id)).not.toContain("stability");
  });

  test("min checks have no tolerance", () => {
    expect(rows.find((r) => r.id === "footOffKnee")).toMatchObject({ target: "≥ 0.15", tolerance: "—" });
  });

  test("weights per pose", () => {
    const sum = (id: string) => rows.filter((r) => r.poseId === id).reduce((n, r) => n + r.weight, 0);
    expect([sum("warrior2"), sum("tree"), sum("downdog")]).toEqual([100, 80, 100]);
  });
});
