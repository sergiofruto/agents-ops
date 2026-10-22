# Biomech Lab: Posture Check

**Date:** 2026-10-22 · **Status:** Approved by Sergio ("go ahead"); exercise and explanation copy ships without a separate review
**Visual companion choices:** capture flow B (guided steps), results layout A (grouped by body region). Mockups in `.superpowers/brainstorm/16815-1792690447/content/`.

## Intent

Clients want a first look at how their head, shoulders and trunk line up when standing. They take three photos (front, side, back), enter their height, and get a posture score plus plain-language findings. Each finding that is off comes with an explanation and 3 exercises. It is a screening a kinesiologist would recognize (plumb line from the side, level lines from front and back), not a diagnosis.

## Goals

- A guided capture flow: height, then front, side and back photos, each checked before moving on.
- A 0-100 posture score and per-finding status (aligned / slight / needs work).
- Findings in real units: centimeters (using the client's height) for offsets, degrees for tilts.
- For every slight or needs-work finding: what was measured, what it can mean, and 3 exercises with how-to and dosage.
- Results grouped by body region, top to bottom: head & neck, shoulders, trunk & hips, knees & feet.
- Everything runs in the browser, like the existing pose check. Photos and height never leave the device.

## Non-goals

- Measuring spine curves (thoracic kyphosis, lumbar lordosis), pelvic tilt or scoliosis. MediaPipe has no spine or pelvis landmarks. The results page says so.
- Front-view knee alignment (valgus/varus), scapular winging, foot arch. Possible later.
- Weight, BMI, age or any other client data (weight was considered and dropped).
- Saving results, accounts, PDF export, sharing.
- AI-generated text. Explanations and exercises are a fixed, reviewable library.
- Live/video posture check. Photos only.
- Adding posture samples to `/reports`.

## Anti-goals (would be a failure even if it works)

- Sounding like a diagnosis ("you have scoliosis", "you have kyphosis").
- Reporting precision the photo can't support (e.g. millimeters, decimals of a degree).
- Scoring a photo taken from the wrong view, or with the person cut off, instead of asking for a new one.
- Uploading photos or height anywhere.
- Freezing the machine: large photos must be downscaled before detection.

## Constraints

- Builds on the existing pipeline: MediaPipe PoseLandmarker (IMAGE mode, full model, GPU with CPU fallback) via `lib/pose-engine.ts`, `toBody()` in `lib/body.ts`, geometry helpers in `lib/geometry.ts`, `inferView()`/`framingOk()` in `lib/view.ts`, the dark "lab instrument" theme and viz components.
- MediaPipe landmarks used: nose, ears, shoulders, hips, knees, ankles, heels, foot index.
- The site is English; posture copy is English too.
- Next.js 16 as installed in the project; read `node_modules/next/dist/docs/` before writing routing or config code (see `AGENTS.md`).
- Run checks one at a time on Sergio's 16 GB machine (see the PR skill).

## Decided by Sergio

1. Three views, **all required** to complete the assessment.
2. **Guided steps** capture: front, then side, then back; one view per screen with photo tips and a silhouette guide; each photo validated before continuing.
3. Results **grouped by body region** (A), with score, the three photos with overlays, and findings.
4. Findings get an **explanation and 3 exercises**.
5. Ask for **height** (to report cm). **No weight.**
6. **Detect swapped front/back photos** using face-landmark visibility.
7. Exercise and explanation copy is written during the build and **ships without a separate review**.

## Flow

### Step 0: height
- Number input in cm, required, range 120-220, integer.
- Short note: "Used only to turn measurements into centimeters. Stays on your device."

### Steps 1-3: front, side, back
Each step screen: progress bar (3 segments), mono label `step N of 3 · <view> view`, a heading ("Face the camera", "Stand sideways to the camera", "Turn your back to the camera"), a silhouette for that view, the tips list, and an upload button.

Tips (all steps): whole body in frame with feet visible; arms relaxed by your sides; camera at hip height, 2-3 m away; fitted clothes; plain wall. Side step adds: "either side is fine". Back step adds: "hair off the neck if possible".

On upload:
1. Decode the image. If it can't be decoded (e.g. HEIC in a browser without support), show "We couldn't open that photo. Try a JPG or PNG."
2. Downscale to at most **1280 px on the long side** before detection (canvas). Detection and overlays use the downscaled image.
3. Detect. Reject with a specific message and stay on the step if:
   - no person, or more than one person (reuse existing messages);
   - `framingOk()` fails ("Step back so your whole body, including your feet, is in frame.");
   - wrong view: on the side step, `inferView()` must be `side`; on front/back steps it must be `front`. `ambiguous` is rejected with "Turn a bit more to face / to the side of the camera."
   - front vs back swapped (Sergio's decision): shoulder width can't tell front from back, so use face landmarks. Add the eye indices (MediaPipe 2 and 5) to `lib/landmarks.ts` and compute the mean visibility of nose and both eyes. High on the front step, low on the back step. Reject a back-looking photo on the front step ("This looks like a back photo. Face the camera.") and a face-visible photo on the back step ("We can see your face. Turn your back to the camera."). Keep the threshold in the posture config and tune it on the golden photos. Also reject the same image file used on both steps.
4. On success show a thumbnail with the skeleton and a "Use this photo" / "Retake" pair; "Use this photo" advances.

Users can go back to any earlier step; changing height or a photo re-runs only what depends on it. When all three are accepted, results render on the same page (no navigation). A "Start over" button clears everything.

## Measurements

All measurements are in image pixels from `toBody()`, then converted.

**Pixel-to-cm scale (per photo):** `cmPerPx = heightCm * 0.936 / earToFloorPx`, where `earToFloorPx` is the vertical distance from the mean ear y to the mean heel y. 0.936 is the average tragion height as a fraction of stature (anthropometric average; good enough for screening). Each photo gets its own scale because each was taken at a different distance.

**Sides:** do not trust MediaPipe's left/right labels for posture (they assume the person faces the camera). Assign anatomical sides by image position: on the front photo the person's right is image-left; on the back photo the person's right is image-right. Findings always use the client's anatomical side ("your right shoulder is lower").

**Side view direction:** decide which way the person faces from nose x vs ear x (nose ahead = facing that way), so "forward" is signed correctly. Use the near-side ear/shoulder/hip/knee/ankle (`nearSide()` in `lib/poses/helpers.ts`).

### Findings

| Region | Finding | View(s) | Measure | Aligned | Slight | Needs work | Weight |
|---|---|---|---|---|---|---|---|
| Head & neck | Forward head | side | horizontal offset of ear ahead of shoulder, cm | ≤ 2.5 | 2.5-5 | > 5 | 20 |
| Head & neck | Head tilt | front, back | ear line vs horizontal, ° | ≤ 2 | 2-5 | > 5 | 10 |
| Shoulders | Shoulder level | front, back | shoulder line vs horizontal, ° (also report height difference in cm) | ≤ 2 | 2-4 | > 4 | 15 |
| Trunk & hips | Trunk shift | front, back | horizontal offset of shoulder midpoint vs hip midpoint, cm | ≤ 1.5 | 1.5-3 | > 3 | 15 |
| Trunk & hips | Hip level | front, back | hip line vs horizontal, ° (also cm) | ≤ 2 | 2-4 | > 4 | 15 |
| Trunk & hips | Hips forward (sway) | side | horizontal offset of hip ahead of ankle, cm | ≤ 3 | 3-6 | > 6 | 10 |
| Knees & feet | Knee hyperextension | side | how far the knee sits behind the hip-ankle line, ° (signed; 0 = straight) | ≤ 5 | 5-10 | > 10 | 10 |
| Knees & feet | Heel alignment | back | each heel→ankle line vs vertical, °, worse side | ≤ 5 | 5-10 | > 10 | 5 |

Weights sum to 100. The forward-head threshold follows the plumb line (earlobe over acromion) rather than the clinical craniovertebral angle (CVA), because MediaPipe has no C7 point. The ear-shoulder angle can be shown as secondary info labeled "ear-shoulder angle (approximates CVA)", never as CVA itself.

**All thresholds are provisional.** They are reasonable starting points from the plumb-line literature, not validated for MediaPipe. They live in one config object so they can be tuned after testing on real photos.

**Front + back findings:** compute each on both photos. The finding's value is the **mean** of the two. If the two disagree on direction (e.g. front says right shoulder lower, back says left) or differ by more than the slight band, show the finding with a note "front and back photos disagree; retake for a reliable reading" and give it a status no worse than slight. Show both per-view values in the finding detail.

**Signed side-view findings (Claude's call):** forward head, hips forward and knee hyperextension are one-sided. A value in the opposite direction (ear behind the shoulder line, hips behind the ankle, knee bent in front of the hip-ankle line) counts as **aligned** in v1, and the measured value is still shown. A standing bent knee is a possible later finding.

**Knee hyperextension angle (Claude's call):** `180° − angle(hip, knee, ankle)`, signed positive when the knee sits behind the hip-ankle line relative to the facing direction. This is the usual recurvatum definition, and the 5°/10° thresholds refer to it.

**Front + back combine rule (Claude's call):** use **signed** values (positive = the client's right side lower or shifted right). The finding's value is the signed mean. They count as disagreeing only when the signs are opposite **and** at least one view is outside the aligned band; small opposite readings near zero are normal noise and get no note. When they disagree, the status is set to **slight** (capped down from needs work, and lifted up from aligned if the mean cancelled toward zero), with the "front and back photos disagree; retake for a reliable reading" note.

**Statuses use raw values (Claude's call);** rounding is for display only.

**Not measurable:** if a required landmark isn't usable (visibility < 0.5 or out of frame), the finding is "not measured" and its weight is excluded from the score, same as the existing `scoreMeasurements`.

### Score

Credit per finding: aligned 1, slight 0.5, needs work 0. Score = round(100 × Σ weight·credit / Σ weight of measured findings). Status display uses the existing colors: aligned = pass (cyan), slight = partial (amber), needs work = fail (rose). Status labels in the UI: "aligned", "slight", "needs work".

### Rounding in copy
cm to the nearest 0.5, degrees to whole numbers. Copy example: "Your ear sits about 4.5 cm ahead of your shoulder line."

## Results page

Top to bottom:
1. **Score header:** score, "posture score · 3 of 3 views", height used.
2. **Photos:** front, side, back thumbnails with overlays. Front/back: skeleton plus horizontal lines across ears, shoulders and hips and a vertical midline; lines for slight/needs-work findings drawn in the status color (like the reference image). Side: skeleton plus a dashed vertical plumb line through the ankle, with ear, shoulder, hip and knee dots colored by status.
3. **Findings by region:** head & neck, shoulders, trunk & hips, knees & feet. Each finding row: label, status pill, measured value. Slight and needs-work rows are expanded by default and show: the measured sentence, a 2-3 sentence explanation, and 3 exercise cards (name, 2-3 step how-to, dosage). Aligned rows are a single collapsed line.
4. **Disclaimer (always visible):** "This is a screening, not a diagnosis. Spine curves and pelvic tilt aren't measured. If you have pain or numbness, see a kinesiologist or physiotherapist."
5. **Start over** button.

## Exercise library

`lib/posture/exercises.ts`: a fixed map from finding id to `{ explanation, exercises: [3 × { name, steps: string[], dosage }] }`. Side-specific findings (shoulder level, hip level, trunk shift, heel alignment) may template the side into the copy. Starting content (builder to write the full copy, Sergio reviews):

- Forward head: chin tucks, doorway pec stretch, wall angels.
- Head tilt: upper trapezius stretch (high side), levator scapulae stretch, chin tucks with a level-gaze check.
- Shoulder level: side-lying lateral raise / shrug on the low side, upper trap stretch on the high side, single-arm farmer carry on the low side.
- Trunk shift: side plank (shifted-toward side), standing side bend stretch, single-leg balance.
- Hip level: side-lying hip abduction, standing hip hike, quadratus lumborum stretch.
- Hips forward (sway): glute bridge, dead bug, half-kneeling hip flexor stretch.
- Knee hyperextension: soft-knee standing practice, hamstring curls (band), calf raises with soft knees.
- Heel alignment: short-foot exercise, single-leg calf raises, towel scrunches.

## Code shape (builder's call within this)

- New `lib/posture/`: pure functions for scale, side assignment, each finding, combining front/back, scoring, plus `thresholds.ts` and `exercises.ts`. No React in `lib/`.
- New route `/posture` with the step flow and results; a `posture` link in `NAV_LINKS`. Home page gets a small entry point to it (placement is the builder's call).
- Reuse `createImageEngine()` and the existing viz components where they fit (`StatusBadge`, `ScoreHeader`, `SkeletonOverlay`/`overlay.ts`).
- The existing yoga pose pipeline (`assessPhoto`, `POSES`, `classify`) is untouched.

## Testing

- Unit tests for every pure function in `lib/posture/` (vitest, `test/`), including side assignment for front vs back, facing direction on side photos, scale, each threshold boundary, front/back disagreement, not-measured handling, and score math.
- Golden tests: extract landmarks from the three local photos in `public/user-1-assets/posture/` with the existing dev extractor (`/dev/extract`) into `data/samples/posture-front.json`, `posture-side.json`, `posture-back.json` (landmark coordinates only; the photos stay gitignored), and snapshot the full assessment with an assumed height of 180 cm (Claude's call). The three photos show three different men, which is fine for regression tests.
- The CSP test must keep passing (no new network origins).

## Left to the builder

- Component structure, state management for the step flow, file names inside `lib/posture/`.
- Silhouette artwork (simple SVG is fine).
- Exact copy for tips, explanations and exercise steps within the guidance above (keep it conservative: no diagnoses, gentle dosages, "stop if it hurts").
- Overlay styling details within the theme.
- Home page entry point placement.
