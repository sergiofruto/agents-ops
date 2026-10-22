import type { Joint } from "@/lib/landmarks";
import { joint } from "@/lib/landmarks";
import { nearSide } from "@/lib/poses/helpers";
import type { FindingId } from "./config";
import type { Finding, PostureStatus } from "./findings";
import type { PostureFrame } from "./frame";

export type PostureLine = { x1: number; y1: number; x2: number; y2: number; status: PostureStatus; dashed?: boolean };
export type PostureDot = { x: number; y: number; status: PostureStatus };
export type PostureOverlayGeometry = { lines: PostureLine[]; dots: PostureDot[] };

const statusOf = (findings: Finding[], id: FindingId): PostureStatus =>
  findings.find((f) => f.id === id)?.status ?? "not_measured";

/** Front/back: level lines across ears, shoulders and hips, plus a dashed midline through the hips. */
export function coronalOverlay(frame: PostureFrame, findings: Finding[]): PostureOverlayGeometry {
  const { body } = frame;
  const lines: PostureLine[] = [];
  const dots: PostureDot[] = [];
  const pairs: [Joint, Joint, FindingId][] = [
    ["leftEar", "rightEar", "headTilt"],
    ["leftShoulder", "rightShoulder", "shoulderLevel"],
    ["leftHip", "rightHip", "hipLevel"],
  ];
  for (const [a, b, id] of pairs) {
    if (!body.usable(a) || !body.usable(b)) continue;
    const p = body.point(a);
    const q = body.point(b);
    const status = statusOf(findings, id);
    lines.push({ x1: p.x, y1: p.y, x2: q.x, y2: q.y, status });
    dots.push({ ...p, status }, { ...q, status });
  }
  if (body.usable("leftHip") && body.usable("rightHip")) {
    const x = body.hipMid.x;
    lines.push({ x1: x, y1: body.bbox.minY, x2: x, y2: body.bbox.maxY, status: statusOf(findings, "trunkShift"), dashed: true });
  }
  return { lines, dots };
}

/** Side: dashed plumb line through the near ankle and status-colored dots on ear, shoulder, hip, knee. */
export function sagittalOverlay(frame: PostureFrame, findings: Finding[]): PostureOverlayGeometry {
  const { body } = frame;
  const s = nearSide(body);
  const lines: PostureLine[] = [];
  const dots: PostureDot[] = [];
  const ankle = joint(s, "Ankle");
  if (body.usable(ankle)) {
    const x = body.point(ankle).x;
    lines.push({ x1: x, y1: 0, x2: x, y2: body.height, status: "aligned", dashed: true });
  }
  const marks: ["Ear" | "Shoulder" | "Hip" | "Knee", FindingId][] = [
    ["Ear", "forwardHead"],
    ["Shoulder", "forwardHead"],
    ["Hip", "hipsForward"],
    ["Knee", "kneeHyperextension"],
  ];
  for (const [part, id] of marks) {
    const j = joint(s, part);
    if (body.usable(j)) dots.push({ ...body.point(j), status: statusOf(findings, id) });
  }
  return { lines, dots };
}
