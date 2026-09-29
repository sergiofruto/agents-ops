import type { Body } from "./body";
import type { CheckDef, Mode, PoseDef } from "./poses";

export type Measurement = { checkId: string; value: number | null };
export type CheckStatus = "pass" | "partial" | "fail" | "not_measured";

export type CheckResult = {
  id: string;
  label: string;
  cue: string;
  unit: "deg" | "ratio";
  weight: number;
  value: number | null;
  credit: number | null;
  status: CheckStatus;
  targetText: string;
};

export type ScoreResult = { score: number | null; checks: CheckResult[] };

export function checkCredit(check: CheckDef, value: number): number {
  if (check.kind === "min") return value >= check.min ? 1 : 0;
  const d = Math.abs(value - check.target);
  if (d <= check.tol) return 1;
  if (d >= 2 * check.tol) return 0;
  return 1 - (d - check.tol) / check.tol;
}

export function applicableChecks(pose: PoseDef, mode: Mode): CheckDef[] {
  return pose.checks.filter((c) => mode === "live" || c.source === "frame");
}

export function measureFrame(pose: PoseDef, body: Body, mode: Mode): Measurement[] {
  const roles = pose.assignRoles(body);
  return applicableChecks(pose, mode).map((c) => {
    if (c.source === "window") return { checkId: c.id, value: null };
    const measurable = c.required(roles).every((j) => body.usable(j));
    const value = measurable ? c.measure(body, roles) : null;
    return { checkId: c.id, value: value !== null && Number.isFinite(value) ? value : null };
  });
}

function targetText(c: CheckDef): string {
  const u = c.unit === "deg" ? "°" : "";
  return c.kind === "range" ? `${c.target}${u} ± ${c.tol}${u}` : `≥ ${c.min}${u}`;
}

/** Pure scoring from values. Safe to run on the server with client-supplied measurements. */
export function scoreMeasurements(
  pose: PoseDef,
  measurements: Measurement[],
  mode: Mode,
): ScoreResult {
  const byId = new Map(measurements.map((m) => [m.checkId, m.value]));
  let weightSum = 0;
  let creditSum = 0;
  const checks = applicableChecks(pose, mode).map((c): CheckResult => {
    const value = byId.get(c.id) ?? null;
    const credit = value === null ? null : checkCredit(c, value);
    if (credit !== null) {
      weightSum += c.weight;
      creditSum += c.weight * credit;
    }
    const status: CheckStatus =
      credit === null ? "not_measured" : credit >= 1 ? "pass" : credit > 0 ? "partial" : "fail";
    return {
      id: c.id,
      label: c.label,
      cue: c.cue,
      unit: c.unit,
      weight: c.weight,
      value,
      credit,
      status,
      targetText: targetText(c),
    };
  });
  return {
    score: weightSum === 0 ? null : Math.round((100 * creditSum) / weightSum),
    checks,
  };
}
