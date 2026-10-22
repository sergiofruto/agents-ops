import { toBody } from "@/lib/body";
import { framingOk, inferView } from "@/lib/view";
import { HEIGHT_MAX_CM, HEIGHT_MIN_CM } from "./config";
import type { PhotoInput } from "./findings";
import { earToFloorPx, facesCamera, type PostureView } from "./frame";

export type StepRejection =
  | "no_person"
  | "multiple_people"
  | "framing"
  | "wrong_view_side"
  | "wrong_view_front"
  | "looks_like_back"
  | "looks_like_front"
  | "duplicate";

export const REJECTION_MESSAGE: Record<StepRejection, string> = {
  no_person: "We couldn't find a person. Step back so your whole body is in frame.",
  multiple_people: "Make sure you're alone in the frame.",
  framing: "Step back so your whole body, including your feet, is in frame.",
  wrong_view_side: "Turn a bit more to the side of the camera.",
  wrong_view_front: "Turn a bit more to face the camera.",
  looks_like_back: "This looks like a back photo. Face the camera.",
  looks_like_front: "We can see your face. Turn your back to the camera.",
  duplicate: "You already used this photo for another view. Upload a different one.",
};

export function validateStep(
  view: PostureView,
  photo: PhotoInput,
  opts: { fingerprint?: string; otherFingerprints?: string[] } = {},
): { ok: true } | { ok: false; reason: StepRejection } {
  const fail = (reason: StepRejection) => ({ ok: false as const, reason });
  if (photo.people.length === 0) return fail("no_person");
  if (photo.people.length > 1) return fail("multiple_people");

  const body = toBody(photo.people[0], photo.width, photo.height);
  if (!framingOk(body) || earToFloorPx(body) === null) return fail("framing");

  const seen = inferView(body);
  if (view === "side" && seen !== "side") return fail("wrong_view_side");
  if (view !== "side" && seen !== "front") return fail("wrong_view_front");

  // Front and back have the same shape; orientation decides (null = unsure, retake).
  const facing = view === "side" ? null : facesCamera(body);
  if (view === "front" && facing !== true) return fail("looks_like_back");
  if (view === "back" && facing !== false) return fail("looks_like_front");

  if (opts.fingerprint && opts.otherFingerprints?.includes(opts.fingerprint)) return fail("duplicate");
  return { ok: true };
}

/** Whole centimeters within the allowed range, else null. */
export function validHeight(input: string): number | null {
  const t = input.trim();
  if (!/^\d+$/.test(t)) return null;
  const n = Number(t);
  return n >= HEIGHT_MIN_CM && n <= HEIGHT_MAX_CM ? n : null;
}
