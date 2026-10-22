import type { PhotoInput } from "./findings";
import type { PostureView } from "./frame";

export type PhotoState = { input: PhotoInput; url: string; fingerprint: string };

export type FlowStep = "height" | PostureView | "results";

export type FlowState = {
  step: FlowStep;
  heightCm: number | null;
  photos: Partial<Record<PostureView, PhotoState>>;
};

export type FlowAction =
  | { type: "setHeight"; heightCm: number }
  | { type: "acceptPhoto"; view: PostureView; photo: PhotoState }
  | { type: "goTo"; step: FlowStep }
  | { type: "reset" };

export const initialFlow: FlowState = { step: "height", heightCm: null, photos: {} };

const VIEWS: PostureView[] = ["front", "side", "back"];

export function canShowResults(s: FlowState): boolean {
  return s.heightCm !== null && VIEWS.every((v) => s.photos[v]);
}

/** The first step still missing input, or results when everything is in. */
function nextStep(s: FlowState): FlowStep {
  if (s.heightCm === null) return "height";
  return VIEWS.find((v) => !s.photos[v]) ?? "results";
}

/** Results are never stored: they're derived from height and photos, so they can't go stale. */
export function flowReducer(s: FlowState, a: FlowAction): FlowState {
  switch (a.type) {
    case "setHeight": {
      const next = { ...s, heightCm: a.heightCm };
      return { ...next, step: nextStep(next) };
    }
    case "acceptPhoto": {
      const next = { ...s, photos: { ...s.photos, [a.view]: a.photo } };
      return { ...next, step: nextStep(next) };
    }
    case "goTo":
      if (a.step === "results" && !canShowResults(s)) return s;
      if (a.step !== "height" && s.heightCm === null) return s;
      return { ...s, step: a.step };
    case "reset":
      return initialFlow;
  }
}
