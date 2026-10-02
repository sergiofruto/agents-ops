# Biomech Lab — Design Spec

**Date:** 2026-09-29
**Version:** v2 (incorporates `design-spec-review.md`; decisions in the last section)
**Status:** Draft — awaiting review
**Location:** `biomech-lab/` in the `agents-ops` repo
**Time budget:** 1 weekend (v1), then published as a LinkedIn Project

## Goal

A public, clickable demo that recognizes one of three yoga poses from a webcam or photo,
scores the quality of the posture from measured joint angles, and streams an AI coaching
note with a short workout. It is the headline item for the LinkedIn Projects / Featured
section and demonstrates: real-time frontend, applied computer vision, deterministic
scoring, and a streamed LLM feature running safely in production.

**Success criteria**

- A visitor with no camera gets a scored result in one click (sample photos).
- A visitor with a camera sees a live skeleton and a score within ~5 s of holding a pose.
- The same photo always yields the same score (scoring is deterministic; only the coach text varies).
- No score is ever shown when the pose cannot be measured reliably (wrong view, poor framing, low coverage).
- Images and video never leave the browser.
- Public URL on Vercel; cost of the AI coach is capped per day.

## Non-goals (v1)

Video file upload, more than 3 poses, user accounts or history, rep counting, mobile app,
multi-person scenes (rejected, not handled), medical/injury claims, manual view selection.

## Architecture

```
Browser (Next.js page, client-side)
 ├─ Input: Camera (live) | Photo upload | Sample photo
 ├─ Pose engine    MediaPipe PoseLandmarker (@mediapipe/tasks-vision), numPoses = 2
 │                   └─ per person: 33 landmarks (x, y normalized; visibility)
 ├─ Overlay        canvas skeleton; check status shown by color AND icon/label
 │
 ├─ Photo / sample path:  detect → people check → classify → readiness → score (single frame)
 ├─ Live path:            detect every frame → people check → classify → [stable 1 s] →
 │                        3 s countdown → collect frames → readiness → window aggregate → score
 │
 └─ Results panel ──POST { pose, mode, measurements: [{ checkId, value }] }──▶ /api/coach
                                   ├─ zod validation (enums + numeric bounds)
                                   ├─ server recomputes checks/score from shared definitions
                                   ├─ reserve quota (per IP + global) BEFORE calling the model
                                   └─ Claude Haiku 4.5, streamed; exercises from allowlisted catalog
```

**Stack:** Next.js 16 (App Router), React 19, TypeScript strict, Tailwind v4, shadcn/ui —
same as `solaris/web-next`. `@mediapipe/tasks-vision` for pose. `@anthropic-ai/sdk` for the
coach. `@upstash/ratelimit` + Upstash Redis (Vercel Marketplace, free tier) for limits.
Vitest for unit tests, Playwright for one browser flow test. Deployed on Vercel with root
directory `biomech-lab/`.

## Units

Pure modules have their own unit tests. Pose definitions and the exercise catalog are shared
by the browser and the API route, so the server owns the same targets the client displays.

| Unit              | File                                   | Input → Output                                                                  |
| ----------------- | -------------------------------------- | ------------------------------------------------------------------------------- |
| Geometry          | `lib/geometry.ts`                      | pixel-space points → angles, tilts, normalized distances (contract below)       |
| Body model        | `lib/body.ts`                          | raw landmarks + image size → `Body` (pixel points, visibility, derived lengths) |
| View & framing    | `lib/view.ts`                          | `Body` → `{ view: front \| side \| ambiguous, framingOk, reasons[] }`           |
| Classifier        | `lib/classify.ts`                      | `Body` → `{ pose, confidence }`                                                 |
| Pose definitions  | `lib/poses/{warrior2,tree,downdog}.ts` | required view, checks: id, measure fn, required landmarks, target, tol, weight, cue |
| Readiness         | `lib/readiness.ts`                     | people count + `Body` + pose def + mode → `AssessmentReadiness`                 |
| Scorer            | `lib/score.ts`                         | pose def + measurements → `{ score, checks[] }` (pure; also used by the server) |
| Window aggregator | `lib/window.ts`                        | frames over 3 s → median measurements + sway                                    |
| Exercise catalog  | `lib/exercises.ts`                     | checkId → 2 allowlisted exercises (name, dose)                                  |
| Pose engine       | `lib/pose-engine.ts`                   | wraps MediaPipe; interface allows a fake engine in tests                        |
| Coach API         | `app/api/coach/route.ts`               | validated measurements → streamed coaching text                                 |
| UI                | `app/page.tsx`, `components/*`         | input tabs, capture guide, overlay, countdown, results, coach stream            |

## Geometry contract

- **Coordinate space:** MediaPipe returns x, y normalized to [0, 1] with y pointing down.
  `lib/body.ts` converts every landmark to **pixel space** (`x·width`, `y·height`) before any
  measurement, so angles are not distorted by the image aspect ratio. All geometry below is
  2D in pixel space; depth (z) is not used.
- **Visibility:** a landmark is *usable* when `visibility ≥ 0.5` and it lies inside the image
  with a 2% margin.
- Feet use MediaPipe heel (29/30) and foot-index (31/32) landmarks in addition to the ankles.
- `angle(a, b, c)`: unsigned angle at `b`, degrees, range [0, 180].
- `tiltFromVertical(p, q)` / `tiltFromHorizontal(p, q)`: unsigned angle between segment p→q
  and the image axis, degrees, range [0, 90].
- `torsoLength`: distance from shoulder midpoint to hip midpoint (px). All distances are
  divided by it (unitless).
- `distanceToLine(p, a, b)`: perpendicular distance from p to line a–b, divided by `torsoLength`.
- **Mirroring:** the pose engine always processes the unmirrored frame. The selfie mirror is
  applied only with CSS on the displayed video and on the overlay canvas.
- **Left/right canonicalization:** MediaPipe's left/right labels are never used for meaning.
  Roles are assigned by geometry:
  - Warrior II **front leg** = the leg with the smaller knee angle.
  - Tree **standing leg** = the leg whose ankle is lower (larger y).
  - Downward Dog **near side** = the side whose required landmarks have the higher mean visibility;
    all side-view checks use the near side.

## View and framing

- `shoulderRatio = shoulderWidth / torsoLength`.
  - `≥ 0.45` → **front**; `≤ 0.25` → **side**; in between → **ambiguous** (never scored).
- **Framing OK** when the four core landmarks (both shoulders, both hips) are usable and
  `max(bboxWidth / frameWidth, bboxHeight / frameHeight) ≥ 0.40`. Other missing landmarks are
  handled by coverage, not framing.
- Starting thresholds are tuned against the fixtures during the build and live only in `lib/view.ts`.

## Classification

Rules run on the `Body` in this order. A rule matches only when **all** its conditions hold;
the first matching rule wins. Confidence = mean visibility of the landmarks the rule uses.
No match, or confidence below 0.6 → **unknown**.

1. **Downward Dog:** hip midpoint is above both the shoulder midpoint and the ankle midpoint
   (smaller y), and both wrists and both ankles are in the bottom 35% of the body bounding box.
2. **Tree:** vertical ankle gap > 0.25 × standing-leg length (hip→ankle), and standing knee angle > 160°.
3. **Warrior II:** horizontal ankle distance > 1.2 × shoulder width, and both wrists within
   0.15 × torsoLength vertically of the shoulder midpoint.
4. Otherwise **unknown** → UI shows the three supported poses with their capture guides.

## Measurement readiness

A numeric score is shown only when readiness passes.

```ts
type ReadinessReason =
  | "no_person" | "multiple_people" | "wrong_view" | "bad_framing" | "low_coverage";

type AssessmentReadiness = {
  canScore: boolean;
  view: "front" | "side" | "ambiguous";
  coverage: number;          // 0..1
  reasons: ReadinessReason[];
  missing: Joint[];          // required landmarks that were not usable (for reframe prompts)
};
```

- `multiple_people`: the engine detected 2 people → reject; ask the visitor to be alone in frame.
- `wrong_view`: inferred view ≠ the pose's required view (Warrior II and Tree: front; Downward Dog: side).
- `bad_framing`: framing check failed.
- `coverage` = sum of weights of checks whose required landmarks are all usable ÷ total weight
  of checks applicable in this mode (the stability check is not applicable in photo mode).
- `low_coverage`: coverage < 0.70.
- `canScore` = no reasons. The results panel shows **measurement confidence** (coverage) separately
  from the posture score.

## Scoring

Each check returns a value in its documented unit. Partial credit uses deviation
`d = |value − target|`: full credit when `d ≤ tol`, falling linearly to 0 at `d = 2·tol`.
Binary checks score 0 or 100. The pose score is the weighted average over measured checks,
rounded to an integer. Checks that cannot be measured are listed as **not measured**; readiness
guarantees they total less than 30% of the weight.

**Warrior II** — required view: front

| Check id          | Measurement                                                   | Target | Tol   | Weight |
| ----------------- | ------------------------------------------------------------- | ------ | ----- | ------ |
| `frontKneeBend`   | `angle(hip, knee, ankle)` front leg, °                        | 90     | 10    | 30     |
| `kneeOverAnkle`   | `|knee.x − ankle.x| / torsoLength`, front leg                 | 0      | 0.10  | 20     |
| `backLegStraight` | `angle(hip, knee, ankle)` back leg, °                         | 180    | 10    | 15     |
| `armsLevel`       | `tiltFromHorizontal(leftWrist, rightWrist)`, °                | 0      | 10    | 20     |
| `torsoUpright`    | `tiltFromVertical(hipMid, shoulderMid)`, °                    | 0      | 10    | 15     |

**Tree** — required view: front

| Check id          | Measurement                                                                 | Target  | Tol   | Weight |
| ----------------- | --------------------------------------------------------------------------- | ------- | ----- | ------ |
| `standingLeg`     | `angle(hip, knee, ankle)` standing leg, °                                   | 180     | 8     | 25     |
| `footOffKnee`     | binary: vertical clearance between the standing knee and the raised foot's heel–toe span (heel, ankle, foot index) / shinLength ≥ 0.15 — 0 when the foot overlaps the knee | pass    | —     | 20     |
| `hipsLevel`       | `tiltFromHorizontal(leftHip, rightHip)`, °                                  | 0       | 6     | 20     |
| `torsoUpright`    | `tiltFromVertical(hipMid, shoulderMid)`, °                                  | 0       | 8     | 15     |
| `stability`       | live only: std. deviation of hipMid over the window / torsoLength           | 0       | 0.02  | 20     |

**Downward Dog** — required view: side (near side landmarks)

| Check id          | Measurement                                                       | Target | Tol   | Weight |
| ----------------- | ----------------------------------------------------------------- | ------ | ----- | ------ |
| `armsStraight`    | `angle(shoulder, elbow, wrist)`, °                                | 180    | 10    | 20     |
| `legsStraight`    | `angle(hip, knee, ankle)`, °                                      | 180    | 15    | 20     |
| `hipAngle`        | `angle(shoulder, hip, ankle)`, °                                  | 80     | 15    | 25     |
| `flatBack`        | `angle(wrist, shoulder, hip)`, °                                  | 180    | 12    | 25     |
| `headAligned`     | `distanceToLine(ear, shoulder, wrist)`                            | 0      | 0.10  | 10     |

Every check declares its required landmarks next to its measure function. Targets and
tolerances are starting values tuned during the build; they live only in the pose definition files.

## Live mode flow

1. Request camera → run the pose engine on each animation frame (target ≥ 20 fps).
2. Draw the skeleton continuously; classify each frame; show framing hints from `lib/view.ts`.
3. Same pose classified with confidence ≥ 0.6 for 1 s → 3 s countdown.
4. Collect frames during the countdown → readiness on the median frame → if it passes,
   window aggregator (median measurements + sway) → score.
5. Freeze the frame, show results, allow "Get coaching". "Try again" restarts at step 2.

If readiness fails, show the reasons as plain-language prompts ("Turn sideways for Downward Dog",
"Step back so your whole body is in frame") instead of a score.

## AI coach

- **Request:** `{ pose, mode, measurements: [{ checkId, value }] }`. zod accepts only known
  pose ids, check ids that belong to that pose, and values within each check's physical bounds
  (angles 0–180, ratios 0–5). No image data and no free text.
- **Server-owned meaning:** the route imports the shared pose definitions, recomputes check
  status and score from the values, picks the two weakest checks, and takes their exercises
  from `lib/exercises.ts`. The prompt is assembled only from these server-owned strings and numbers.
- **Model:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`), streamed, `max_tokens` ≈ 400.
- **Output:** 2–3 sentences explaining the weakest checks in plain language, then the
  pre-selected exercises, each with one line on why it helps. The system prompt forbids
  diagnoses, injury or medical advice; the UI shows "Educational feedback, not medical advice."
- **Quota:** before any model call, reserve 1 unit from each limit via Upstash (each `limit()`
  call is atomic): 5/min per IP, 20/day per IP, 500/day global. Daily windows reset at 00:00 UTC.
  Any limit hit → 429; score stays visible and the coach panel says "Coach is resting — try again later."
- **Fail closed:** if Redis is unreachable or its env vars are missing, the route returns 503
  without calling the model; the UI shows "Coach unavailable right now."
- **Secrets:** `ANTHROPIC_API_KEY`, `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` in Vercel env only.

## Privacy

On-page wording: **"Images and video stay on your device. Only anonymous measurement results
are sent when you ask for coaching."** Links to a short privacy note (same page section)
stating that the coach request contains joint measurements and passes through Vercel, where
the IP address is used for rate limiting; nothing is stored beyond rate-limit counters.

MediaPipe tasks-vision includes a built-in usage logger (posts task type and timings to odml.pa.googleapis.com) with no opt-out. The app blocks it with a Content-Security-Policy connect-src header that allows only the app origin and the WASM/model hosts (lib/csp.ts).

## Screens

Single page, dark theme consistent with Solaris.

1. **Header:** "Biomech Lab", one-line pitch, privacy line.
2. **Input tabs:** Camera · Upload photo · Try a sample (3 thumbnails).
3. **Capture guide:** per pose — required view (front/side), a silhouette, "full body in frame".
4. **Stage:** video/photo with skeleton overlay; detected pose + confidence chip; countdown ring;
   readiness prompts.
5. **Results:** posture score, measurement confidence, per-check rows (measured vs target,
   status as text + icon + color, cue text).
6. **Coach:** "Get coaching" button → streamed text, then the exercise card.
7. **Footer:** "How it works" (3 bullets), privacy note, links to GitHub and LinkedIn.

**Accessibility:** tabs, capture, retry and coach controls are keyboard-operable with visible
focus; status never relies on color alone; the streamed coach text is in an `aria-live="polite"` region.

## Error handling

| Situation                             | Behavior                                                                   |
| ------------------------------------- | -------------------------------------------------------------------------- |
| Camera denied or unavailable          | Switch to "Upload photo" with a short explanation                          |
| Model fails to load (network / WebGL) | Error card with retry; samples tab still explains the app                  |
| No person detected                    | "Step back so your whole body is in frame"                                 |
| More than one person                  | No score; "Make sure you're alone in the frame"                            |
| Wrong view / ambiguous view           | No score; pose-specific prompt ("Turn sideways for Downward Dog")          |
| Bad framing / low coverage            | No score; reframe prompt naming the missing body parts                     |
| Unknown pose                          | Show the 3 supported poses with capture guides                             |
| Coach 429                             | Score visible; "Coach is resting — try again later"                        |
| Coach 503 / 5xx / timeout             | Score visible; "Coach unavailable right now" + retry                       |
| Stream interrupted                    | Keep partial text; "Coach disconnected — retry"                            |

## Testing

- **Unit (Vitest):** geometry functions (synthetic points with known answers), body pixel
  conversion (non-square images), view inference, classifier, readiness, scorer (partial-credit
  math, binary checks, coverage), window aggregator, exercise selection.
- **Golden cases** (landmark JSON under `test/fixtures/`): each sample photo with a documented
  expected score range, plus derived variants generated in tests —
  mirrored (x → 1−x with left/right labels swapped) must give the **same** score;
  left/right role variants; occluded (visibility zeroed on key joints → `low_coverage`);
  wrong view; cropped (`bad_framing`); two people (`multiple_people`).
- **API route:** schema rejections (unknown ids, out-of-range values, extra fields),
  server-side recomputation ignores any client score, quota path (429), Redis missing (503),
  Anthropic client mocked to stream chunks.
- **Request builder:** unit test asserts the coach request body contains only the allowed fields
  (no image bytes, no data URLs).
- **Browser flow (Playwright, 1 test):** fake pose engine; covers camera denied → photo tab,
  countdown, readiness gating (no score on wrong view), score display, coach fallback on 429.
- **Manual before publishing:** Chrome + Safari desktop, iPhone Safari, Android Chrome; each
  sample; keyboard-only run; network panel confirms no image/video uploads.

## Sample photos

Three photos of Sergio: Warrior II (front), Tree (front), Downward Dog (side), full body in
frame. Resized and committed under `public/samples/`; their landmark JSON becomes the golden fixtures.

## Launch gates

- No numeric score for an unsupported view or coverage below 70%.
- All three samples produce stable, documented expected score ranges.
- Camera denial, model load failure, multi-person input and coach limits are all handled.
- Network inspection confirms images and video never leave the browser.
- Input selection, retry and results are keyboard-operable with non-color status cues.

## Deliverables (weekend)

- **Day 1:** scaffold; geometry, body, view, readiness contracts + unit tests; classifier and
  scorer; photo + sample paths; golden fixtures from the sample photos.
- **Day 2:** live path (countdown, window, framing hints); coach route with shared definitions,
  catalog and quotas; UI polish + accessibility pass; deploy; `README.md` (demo GIF, how it works, stack).
- **If Day 2 runs over:** the Playwright test moves to the following week; all other launch gates stay.
- **Separate, ~1 h:** root `README.md` for agents-ops — what it is, architecture diagram, Solaris
  screenshot, link to Biomech Lab. No live trading data exposed.
- **Then:** LinkedIn Project entry + Featured link.

## Review decisions (v1 → v2)

| Review item | Decision |
| --- | --- |
| 1. View as explicit input | **Adopted with a change:** the view is **inferred** from shoulder width vs torso length and gated by readiness, plus a per-pose capture guide. No manual front/side control: it adds a step for every visitor, and a wrong manual choice would still need detection. Mirroring and left/right canonicalization specified. |
| 2. Readiness gate | **Adopted:** `AssessmentReadiness`, 70% weighted coverage, confidence shown separately. |
| 3. Geometry contract | **Adopted:** pixel-space contract, units and bounds per check, `headAligned` defined as a distance. **Added:** conversion to pixel space before measuring (normalized coordinates distort angles on non-square frames — not raised in the review). |
| 4. Multi-person | **Adopted:** detect up to 2 people and reject when 2 are found. |
| 5. Photo vs live paths | **Adopted:** separate pipelines in the architecture. |
| 6. Coach API boundary | **Adopted:** client sends check ids + measured values only; server owns targets, status, score and prompt text; quotas reserved before the model call; UTC day; fail closed. |
| 7. Privacy and safety | **Adopted:** corrected wording, privacy note, allowlisted exercise catalog, non-medical framing. |
| 8. Validation | **Adopted:** golden variants and request-body assertion. The Playwright test is the only item allowed to slip past the weekend. |
