import { describe, expect, test } from "vitest";
import {
  angle,
  distance,
  distanceToLine,
  midpoint,
  tiltFromHorizontal,
  tiltFromVertical,
} from "@/lib/geometry";
import { joint, other, partOf, sideOf } from "@/lib/landmarks";

describe("angle", () => {
  test("right angle", () => {
    expect(angle({ x: 10, y: 0 }, { x: 0, y: 0 }, { x: 0, y: 10 })).toBeCloseTo(90, 6);
  });
  test("straight line", () => {
    expect(angle({ x: -5, y: 0 }, { x: 0, y: 0 }, { x: 7, y: 0 })).toBeCloseTo(180, 6);
  });
  test("45 degrees", () => {
    expect(angle({ x: 10, y: 0 }, { x: 0, y: 0 }, { x: 10, y: 10 })).toBeCloseTo(45, 6);
  });
  test("degenerate segment returns NaN", () => {
    expect(angle({ x: 0, y: 0 }, { x: 0, y: 0 }, { x: 1, y: 1 })).toBeNaN();
  });
});

describe("tilts", () => {
  test("horizontal segment", () => {
    expect(tiltFromHorizontal({ x: 0, y: 0 }, { x: 10, y: 0 })).toBeCloseTo(0, 6);
    expect(tiltFromVertical({ x: 0, y: 0 }, { x: 10, y: 0 })).toBeCloseTo(90, 6);
  });
  test("vertical segment", () => {
    expect(tiltFromHorizontal({ x: 0, y: 0 }, { x: 0, y: 10 })).toBeCloseTo(90, 6);
    expect(tiltFromVertical({ x: 0, y: 10 }, { x: 0, y: 0 })).toBeCloseTo(0, 6);
  });
  test("tilts are unsigned (direction does not matter)", () => {
    expect(tiltFromHorizontal({ x: 10, y: 10 }, { x: 0, y: 0 })).toBeCloseTo(45, 6);
    expect(tiltFromHorizontal({ x: 0, y: 10 }, { x: 10, y: 0 })).toBeCloseTo(45, 6);
  });
  test("degenerate segment returns NaN", () => {
    expect(tiltFromVertical({ x: 3, y: 3 }, { x: 3, y: 3 })).toBeNaN();
  });
});

describe("distances", () => {
  test("distance and midpoint", () => {
    expect(distance({ x: 0, y: 0 }, { x: 3, y: 4 })).toBe(5);
    expect(midpoint({ x: 0, y: 0 }, { x: 4, y: 2 })).toEqual({ x: 2, y: 1 });
  });
  test("distanceToLine is perpendicular distance in pixels", () => {
    expect(distanceToLine({ x: 5, y: 5 }, { x: 0, y: 0 }, { x: 10, y: 0 })).toBeCloseTo(5, 6);
    expect(distanceToLine({ x: 5, y: 0 }, { x: 0, y: 0 }, { x: 10, y: 0 })).toBeCloseTo(0, 6);
  });
});

describe("landmark helpers", () => {
  test("joint/other/sideOf/partOf", () => {
    expect(joint("left", "Knee")).toBe("leftKnee");
    expect(other("left")).toBe("right");
    expect(sideOf("rightAnkle")).toBe("right");
    expect(sideOf("nose")).toBeNull();
    expect(partOf("leftWrist")).toBe("Wrist");
    expect(partOf("nose")).toBeNull();
  });
});
