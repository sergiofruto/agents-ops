import { describe, expect, test } from "vitest";
import { FINDINGS, type FindingId } from "@/lib/posture/config";
import { combineFrontBack, scoreFindings, statusFor, type Finding, type PostureStatus } from "@/lib/posture/findings";

describe("statusFor", () => {
  test("one-sided forward head", () => {
    expect(statusFor("forwardHead", 2.5)).toBe("aligned");
    expect(statusFor("forwardHead", 2.6)).toBe("slight");
    expect(statusFor("forwardHead", 5.1)).toBe("needs_work");
    expect(statusFor("forwardHead", -3)).toBe("aligned");
    expect(statusFor("forwardHead", null)).toBe("not_measured");
  });

  test("two-sided findings use the magnitude", () => {
    expect(statusFor("shoulderLevel", -4.5)).toBe("needs_work");
    expect(statusFor("shoulderLevel", -3)).toBe("slight");
  });
});

describe("combineFrontBack", () => {
  test("agreeing views average", () => {
    expect(combineFrontBack("shoulderLevel", 3, 1)).toEqual({ value: 2, status: "aligned", disagree: false });
    expect(combineFrontBack("shoulderLevel", 4, 2)).toEqual({ value: 3, status: "slight", disagree: false });
  });

  test("small opposite readings near zero are noise", () => {
    expect(combineFrontBack("shoulderLevel", 0.5, -0.5)).toEqual({ value: 0, status: "aligned", disagree: false });
  });

  test("clear disagreement caps needs work to slight", () => {
    expect(combineFrontBack("shoulderLevel", 11, -1)).toEqual({ value: 5, status: "slight", disagree: true });
  });

  test("clear disagreement lifts a cancelled mean to slight", () => {
    expect(combineFrontBack("shoulderLevel", 3, -3)).toEqual({ value: 0, status: "slight", disagree: true });
  });

  test("one missing view uses the other", () => {
    expect(combineFrontBack("hipLevel", null, 5)).toEqual({ value: 5, status: "needs_work", disagree: false });
    expect(combineFrontBack("hipLevel", null, null)).toEqual({ value: null, status: "not_measured", disagree: false });
  });
});

const all = (status: PostureStatus, overrides: Partial<Record<FindingId, PostureStatus>> = {}): Finding[] =>
  (Object.keys(FINDINGS) as FindingId[]).map((id) => ({
    id,
    region: FINDINGS[id].region,
    unit: FINDINGS[id].unit,
    value: 0,
    perView: {},
    status: overrides[id] ?? status,
    disagree: false,
    side: null,
  }));

describe("scoreFindings", () => {
  test("all aligned scores 100", () => expect(scoreFindings(all("aligned"))).toBe(100));
  test("forward head needs work costs its 20 points", () =>
    expect(scoreFindings(all("aligned", { forwardHead: "needs_work" }))).toBe(80));
  test("slight earns half", () => expect(scoreFindings(all("aligned", { forwardHead: "slight" }))).toBe(90));
  test("unmeasured findings are left out of the total", () =>
    expect(scoreFindings(all("aligned", { forwardHead: "not_measured" }))).toBe(100));
  test("nothing measured gives no score", () => expect(scoreFindings(all("not_measured"))).toBeNull());
});
