import { describe, expect, test } from "vitest";
import { TELEMETRY_ORIGIN, connectSources, contentSecurityPolicy } from "@/lib/csp";
import { MODEL_URL, WASM_URL } from "@/lib/pose-engine-config";

describe("content security policy", () => {
  test("allows the app itself and the MediaPipe asset origins", () => {
    const sources = connectSources(false);
    expect(sources).toContain("'self'");
    expect(sources).toContain(new URL(WASM_URL).origin);
    expect(sources).toContain(new URL(MODEL_URL).origin);
  });

  test("production allows nothing else (telemetry origin is blocked)", () => {
    expect(connectSources(false)).toHaveLength(3);
    expect(contentSecurityPolicy(false)).not.toContain(new URL(TELEMETRY_ORIGIN).host);
    expect(contentSecurityPolicy(false)).not.toContain("googleapis.com/v1");
  });

  test("development additionally allows the local HMR websocket", () => {
    expect(connectSources(true)).toContain("ws://localhost:*");
    expect(connectSources(false)).not.toContain("ws://localhost:*");
  });

  test("header value is a single connect-src directive", () => {
    expect(contentSecurityPolicy(false)).toBe(
      `connect-src 'self' ${new URL(WASM_URL).origin} ${new URL(MODEL_URL).origin}`,
    );
  });
});
