# Posture Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `/posture` page where a client enters their height, uploads front, side and back photos through guided steps, and gets a 0-100 posture score with findings grouped by body region, each off finding explained with 3 exercises.

**Architecture:** All posture logic is pure TypeScript in `lib/posture/` (measure, classify, combine, score, validate, flow reducer, copy), unit-tested in node with synthetic landmarks and golden landmark files. React components in `components/posture/` only render state and call the existing MediaPipe engine (`createImageEngine()`) on downscaled images. The yoga pose pipeline is untouched.

**Tech Stack:** Next.js 16 (App Router, Turbopack), React, TypeScript, Tailwind v4, `@mediapipe/tasks-vision` 1.0.1, vitest, lucide-react.

**Spec:** `biomech-lab/docs/posture-check-design.md` (read it before starting; this plan argues from it).

## Global Constraints

- All commands run from `biomech-lab/`. Run `npm run typecheck`, `npm run lint`, `npm test`, `npm run build` **one at a time, never in parallel** (16 GB machine; parallel Next jobs froze it).
- Before any `npm run dev`: `rm -rf .next` if the cache predates 2026-10-22, and run the dev server behind a kill switch (stop it if `pgrep -x node | wc -l` > 30 or `memory_pressure` free < 40%).
- Read `node_modules/next/dist/docs/` before writing routing/page code (`AGENTS.md`).
- Photos and height never leave the device. No new network origins (`test/csp.test.ts` must pass).
- Downscale every photo to at most **1280 px on the long side** before detection.
- Height: integer cm, **120-220**, required. No weight.
- UI copy is English. Never use em dashes in copy. Never use diagnostic language ("you have scoliosis/kyphosis").
- Display rounding: cm to nearest 0.5, degrees to whole numbers. **Statuses use raw values.**
- Status labels: "aligned", "slight", "needs work"; colors: pass (cyan) / partial (amber) / fail (rose) tokens.
- Disclaimer text (exact): "This is a screening, not a diagnosis. Spine curves and pelvic tilt aren't measured. If you have pain or numbness, see a kinesiologist or physiotherapist."
- Git: Claude has full git autonomy in `biomech-lab/` on branch `feat/posture-check`. Commit with `git commit -- <paths>` so other staged changes in the monorepo are never swept in. End messages with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Side photo facing left vs right**: every sagittal finding must give the same value for a mirrored side photo (pinned in Task 3).
2. **Feet or heels not usable** (shoes, cropped floor): there is no cm scale; the step must reject with the framing message, not score with NaN (pinned in Task 5).
3. **Changing an earlier photo or the height after results are shown**: results must be invalidated and recomputed, never stale (pinned in Task 5, flow reducer).
4. **Same file on front and back steps**: rejected (pinned in Task 5).
5. **Undecodable or huge images** (HEIC, 36 MP JPEG): a clear message or a downscale, never a hang (pinned in Task 7, `targetSize`; decode failure message in Task 8).

---

## File Structure

| File | Responsibility |
|---|---|
| `lib/landmarks.ts` (modify) | add `leftEye: 2`, `rightEye: 5` |
| `lib/overlay.ts` (modify) | keep eyes out of drawn joints |
| `lib/posture/config.ts` | every threshold, weight and constant from the spec |
| `lib/posture/frame.ts` | per-photo frame: cm scale, anatomical sides, facing direction, face visibility |
| `lib/posture/measure.ts` | raw signed measurements per view |
| `lib/posture/findings.ts` | status per value, front/back combine, findings list, score |
| `lib/posture/validate.ts` | per-step photo validation with reasons and messages |
| `lib/posture/flow.ts` | pure reducer for the step flow |
| `lib/posture/copy.ts` | measured sentences per finding |
| `lib/posture/exercises.ts` | explanation + 3 exercises per finding |
| `lib/posture/overlay.ts` | pure SVG geometry for posture overlays |
| `lib/posture/image.ts` | `targetSize` (pure), `downscaleImage`, `fileFingerprint` (browser) |
| `components/posture/*.tsx` | flow UI and results |
| `app/posture/page.tsx` | route |
| `data/samples/posture/{front,side,back}.json` | golden landmarks |
| `test/posture-*.test.ts` | tests |

---

### Task 1: Eye landmarks

**Files:**
- Modify: `lib/landmarks.ts` (`JOINT_INDEX`), `lib/overlay.ts:26` (`OVERLAY_JOINTS`)
- Test: `test/overlay.test.ts`

**Interfaces:**
- Produces: `Joint` now includes `"leftEye" | "rightEye"`.

- [ ] **Step 1: Write the failing test** in `test/overlay.test.ts`:

```ts
test("eyes are indexed but never drawn as joints", () => {
  expect(JOINT_INDEX.leftEye).toBe(2);
  expect(JOINT_INDEX.rightEye).toBe(5);
  expect(OVERLAY_JOINTS).not.toContain("leftEye");
  expect(OVERLAY_JOINTS).not.toContain("rightEye");
});
```

- [ ] **Step 2:** `npx vitest run test/overlay.test.ts` → FAIL (`leftEye` undefined).
- [ ] **Step 3:** Add `leftEye: 2, rightEye: 5` to `JOINT_INDEX` (keep index order); filter eyes out of `OVERLAY_JOINTS` alongside ears.
- [ ] **Step 4:** `npm test` → all existing tests still PASS (golden scores 50/55/46 unchanged; eyes sit inside the head so `bbox` does not change scoring).
- [ ] **Step 5: Commit** `feat(biomech-lab): index eye landmarks` with `-- lib/landmarks.ts lib/overlay.ts test/overlay.test.ts`.

---

### Task 2: Config and per-photo frame

**Files:**
- Create: `lib/posture/config.ts`, `lib/posture/frame.ts`
- Test: `test/posture-frame.test.ts`

**Interfaces:**
- Consumes: `Body`, `toBody` (`lib/body.ts`), `nearSide` (`lib/poses/helpers.ts`).
- Produces:

```ts
// config.ts
export type FindingId = "forwardHead" | "headTilt" | "shoulderLevel" | "trunkShift"
  | "hipLevel" | "hipsForward" | "kneeHyperextension" | "heelAlignment";
export type Region = "headNeck" | "shoulders" | "trunkHips" | "kneesFeet";
export const FINDINGS: Record<FindingId, {
  label: string; region: Region; unit: "cm" | "deg"; weight: number;
  aligned: number; slight: number;   // |value| <= aligned → aligned; <= slight → slight; else needs work
  oneSided: boolean;                 // true: value <= 0 is aligned
}>;
export const REGION_ORDER: Region[]; // ["headNeck","shoulders","trunkHips","kneesFeet"]
export const REGION_LABEL: Record<Region, string>; // "Head & neck", "Shoulders", "Trunk & hips", "Knees & feet"
export const MAX_SIDE_PX = 1280;
export const TRAGION_RATIO = 0.936;
export const HEIGHT_MIN_CM = 120; export const HEIGHT_MAX_CM = 220;
export const FACE_FRONT_MIN = 0.8; // provisional, tuned in Task 9
export const FACE_BACK_MAX = 0.5;  // provisional, tuned in Task 9

// frame.ts
export type PostureView = "front" | "side" | "back";
export type PostureFrame = { view: PostureView; body: Body; cmPerPx: number | null };
export function makeFrame(view: PostureView, body: Body, heightCm: number): PostureFrame;
export function earToFloorPx(body: Body): number | null;
export function anatomicalRight(view: "front" | "back", a: Point, b: Point): { right: Point; left: Point };
export function facing(body: Body): 1 | -1 | null;   // +1 = facing +x (image right)
export function faceVisibility(body: Body): number;  // mean visibility of nose, leftEye, rightEye
```

Values from the spec for `FINDINGS` (label, region, unit, weight, aligned, slight, oneSided):
forwardHead "Forward head" headNeck cm 20 2.5 5 true · headTilt "Head tilt" headNeck deg 10 2 5 false · shoulderLevel "Shoulder level" shoulders deg 15 2 4 false · trunkShift "Trunk shift" trunkHips cm 15 1.5 3 false · hipLevel "Hip level" trunkHips deg 15 2 4 false · hipsForward "Hips forward" trunkHips cm 10 3 6 true · kneeHyperextension "Knee hyperextension" kneesFeet deg 10 5 10 true · heelAlignment "Heel alignment" kneesFeet deg 5 5 10 false.

- [ ] **Step 1: Write failing tests** (use `rawFromPixels` from `test/helpers/synthetic.ts`):
  - `weights sum to 100`: `Object.values(FINDINGS).reduce(..weight) === 100`.
  - `earToFloorPx uses mean ear y to mean heel y`: ears at y=100, heels at y=1036 → `936`; `makeFrame("front", body, 180).cmPerPx` → `180 * 0.936 / 936` (= 0.18).
  - `earToFloorPx falls back to ankles when heels are unusable`, and returns `null` when neither heels nor ankles are usable; `cmPerPx` is then `null`.
  - `anatomicalRight on front picks the smaller x as right; on back the larger x`.
  - `facing`: nose x 600, near ear x 560 → `1`; mirrored → `-1`; nose unusable → `null`.
  - `faceVisibility` averages the three visibilities (0.9, 0.6, 0.3 → 0.6).
- [ ] **Step 2:** `npx vitest run test/posture-frame.test.ts` → FAIL (module missing).
- [ ] **Step 3:** Implement. Sides by image position only, never by MediaPipe left/right labels. `facing` uses `nearSide()` for the ear.
- [ ] **Step 4:** Tests PASS.
- [ ] **Step 5: Commit** `feat(biomech-lab): posture config and frame`.

---

### Task 3: Measurements

**Files:**
- Create: `lib/posture/measure.ts`
- Test: `test/posture-measure.test.ts`

**Interfaces:**
- Consumes: `PostureFrame`, `anatomicalRight`, `facing`, `nearSide`, `angle` (`lib/geometry.ts`).
- Produces:

```ts
export type CoronalMeasures = {
  headTilt: number | null;       // deg, + = client's right ear lower
  shoulderLevel: number | null;  // deg, + = client's right shoulder lower
  shoulderDropCm: number | null; // cm, same sign
  hipLevel: number | null;       // deg, + = client's right hip lower
  hipDropCm: number | null;
  trunkShift: number | null;     // cm, + = shoulders shifted to client's right of hips
  heelAlignment: { deg: number; side: "right" | "left" } | null; // back only: worse heel→ankle tilt from vertical, unsigned
};
export type SagittalMeasures = {
  forwardHead: number | null;        // cm, + = ear ahead of shoulder
  earShoulderAngle: number | null;   // deg from horizontal, info only ("approximates CVA")
  hipsForward: number | null;        // cm, + = hip ahead of ankle
  kneeHyperextension: number | null; // deg = 180 - angle(hip,knee,ankle), + when knee is behind the hip-ankle line
};
export function measureCoronal(frame: PostureFrame): CoronalMeasures;  // frame.view "front" | "back"
export function measureSagittal(frame: PostureFrame): SagittalMeasures; // frame.view "side"
```

Any value whose landmarks aren't `body.usable()`, or that needs cm while `cmPerPx` is `null`, is `null`. `heelAlignment` is `null` on the front view.

- [ ] **Step 1: Write failing tests:**
  - Front, client's right shoulder (image-left) 10 px lower over a 200 px span → `shoulderLevel ≈ +2.86`; the same pixels on a **back** frame → `≈ -2.86` (sides flip).
  - `trunkShift`: shoulder midpoint 20 px image-right of hip midpoint, cmPerPx 0.2 → front `-4`, back `+4`.
  - `heelAlignment` on back: right heel→ankle 8° off vertical, left 3° → `{ deg ≈ 8, side: "right" }`.
  - Side, facing +x: ear 25 px ahead of shoulder, cmPerPx 0.2 → `forwardHead 5`; **mirrored image (facing -x) gives the same 5** (Review Focus 1).
  - `hipsForward` mirrored-invariant the same way.
  - `kneeHyperextension`: knee 6° behind the hip-ankle line → `≈ +6`; knee bent forward 6° → `≈ -6`; mirrored → same values.
  - Unusable near ear → `forwardHead === null`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement. Signed tilt: `atan2(yRight - yLeft, |xRight - xLeft|)` in degrees. Knee sign: compare the knee x to the hip-ankle line's x at the knee's y, multiplied by `facing`.
- [ ] **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat(biomech-lab): posture measurements`.

---

### Task 4: Findings, combine and score

**Files:**
- Create: `lib/posture/findings.ts`
- Test: `test/posture-findings.test.ts`

**Interfaces:**
- Consumes: `FINDINGS`, `FindingId`, `Region`, `CoronalMeasures`, `SagittalMeasures`, `makeFrame`, `measureCoronal`, `measureSagittal`.
- Produces:

```ts
export type PostureStatus = "aligned" | "slight" | "needs_work" | "not_measured";
export type Finding = {
  id: FindingId; region: Region; unit: "cm" | "deg";
  value: number | null;                       // signed (combined for front+back)
  perView: Partial<Record<"front" | "side" | "back", number | null>>;
  status: PostureStatus;
  disagree: boolean;                          // front/back opposite and one outside aligned band
  side: "right" | "left" | null;              // side the finding refers to (lower/shifted/worse), null if not lateral
  extra?: { dropCm?: number | null; earShoulderAngle?: number | null };
};
export type PostureResult = { score: number | null; findings: Finding[] };   // findings in REGION_ORDER, then FINDINGS key order
export type PhotoInput = { people: RawLandmark[][]; width: number; height: number };
export function statusFor(id: FindingId, value: number | null): PostureStatus;
export function combineFrontBack(id: FindingId, front: number | null, back: number | null):
  { value: number | null; status: PostureStatus; disagree: boolean };
export function assessPosture(input: { heightCm: number; front: PhotoInput; side: PhotoInput; back: PhotoInput }): PostureResult;
```

Rules (from the spec): one-sided findings with value ≤ 0 → aligned. Combine: signed mean; if only one is non-null, use it; `disagree` when signs are opposite **and** at least one `|v| > aligned`; then status = `slight`. Score: credit aligned 1, slight 0.5, needs_work 0; `round(100 * Σ w·c / Σ w over measured)`; `null` if nothing measured. `assessPosture` uses `people[0]` of each photo (validation already guaranteed one person).

- [ ] **Step 1: Write failing tests:**
  - `statusFor("forwardHead", 2.5)` aligned, `2.6` slight, `5.1` needs_work, `-3` aligned (one-sided).
  - `statusFor("shoulderLevel", -4.5)` needs_work (two-sided uses magnitude).
  - `combineFrontBack("shoulderLevel", 3, 1)` → value 2, slight, disagree false.
  - `combineFrontBack("shoulderLevel", 0.5, -0.5)` → aligned, disagree false (noise near zero).
  - `combineFrontBack("shoulderLevel", 5, -1)` → disagree true, status slight (capped from needs work).
  - `combineFrontBack("shoulderLevel", 3, -3)` → value 0 but status slight, disagree true (lifted).
  - Score: all aligned → 100; forwardHead needs_work only → 80; forwardHead not_measured and rest aligned → 100.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat(biomech-lab): posture findings and score`.

---

### Task 5: Step validation and flow reducer

**Files:**
- Create: `lib/posture/validate.ts`, `lib/posture/flow.ts`
- Test: `test/posture-validate.test.ts`, `test/posture-flow.test.ts`

**Interfaces:**
- Consumes: `toBody`, `inferView`, `framingOk` (`lib/view.ts`), `earToFloorPx`, `faceVisibility`, `FACE_FRONT_MIN`, `FACE_BACK_MAX`, `HEIGHT_MIN_CM`, `HEIGHT_MAX_CM`, `PhotoInput`, `PostureView`.
- Produces:

```ts
// validate.ts
export type StepRejection = "no_person" | "multiple_people" | "framing" | "wrong_view_side"
  | "wrong_view_front" | "looks_like_back" | "looks_like_front" | "duplicate";
export const REJECTION_MESSAGE: Record<StepRejection, string>;
export function validateStep(view: PostureView, photo: PhotoInput,
  opts?: { fingerprint?: string; otherFingerprints?: string[] }): { ok: true } | { ok: false; reason: StepRejection };
export function validHeight(input: string): number | null;   // integer 120..220 else null

// flow.ts
export type PhotoState = { input: PhotoInput; url: string; fingerprint: string };
export type FlowState = {
  step: "height" | PostureView | "results";
  heightCm: number | null;
  photos: Partial<Record<PostureView, PhotoState>>;
};
export type FlowAction =
  | { type: "setHeight"; heightCm: number }
  | { type: "acceptPhoto"; view: PostureView; photo: PhotoState }
  | { type: "goTo"; step: FlowState["step"] }
  | { type: "reset" };
export const initialFlow: FlowState;
export function flowReducer(s: FlowState, a: FlowAction): FlowState;
export function canShowResults(s: FlowState): boolean;   // height + all 3 photos
```

Messages (exact): no_person and multiple_people reuse the existing app wording ("We couldn't find a person. Step back so your whole body is in frame." / "Make sure you're alone in the frame."); framing "Step back so your whole body, including your feet, is in frame."; wrong_view_side "Turn a bit more to the side of the camera."; wrong_view_front "Turn a bit more to face the camera."; looks_like_back "This looks like a back photo. Face the camera."; looks_like_front "We can see your face. Turn your back to the camera."; duplicate "You already used this photo for another view. Upload a different one.".

Order of checks: people count → framing (`framingOk` **and** `earToFloorPx !== null`) → view (`inferView` must be `side` on side, `front` on front/back) → face visibility (front ≥ FACE_FRONT_MIN, back ≤ FACE_BACK_MAX; values in between are rejected as the step's mismatch message) → duplicate fingerprint.

Flow rules: `acceptPhoto` stores the photo and advances front → side → back → results (if `canShowResults`, else the first missing step). `setHeight` advances to the first missing step. `goTo` to any earlier step is allowed; `results` only when `canShowResults`. Changing height or replacing a photo while on/after results keeps the other photos; the results are always derived from state (never stored), so they can't go stale (Review Focus 3).

- [ ] **Step 1: Write failing tests** (synthetic bodies):
  - Valid front body with face visibility 0.95 on front → ok; same body on back → `looks_like_front`.
  - Face visibility 0.2 on front → `looks_like_back`.
  - Side-shaped body (narrow shoulders) on front → `wrong_view_front`; front-shaped on side → `wrong_view_side`.
  - Heels and ankles invisible → `framing` (Review Focus 2).
  - Same fingerprint as another step → `duplicate` (Review Focus 4).
  - `validHeight("175")` 175; `"119"`, `"221"`, `"175.5"`, `""`, `"abc"` → null.
  - Flow: height → front → side → back lands on `results`; replacing `front` from results returns to `results` with side/back kept; `goTo("results")` without all photos is ignored; `reset` returns `initialFlow`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat(biomech-lab): posture step validation and flow`.

---

### Task 6: Copy and exercise library

**Files:**
- Create: `lib/posture/copy.ts`, `lib/posture/exercises.ts`
- Test: `test/posture-copy.test.ts`

**Interfaces:**
- Consumes: `Finding`, `FindingId`.
- Produces:

```ts
// copy.ts
export function formatCm(v: number): string;    // nearest 0.5, e.g. 4.3 → "4.5 cm"
export function formatDeg(v: number): string;   // whole degrees, e.g. 3.4 → "3°"
export function measuredSentence(f: Finding): string;  // "" for not_measured
// exercises.ts
export type Exercise = { name: string; steps: string[]; dosage: string };
export const LIBRARY: Record<FindingId, { explanation: (f: Finding) => string; exercises: (f: Finding) => [Exercise, Exercise, Exercise] }>;
```

Sentences use the client's side and the spec's style, e.g. forwardHead 4.3 → "Your ear sits about 4.5 cm ahead of your shoulder line."; shoulderLevel +3 with dropCm 1.2 → "Your right shoulder sits about 1 cm lower than your left (3°)."; aligned findings get a short "lined up" sentence. Exercise sets per the spec's "Exercise library" list. Explanations 2-3 sentences, conservative, no diagnoses; every exercise list ends its steps with a stop-if-it-hurts cue or includes it in the dosage.

- [ ] **Step 1: Write failing tests:**
  - `formatCm(4.3) === "4.5 cm"`, `formatCm(2.6) === "2.5 cm"`, `formatDeg(3.4) === "3°"`.
  - For every `FindingId`: exactly 3 exercises, each with ≥ 2 steps and a dosage.
  - No string in any explanation, exercise or sentence (rendered with sample findings for both sides) contains `—`, "diagnos", "scoliosis", "kyphosis" or "you have".
  - Side templating: shoulderLevel with side "left" mentions "left shoulder" and the exercises target the matching side.
- [ ] **Step 2:** FAIL. **Step 3:** Implement and write the copy. **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat(biomech-lab): posture copy and exercise library`.

---

### Task 7: Image utilities and overlay geometry

**Files:**
- Create: `lib/posture/image.ts`, `lib/posture/overlay.ts`
- Test: `test/posture-image.test.ts`, `test/posture-overlay.test.ts`

**Interfaces:**
- Consumes: `PostureFrame`, `Finding`, `overlayGeometry` (`lib/overlay.ts`), `MAX_SIDE_PX`.
- Produces:

```ts
// image.ts
export function targetSize(w: number, h: number, max?: number): { width: number; height: number };
export function downscaleImage(file: File, max?: number): Promise<{ image: HTMLImageElement; url: string; width: number; height: number }>; // browser only; rejects with Error("decode") if the file can't be decoded
export function fileFingerprint(file: File): Promise<string>; // SHA-256 hex via crypto.subtle
// overlay.ts
export type PostureLine = { x1: number; y1: number; x2: number; y2: number; status: PostureStatus; dashed?: boolean };
export type PostureDot = { x: number; y: number; status: PostureStatus };
export function coronalOverlay(frame: PostureFrame, findings: Finding[]): { lines: PostureLine[]; dots: PostureDot[] };
export function sagittalOverlay(frame: PostureFrame, findings: Finding[]): { lines: PostureLine[]; dots: PostureDot[] };
```

`downscaleImage` draws to a canvas at `targetSize`, exports JPEG (quality 0.9) to a blob URL, and loads it into an `HTMLImageElement`. Coronal: lines across ears (headTilt), shoulders (shoulderLevel), hips (hipLevel) colored by their finding status, plus a dashed vertical midline through the hip midpoint (status aligned). Sagittal: dashed vertical plumb line through the near ankle; dots on ear, shoulder, hip, knee colored by forwardHead, forwardHead, hipsForward, kneeHyperextension.

- [ ] **Step 1: Write failing tests:**
  - `targetSize(4912, 7360)` → `{ width: 854, height: 1280 }`; `targetSize(826, 1752)` → `{ width: 603, height: 1280 }`; `targetSize(425, 740)` unchanged (never upscale) (Review Focus 5).
  - `coronalOverlay`: shoulder line status equals the shoulderLevel finding's status; a midline exists and is dashed.
  - `sagittalOverlay`: the plumb line's x equals the near ankle's x for its full height.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat(biomech-lab): posture image utils and overlay geometry`.

---

### Task 8: Posture page UI

**Files:**
- Create: `app/posture/page.tsx`, `components/posture/PostureCheck.tsx` (client; owns `useReducer(flowReducer)` and the engine ref), `components/posture/HeightStep.tsx`, `components/posture/PhotoStep.tsx`, `components/posture/Silhouette.tsx`, `components/posture/PostureResults.tsx`, `components/posture/PostureOverlay.tsx`, `components/posture/FindingRow.tsx`
- Modify: `lib/site.ts` (`NAV_LINKS`: add `{ href: "/posture", label: "posture" }` after `analyze`), `app/page.tsx` (entry point to `/posture`, placement builder's call)

**Interfaces:**
- Consumes: everything from Tasks 2-7; `createImageEngine` (`lib/pose-engine.ts`, lazily imported like `PhotoLab.getEngine`, closed on unmount); `SiteNav`, `SiteFooter`, `StatusBadge` look; `ui/styles.ts` tokens.

Requirements:
- Height step (number input, `validHeight`, note: "Used only to turn measurements into centimeters. Stays on your device."), then the three photo steps, as in the spec's Flow section and the approved mockup (progress bar with 3 segments, mono `step N of 3 · <view> view` label, heading, silhouette, tips, upload button). Tips text from the spec.
- On upload: `downscaleImage` → on `Error("decode")` show "We couldn't open that photo. Try a JPG or PNG." → `fileFingerprint` → `engine.detectImage(image)` → `validateStep` → show rejection message on the step, or a thumbnail with the skeleton plus "Use this photo" / "Retake". "Use this photo" dispatches `acceptPhoto`.
- Back navigation to any earlier step; "Start over" dispatches `reset` and revokes all blob URLs (also revoke a photo's URL when it is replaced).
- Results: compute `assessPosture` with `useMemo` from flow state. Score header (score, "posture score · 3 of 3 views", height used), the three photos with `PostureOverlay` (render the downscaled blob URL with a plain `<img>`, not `next/image`), findings grouped by `REGION_ORDER` using `REGION_LABEL`; `FindingRow` shows label, status pill ("aligned" / "slight" / "needs work" / "not measured"), measured value; slight and needs-work rows expanded by default with `measuredSentence`, the explanation and 3 exercise cards; the disagree note "Front and back photos disagree; retake for a reliable reading." when `disagree`; forwardHead detail shows "ear-shoulder angle (approximates CVA): N°". Disclaimer (exact text from Global Constraints) always visible. "Start over" button.
- `app/posture/page.tsx`: `SiteNav`, a section shell with label `posture check` and title, `PostureCheck`, `SiteFooter`; page metadata title "Posture check".

- [ ] **Step 1:** `npm run typecheck` and `npm run lint` → PASS (one at a time).
- [ ] **Step 2:** `npm run build` → PASS, `/posture` listed as a static route.
- [ ] **Step 3:** Manual check with the guarded dev server (`rm -rf .next` first): walk the flow with the three photos in `public/user-1-assets/posture/`; confirm a front photo on the back step is rejected, the same file twice is rejected, results render with overlays, and replacing the front photo from results updates the score. Stop the dev server.
- [ ] **Step 4: Commit** `feat(biomech-lab): posture check page`.

---

### Task 9: Golden landmarks and threshold tuning

**Files:**
- Modify: `components/dev/Extractor.tsx` (also extract the three local posture photos `/user-1-assets/posture/posture-01-{front,side,back}.jpg`, through `downscaleImage`-equivalent sizing: load, `targetSize`, draw to canvas, detect on the canvas-backed image so landmarks match production)
- Create: `data/samples/posture/front.json`, `side.json`, `back.json` (same shape as `LandmarkFile`; **not** added to `LANDMARK_FILES`, so `/reports` is unaffected)
- Modify (if needed): `lib/posture/config.ts` (`FACE_FRONT_MIN`, `FACE_BACK_MAX`)
- Test: `test/posture-golden.test.ts`

- [ ] **Step 1:** Guarded dev server, open `/dev/extract` in Chrome, copy the three posture JSON blocks into the files above. Stop the dev server.
- [ ] **Step 2: Write the golden test:** each fixture passes `validateStep` for its own view; front on the back step → `looks_like_front`; back on the front step → `looks_like_back`; side on front → `wrong_view_front`; `assessPosture({ heightCm: 180, ... })` score is non-null and within the recorded score ± 5 (record on first run, document in a comment like `test/golden.test.ts`); log `faceVisibility` of front and back.
- [ ] **Step 3:** If the face rules fail on these photos, set `FACE_FRONT_MIN` / `FACE_BACK_MAX` to sit midway between the observed values (keep a margin of at least 0.1 on each side) and note the observed values in a comment.
- [ ] **Step 4:** `npm test` → PASS.
- [ ] **Step 5: Commit** `test(biomech-lab): posture golden landmarks`.

---

### Task 10: Final verification

- [ ] **Step 1:** One at a time from `biomech-lab/`: `npm run typecheck`, `npm run lint`, `npm test`, `npm run build`. All PASS; `test/csp.test.ts` included.
- [ ] **Step 2:** `git status` shows no stray changes in `biomech-lab/`; nothing outside `biomech-lab/` was committed on this branch (`git diff --stat main...HEAD`).
- [ ] **Step 3:** Hand off to the `biomech-lab:pr-creation` skill to open the draft PR.
