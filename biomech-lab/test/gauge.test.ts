import { expect, test } from "vitest";
import { gaugeGeometry } from "@/lib/gauge";

test("maps band, partial band and value onto 0..180°", () => {
  expect(gaugeGeometry(90, 10, 167)).toEqual({
    value: 167 / 180,
    band: [80 / 180, 100 / 180],
    partial: [70 / 180, 110 / 180],
  });
});

test("clamps to the 0..180° domain", () => {
  expect(gaugeGeometry(180, 10, 200)).toEqual({ value: 1, band: [170 / 180, 1], partial: [160 / 180, 1] });
  expect(gaugeGeometry(0, 10, -5)).toEqual({ value: 0, band: [0, 10 / 180], partial: [0, 20 / 180] });
});
