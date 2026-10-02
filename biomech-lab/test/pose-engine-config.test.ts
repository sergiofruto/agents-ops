import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "vitest";
import { MEDIAPIPE_VERSION, WASM_URL } from "@/lib/pose-engine-config";

test("WASM URL is pinned to the installed @mediapipe/tasks-vision version", () => {
  const pkg = JSON.parse(
    readFileSync(
      path.join(process.cwd(), "node_modules/@mediapipe/tasks-vision/package.json"),
      "utf8",
    ),
  ) as { version: string };
  expect(MEDIAPIPE_VERSION).toBe(pkg.version);
  expect(WASM_URL).toContain(`@${pkg.version}/wasm`);
});
