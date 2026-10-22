import { describe, expect, test } from "vitest";
import { FINDINGS, type FindingId } from "@/lib/posture/config";
import { formatCm, formatDeg, measuredSentence } from "@/lib/posture/copy";
import { LIBRARY } from "@/lib/posture/exercises";
import type { Finding, PostureStatus } from "@/lib/posture/findings";

const IDS = Object.keys(FINDINGS) as FindingId[];

const finding = (
  id: FindingId,
  value: number,
  status: PostureStatus,
  side: Finding["side"] = null,
  extra?: Finding["extra"],
): Finding => ({
  id,
  region: FINDINGS[id].region,
  unit: FINDINGS[id].unit,
  value,
  perView: {},
  status,
  disagree: false,
  side,
  ...(extra ? { extra } : {}),
});

/** One off-finding per id and side, plus an aligned one, to render every template. */
const SAMPLES: Finding[] = IDS.flatMap((id) => [
  finding(id, 6, "needs_work", FINDINGS[id].oneSided ? null : "right", { dropCm: 1.2, earShoulderAngle: 44 }),
  finding(id, -6, "needs_work", FINDINGS[id].oneSided ? null : "left", { dropCm: -1.2 }),
  finding(id, 0.5, "aligned", null),
]);

const FORBIDDEN = ["—", "diagnos", "scoliosis", "kyphosis", "you have"];

describe("formatting", () => {
  test("cm round to the nearest half", () => {
    expect(formatCm(4.3)).toBe("4.5 cm");
    expect(formatCm(2.6)).toBe("2.5 cm");
    expect(formatCm(1.2)).toBe("1 cm");
    expect(formatCm(-3.1)).toBe("3 cm");
  });
  test("degrees round to whole numbers", () => expect(formatDeg(3.4)).toBe("3°"));
});

describe("measuredSentence", () => {
  test("forward head reads in cm", () =>
    expect(measuredSentence(finding("forwardHead", 4.3, "slight"))).toBe(
      "Your ear sits about 4.5 cm ahead of your shoulder line.",
    ));

  test("shoulder level names the lower side with cm and degrees", () =>
    expect(measuredSentence(finding("shoulderLevel", 3, "slight", "right", { dropCm: 1.2 }))).toBe(
      "Your right shoulder sits about 1 cm lower than your left (3°).",
    ));

  test("left side is templated", () =>
    expect(measuredSentence(finding("shoulderLevel", -3, "slight", "left", { dropCm: -1.2 }))).toContain(
      "left shoulder",
    ));

  test("not measured gives an empty sentence", () =>
    expect(measuredSentence(finding("headTilt", 0, "not_measured"))).toBe(""));
});

describe("exercise library", () => {
  test.each(IDS)("%s has an explanation and exactly 3 complete exercises", (id) => {
    const f = finding(id, 6, "needs_work", FINDINGS[id].oneSided ? null : "right", { dropCm: 1.2 });
    expect(LIBRARY[id].explanation(f).length).toBeGreaterThan(40);
    const ex = LIBRARY[id].exercises(f);
    expect(ex).toHaveLength(3);
    for (const e of ex) {
      expect(e.name.length).toBeGreaterThan(3);
      expect(e.steps.length).toBeGreaterThanOrEqual(2);
      expect(e.dosage.length).toBeGreaterThan(3);
    }
  });

  test("shoulder exercises follow the lower side", () => {
    const text = (side: "left" | "right") =>
      JSON.stringify(LIBRARY.shoulderLevel.exercises(finding("shoulderLevel", side === "right" ? 3 : -3, "slight", side)));
    expect(text("left")).toContain("left");
    expect(text("right")).toContain("right");
    expect(text("left")).not.toBe(text("right"));
  });

  test("no copy uses em dashes or diagnostic language", () => {
    for (const f of SAMPLES) {
      const all = [measuredSentence(f), LIBRARY[f.id].explanation(f), JSON.stringify(LIBRARY[f.id].exercises(f))]
        .join(" ")
        .toLowerCase();
      for (const word of FORBIDDEN) expect(all, `${f.id}: ${word}`).not.toContain(word);
    }
  });
});
