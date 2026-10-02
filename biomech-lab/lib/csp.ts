import { MODEL_URL, WASM_URL } from "./pose-engine-config";

/**
 * MediaPipe tasks-vision ships a built-in usage logger that posts to this origin and
 * has no opt-out. It is deliberately NOT in the allow-list below.
 */
export const TELEMETRY_ORIGIN = "https://odml.pa.googleapis.com";

/**
 * Origins the browser may contact via fetch/XHR/WebSocket. Images never leave the page.
 *
 * Day 2 note: adopting Vercel Analytics, Speed Insights, or the vercel.live preview
 * toolbar will each need their own origins allow-listed here (and in a script-src
 * directive, which this policy does not yet set) — they are not included today.
 */
export function connectSources(dev: boolean): string[] {
  const sources = ["'self'", new URL(WASM_URL).origin, new URL(MODEL_URL).origin];
  return dev ? [...sources, "ws://localhost:*"] : sources;
}

export function contentSecurityPolicy(dev: boolean): string {
  return `connect-src ${connectSources(dev).join(" ")}`;
}
