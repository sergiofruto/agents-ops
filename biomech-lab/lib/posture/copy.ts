import type { Finding } from "./findings";

/** Nearest half centimeter, unsigned. */
export function formatCm(v: number): string {
  return `${Math.round(Math.abs(v) * 2) / 2} cm`;
}

/** Whole degrees, unsigned. */
export function formatDeg(v: number): string {
  return `${Math.round(Math.abs(v))}°`;
}

const otherSide = (s: "left" | "right") => (s === "left" ? "right" : "left");

function level(part: "shoulder" | "hip", f: Finding, v: number): string {
  if (f.status === "aligned" || !f.side) return `Your ${part}s are level.`;
  const drop = f.extra?.dropCm;
  const size = drop !== null && drop !== undefined ? `about ${formatCm(drop)} ` : "";
  return `Your ${f.side} ${part} sits ${size}lower than your ${otherSide(f.side)} (${formatDeg(v)}).`;
}

/** One plain sentence describing what was measured; "" when the finding wasn't measured. */
export function measuredSentence(f: Finding): string {
  if (f.status === "not_measured" || f.value === null) return "";
  const v = f.value;
  const off = f.status !== "aligned";
  switch (f.id) {
    case "forwardHead":
      return off && v > 0
        ? `Your ear sits about ${formatCm(v)} ahead of your shoulder line.`
        : "Your ear sits over your shoulder line.";
    case "headTilt":
      return off && f.side
        ? `Your head tilts about ${formatDeg(v)} toward your ${f.side} shoulder.`
        : "Your head sits level.";
    case "shoulderLevel":
      return level("shoulder", f, v);
    case "hipLevel":
      return level("hip", f, v);
    case "trunkShift":
      return off && f.side
        ? `Your shoulders sit about ${formatCm(v)} to the ${f.side} of your hips.`
        : "Your shoulders stack over your hips.";
    case "hipsForward":
      return off && v > 0
        ? `Your hips sit about ${formatCm(v)} ahead of your ankles.`
        : "Your hips sit over your ankles.";
    case "kneeHyperextension":
      return off && v > 0 ? `Your knee bends back about ${formatDeg(v)} past straight.` : "Your knee sits straight.";
    case "heelAlignment":
      return off && f.side
        ? `Your ${f.side} heel tilts about ${formatDeg(v)} from vertical.`
        : "Your heels sit upright.";
  }
}
