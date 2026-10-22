import { toBody } from "@/lib/body";
import type { RawLandmark } from "@/lib/landmarks";
import { FINDINGS, REGION_ORDER, type FindingId, type Region } from "./config";
import { makeFrame } from "./frame";
import { measureCoronal, measureSagittal, type CoronalMeasures } from "./measure";

export type PostureStatus = "aligned" | "slight" | "needs_work" | "not_measured";

export type Finding = {
  id: FindingId;
  region: Region;
  unit: "cm" | "deg";
  /** Signed value (the front/back mean for findings seen in both). */
  value: number | null;
  perView: Partial<Record<"front" | "side" | "back", number | null>>;
  status: PostureStatus;
  /** Front and back point in opposite directions and at least one is outside the aligned band. */
  disagree: boolean;
  /** The client's side the finding refers to (lower, shifted toward, worse heel); null if not lateral. */
  side: "right" | "left" | null;
  extra?: { dropCm?: number | null; earShoulderAngle?: number | null };
};

export type PostureResult = { score: number | null; findings: Finding[] };

export type PhotoInput = { people: RawLandmark[][]; width: number; height: number };

const CREDIT: Record<Exclude<PostureStatus, "not_measured">, number> = { aligned: 1, slight: 0.5, needs_work: 0 };

export function statusFor(id: FindingId, value: number | null): PostureStatus {
  if (value === null || !Number.isFinite(value)) return "not_measured";
  const def = FINDINGS[id];
  const v = def.oneSided ? Math.max(0, value) : Math.abs(value);
  if (v <= def.aligned) return "aligned";
  if (v <= def.slight) return "slight";
  return "needs_work";
}

export function combineFrontBack(
  id: FindingId,
  front: number | null,
  back: number | null,
): { value: number | null; status: PostureStatus; disagree: boolean } {
  if (front === null || back === null) {
    const value = front ?? back;
    return { value, status: statusFor(id, value), disagree: false };
  }
  const value = (front + back) / 2;
  const aligned = FINDINGS[id].aligned;
  const disagree = Math.sign(front) * Math.sign(back) < 0 && Math.max(Math.abs(front), Math.abs(back)) > aligned;
  return { value, status: disagree ? "slight" : statusFor(id, value), disagree };
}

export function scoreFindings(findings: Finding[]): number | null {
  let weightSum = 0;
  let creditSum = 0;
  for (const f of findings) {
    if (f.status === "not_measured") continue;
    weightSum += FINDINGS[f.id].weight;
    creditSum += FINDINGS[f.id].weight * CREDIT[f.status];
  }
  return weightSum === 0 ? null : Math.round((100 * creditSum) / weightSum);
}

const sideOf = (v: number | null): Finding["side"] => (v === null || v === 0 ? null : v > 0 ? "right" : "left");

function base(id: FindingId): Pick<Finding, "id" | "region" | "unit"> {
  return { id, region: FINDINGS[id].region, unit: FINDINGS[id].unit };
}

function single(id: FindingId, view: "side" | "back", value: number | null, side: Finding["side"] = null): Finding {
  return { ...base(id), value, perView: { [view]: value }, status: statusFor(id, value), disagree: false, side };
}

function lateral(
  id: "headTilt" | "shoulderLevel" | "trunkShift" | "hipLevel",
  front: CoronalMeasures,
  back: CoronalMeasures,
): Finding {
  const c = combineFrontBack(id, front[id], back[id]);
  const drop = (k: "shoulderDropCm" | "hipDropCm") => {
    const vals = [front[k], back[k]].filter((v): v is number => v !== null);
    return vals.length === 0 ? null : vals.reduce((a, b) => a + b, 0) / vals.length;
  };
  const extra =
    id === "shoulderLevel" ? { dropCm: drop("shoulderDropCm") } : id === "hipLevel" ? { dropCm: drop("hipDropCm") } : undefined;
  return {
    ...base(id),
    value: c.value,
    perView: { front: front[id], back: back[id] },
    status: c.status,
    disagree: c.disagree,
    side: sideOf(c.value),
    ...(extra ? { extra } : {}),
  };
}

export function assessPosture(input: {
  heightCm: number;
  front: PhotoInput;
  side: PhotoInput;
  back: PhotoInput;
}): PostureResult {
  const frame = (view: "front" | "side" | "back", p: PhotoInput) =>
    makeFrame(view, toBody(p.people[0], p.width, p.height), input.heightCm);
  const front = measureCoronal(frame("front", input.front));
  const back = measureCoronal(frame("back", input.back));
  const side = measureSagittal(frame("side", input.side));

  const byId: Record<FindingId, Finding> = {
    forwardHead: { ...single("forwardHead", "side", side.forwardHead), extra: { earShoulderAngle: side.earShoulderAngle } },
    headTilt: lateral("headTilt", front, back),
    shoulderLevel: lateral("shoulderLevel", front, back),
    trunkShift: lateral("trunkShift", front, back),
    hipLevel: lateral("hipLevel", front, back),
    hipsForward: single("hipsForward", "side", side.hipsForward),
    kneeHyperextension: single("kneeHyperextension", "side", side.kneeHyperextension),
    heelAlignment: single("heelAlignment", "back", back.heelAlignment?.deg ?? null, back.heelAlignment?.side ?? null),
  };

  const ids = Object.keys(FINDINGS) as FindingId[];
  const findings = REGION_ORDER.flatMap((r) => ids.filter((id) => FINDINGS[id].region === r).map((id) => byId[id]));
  return { score: scoreFindings(findings), findings };
}
