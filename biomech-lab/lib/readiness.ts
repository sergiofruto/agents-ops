import type { Body } from "./body";
import type { Joint } from "./landmarks";
import type { Mode, PoseDef } from "./poses";
import { applicableChecks } from "./score";
import { framingOk, inferView, type View } from "./view";

export const MIN_COVERAGE = 0.7;

export type ReadinessReason =
  | "no_person"
  | "multiple_people"
  | "wrong_view"
  | "bad_framing"
  | "low_coverage";

export type AssessmentReadiness = {
  canScore: boolean;
  view: View;
  coverage: number;
  reasons: ReadinessReason[];
  missing: Joint[];
};

export function assessReadiness(input: {
  peopleCount: number;
  body: Body | null;
  pose: PoseDef;
  mode: Mode;
}): AssessmentReadiness {
  const { peopleCount, body, pose, mode } = input;
  if (peopleCount === 0 || body === null) {
    return { canScore: false, view: "ambiguous", coverage: 0, reasons: ["no_person"], missing: [] };
  }

  const reasons: ReadinessReason[] = [];
  if (peopleCount > 1) reasons.push("multiple_people");

  const view = inferView(body);
  if (view !== pose.view) reasons.push("wrong_view");
  if (!framingOk(body)) reasons.push("bad_framing");

  const roles = pose.assignRoles(body);
  const checks = applicableChecks(pose, mode);
  const total = checks.reduce((sum, c) => sum + c.weight, 0);
  const missing = new Set<Joint>();
  let covered = 0;
  for (const c of checks) {
    const unusable = c.required(roles).filter((j) => !body.usable(j));
    unusable.forEach((j) => missing.add(j));
    if (unusable.length === 0) covered += c.weight;
  }
  const coverage = total === 0 ? 0 : covered / total;
  if (coverage < MIN_COVERAGE) reasons.push("low_coverage");

  return { canScore: reasons.length === 0, view, coverage, reasons, missing: [...missing] };
}
