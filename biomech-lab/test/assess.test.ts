import { describe, expect, test } from "vitest";
import { assessPhoto } from "@/lib/assess";
import {
  DOWNDOG_PX,
  H,
  NEUTRAL_PX,
  TREE_PX,
  W,
  WARRIOR2_105_PX,
  WARRIOR2_PX,
  occlude,
  rawFromPixels,
  scaleAbout,
} from "./helpers/synthetic";

describe("assessPhoto", () => {
  test("scores each synthetic pose", () => {
    const w = assessPhoto([rawFromPixels(WARRIOR2_105_PX)], W, H);
    expect(w.kind).toBe("scored");
    if (w.kind === "scored") {
      expect(w.pose).toBe("warrior2");
      expect(w.result.score).toBe(65);
    }
    const t = assessPhoto([rawFromPixels(TREE_PX)], W, H);
    expect(t.kind === "scored" && t.result.score).toBe(100);
    const d = assessPhoto([rawFromPixels(DOWNDOG_PX)], W, H);
    expect(d.kind === "scored" && d.pose).toBe("downdog");
  });

  test("no people", () => {
    expect(assessPhoto([], W, H)).toEqual({ kind: "no_person" });
  });

  test("two people are rejected before classification", () => {
    const raw = rawFromPixels(WARRIOR2_PX);
    expect(assessPhoto([raw, raw], W, H)).toEqual({ kind: "multiple_people" });
  });

  test("unrecognized pose", () => {
    expect(assessPhoto([rawFromPixels(NEUTRAL_PX)], W, H)).toEqual({ kind: "unknown_pose" });
  });

  test("low coverage yields prompts and never a score", () => {
    const r = assessPhoto([occlude(rawFromPixels(WARRIOR2_PX), ["leftKnee"])], W, H);
    expect(r.kind).toBe("not_ready");
    if (r.kind === "not_ready") {
      expect(r.pose).toBe("warrior2");
      expect(r.messages[0]).toMatch(/knees/);
      expect("result" in r).toBe(false);
    }
  });

  test("bad framing yields prompts and never a score", () => {
    const r = assessPhoto([scaleAbout(rawFromPixels(TREE_PX), 0.3)], W, H);
    expect(r.kind).toBe("not_ready");
    if (r.kind === "not_ready") expect(r.readiness.reasons).toContain("bad_framing");
  });
});
