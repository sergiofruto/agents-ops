import { ITERATIONS } from "@/data/iterations";
import { LANDMARK_FILES } from "@/data/samples";
import { assessPhoto } from "./assess";
import type { RawLandmark } from "./landmarks";
import { POSE_ORDER, POSES, type PoseId } from "./poses";
import { SAMPLES } from "./samples";
import type { CheckResult } from "./score";

export type SampleReport = {
  id: PoseId;
  label: string;
  view: "front" | "side";
  imageSrc: string;
  width: number;
  height: number;
  landmarks: RawLandmark[];
  score: number;
  coverage: number;
  checks: CheckResult[];
};

export type IterationPoint = { iteration: number; date: string; scores: Record<PoseId, number> };

/** Runs the real assessment pipeline on a stored landmark file. Throws if the sample does not score. */
export function buildReport(id: PoseId, fileId: string = id): SampleReport {
  const file = LANDMARK_FILES[fileId];
  if (!file) throw new Error(`unknown landmark file "${fileId}"`);
  const a = assessPhoto(file.people, file.width, file.height);
  if (a.kind !== "scored" || a.result.score === null) {
    throw new Error(`sample "${fileId}" did not score (${a.kind})`);
  }
  if (a.pose !== id) throw new Error(`sample "${fileId}" classified as ${a.pose}, expected ${id}`);
  return {
    id,
    label: POSES[id].label,
    view: POSES[id].view,
    imageSrc: SAMPLES.find((s) => s.id === id)?.src ?? `/samples/${id}.jpg`,
    width: file.width,
    height: file.height,
    landmarks: file.people[0],
    score: a.result.score,
    coverage: a.readiness.coverage,
    checks: a.result.checks,
  };
}

export function sampleReports(): SampleReport[] {
  const latest = ITERATIONS[ITERATIONS.length - 1];
  return POSE_ORDER.map((id) => buildReport(id, latest.samples[id]));
}

export function iterationSeries(): IterationPoint[] {
  return ITERATIONS.map((it) => ({
    iteration: it.id,
    date: it.date,
    scores: Object.fromEntries(
      POSE_ORDER.map((id) => [id, buildReport(id, it.samples[id]).score]),
    ) as Record<PoseId, number>,
  }));
}
