import { expect, test } from "vitest";
import { targetSize } from "@/lib/posture/image";

test("large photos scale down to 1280 px on the long side", () => {
  expect(targetSize(4912, 7360)).toEqual({ width: 854, height: 1280 });
  expect(targetSize(826, 1752)).toEqual({ width: 603, height: 1280 });
  expect(targetSize(7360, 4912)).toEqual({ width: 1280, height: 854 });
});

test("small photos are never upscaled", () => {
  expect(targetSize(425, 740)).toEqual({ width: 425, height: 740 });
  expect(targetSize(1080, 1080)).toEqual({ width: 1080, height: 1080 });
});
