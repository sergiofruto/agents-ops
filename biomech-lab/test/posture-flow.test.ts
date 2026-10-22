import { expect, test } from "vitest";
import { canShowResults, flowReducer, initialFlow, type FlowState, type PhotoState } from "@/lib/posture/flow";

const VIEW_OF: Record<string, PhotoState["view"]> = { f: "front", f2: "front", s: "side", b: "back" };

const photo = (id: string, view: PhotoState["view"] = VIEW_OF[id]): PhotoState => ({
  view,
  input: { people: [], width: 1, height: 1 },
  url: `blob:${id}`,
  fingerprint: id,
});

function complete(): FlowState {
  let s = flowReducer(initialFlow, { type: "setHeight", heightCm: 175 });
  s = flowReducer(s, { type: "acceptPhoto", view: "front", photo: photo("f") });
  s = flowReducer(s, { type: "acceptPhoto", view: "side", photo: photo("s") });
  return flowReducer(s, { type: "acceptPhoto", view: "back", photo: photo("b") });
}

test("height then front, side and back lands on results", () => {
  let s = flowReducer(initialFlow, { type: "setHeight", heightCm: 175 });
  expect(s.step).toBe("front");
  s = flowReducer(s, { type: "acceptPhoto", view: "front", photo: photo("f") });
  expect(s.step).toBe("side");
  s = flowReducer(s, { type: "acceptPhoto", view: "side", photo: photo("s") });
  expect(s.step).toBe("back");
  s = flowReducer(s, { type: "acceptPhoto", view: "back", photo: photo("b") });
  expect(s.step).toBe("results");
  expect(canShowResults(s)).toBe(true);
});

test("replacing the front photo from results keeps the others and returns to results", () => {
  let s = flowReducer(complete(), { type: "goTo", step: "front" });
  expect(s.step).toBe("front");
  s = flowReducer(s, { type: "acceptPhoto", view: "front", photo: photo("f2") });
  expect(s.step).toBe("results");
  expect(s.photos.front?.fingerprint).toBe("f2");
  expect(s.photos.side?.fingerprint).toBe("s");
});

test("changing height after results goes straight back to results", () => {
  let s = flowReducer(complete(), { type: "goTo", step: "height" });
  s = flowReducer(s, { type: "setHeight", heightCm: 160 });
  expect(s.step).toBe("results");
  expect(s.heightCm).toBe(160);
});

test("results can't be reached before all photos are in", () => {
  const s = flowReducer(flowReducer(initialFlow, { type: "setHeight", heightCm: 175 }), { type: "goTo", step: "results" });
  expect(s.step).toBe("front");
});

test("photo steps can't be reached before the height is set", () => {
  expect(flowReducer(initialFlow, { type: "goTo", step: "side" }).step).toBe("height");
});

test("reset returns to the start", () => {
  expect(flowReducer(complete(), { type: "reset" })).toEqual(initialFlow);
});

test("a photo checked for another view is never accepted", () => {
  const atFront = flowReducer(initialFlow, { type: "setHeight", heightCm: 175 });
  const stale = flowReducer(atFront, { type: "acceptPhoto", view: "front", photo: photo("s", "side") });
  expect(stale).toBe(atFront);
  const offStep = flowReducer(atFront, { type: "acceptPhoto", view: "side", photo: photo("s") });
  expect(offStep).toBe(atFront);
});
