import { expect, test } from "vitest";
import { toBody } from "@/lib/body";
import { FINDINGS, type FindingId } from "@/lib/posture/config";
import type { Finding, PostureStatus } from "@/lib/posture/findings";
import type { PostureFrame } from "@/lib/posture/frame";
import { coronalOverlay, sagittalOverlay } from "@/lib/posture/overlay";
import { rawFromPixels, type PxSpec } from "./helpers/synthetic";

const W = 1000;
const HT = 1200;

const findings = (overrides: Partial<Record<FindingId, PostureStatus>>): Finding[] =>
  (Object.keys(FINDINGS) as FindingId[]).map((id) => ({
    id,
    region: FINDINGS[id].region,
    unit: FINDINGS[id].unit,
    value: 0,
    perView: {},
    status: overrides[id] ?? "aligned",
    disagree: false,
    side: null,
  }));

const frame = (view: PostureFrame["view"], spec: PxSpec): PostureFrame => ({
  view,
  body: toBody(rawFromPixels(spec, { width: W, height: HT }), W, HT),
  cmPerPx: 0.2,
});

const FRONT: PxSpec = {
  leftEar: [480, 100],
  rightEar: [520, 100],
  leftShoulder: [580, 210],
  rightShoulder: [420, 200],
  leftHip: [560, 480],
  rightHip: [440, 480],
};

test("coronal: level lines take their finding's status and a dashed midline runs through the hips", () => {
  const o = coronalOverlay(frame("front", FRONT), findings({ shoulderLevel: "needs_work", hipLevel: "slight" }));
  const shoulder = o.lines.find((l) => Math.abs(l.y1 - 210) < 1e-6 || Math.abs(l.y1 - 200) < 1e-6);
  expect(shoulder?.status).toBe("needs_work");
  expect(o.lines.find((l) => !l.dashed && Math.abs(l.y1 - 480) < 1e-6)?.status).toBe("slight");
  const mid = o.lines.find((l) => l.dashed);
  expect(mid?.x1).toBeCloseTo(500, 6);
  expect(mid?.x2).toBeCloseTo(500, 6);
});

test("sagittal: the plumb line runs through the near ankle for the full photo height", () => {
  const side: PxSpec = {
    nose: [640, 120],
    leftEar: [600, 110],
    leftShoulder: [575, 200],
    leftHip: [615, 500],
    leftKnee: [607, 750],
    leftAnkle: [600, 1000],
  };
  const o = sagittalOverlay(frame("side", side), findings({ forwardHead: "needs_work" }));
  const plumb = o.lines.find((l) => l.dashed);
  expect(plumb?.x1).toBeCloseTo(600, 6);
  expect(plumb?.x2).toBeCloseTo(600, 6);
  expect(plumb).toMatchObject({ y1: 0, y2: HT });
  const ear = o.dots.find((d) => Math.abs(d.x - 600) < 1e-6 && Math.abs(d.y - 110) < 1e-6);
  expect(ear?.status).toBe("needs_work");
});
