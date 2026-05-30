import { createHmac, timingSafeEqual } from "crypto";

const COOKIE = "solaris_auth";

function sign(value: string): string {
  const sig = createHmac("sha256", process.env.AUTH_SECRET!).update(value).digest("hex");
  return `${value}.${sig}`;
}

export function makeSessionCookie(): { name: string; value: string } {
  return { name: COOKIE, value: sign("ok") };
}

export function isValidCookie(raw: string | undefined): boolean {
  if (!raw) return false;
  const [value, sig] = raw.split(".");
  if (!value || !sig) return false;
  const expected = createHmac("sha256", process.env.AUTH_SECRET!).update(value).digest("hex");
  try {
    return value === "ok" && timingSafeEqual(Buffer.from(sig), Buffer.from(expected));
  } catch { return false; }
}

export function checkPassword(input: string): boolean {
  const expected = process.env.SOLARIS_PASSWORD ?? "";
  if (input.length !== expected.length) return false;
  return timingSafeEqual(Buffer.from(input), Buffer.from(expected));
}

export const COOKIE_NAME = COOKIE;
