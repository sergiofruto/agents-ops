import { expect, test } from "vitest";
import { scoreBasis } from "@/components/viz/CheckRow";
import { sampleReports } from "@/lib/sample-reports";

test("scoreBasis reproduces each sample report's score", () => {
  for (const report of sampleReports()) {
    const { earned, total } = scoreBasis(report.checks);
    expect(Math.round((100 * earned) / total)).toBe(report.score);
  }
});

test("Tree's measured total is 80 points", () => {
  const tree = sampleReports().find((r) => r.id === "tree")!;
  const { total } = scoreBasis(tree.checks);
  expect(total).toBe(80);
});
