import { describe, expect, test } from "vitest";
import { iterationSeries, sampleReports } from "@/lib/sample-reports";

describe("sampleReports", () => {
  const reports = sampleReports();

  test("three reports with the golden scores", () => {
    expect(reports.map((r) => [r.id, r.score])).toEqual([
      ["warrior2", 50],
      ["tree", 55],
      ["downdog", 46],
    ]);
  });

  test("check credits reproduce each score", () => {
    for (const r of reports) {
      const measured = r.checks.filter((c) => c.credit !== null);
      const earned = measured.reduce((s, c) => s + c.weight * (c.credit ?? 0), 0);
      const total = measured.reduce((s, c) => s + c.weight, 0);
      expect(Math.round((100 * earned) / total)).toBe(r.score);
    }
  });

  test("tree flags the foot on the knee", () => {
    const tree = reports.find((r) => r.id === "tree");
    expect(tree?.checks.find((c) => c.id === "footOffKnee")?.status).toBe("fail");
  });

  test("reports carry landmarks and image metadata", () => {
    for (const r of reports) {
      expect(r.landmarks).toHaveLength(33);
      expect(r.imageSrc).toBe(`/samples/${r.id}.jpg`);
      expect([r.width, r.height]).toEqual([1280, 720]);
      expect(r.coverage).toBe(1);
    }
  });
});

test("iterationSeries: iteration 1 matches the reports", () => {
  expect(iterationSeries()).toEqual([
    { iteration: 1, date: "2026-10-01", scores: { warrior2: 50, tree: 55, downdog: 46 } },
  ]);
});
