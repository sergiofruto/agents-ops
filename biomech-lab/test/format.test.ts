import { expect, test } from "vitest";
import { countWord } from "@/lib/format";

test("spells out small counts", () => {
  expect(countWord(3)).toBe("Three");
});

test("falls back to the digit outside the known range", () => {
  expect(countWord(7)).toBe("7");
});
