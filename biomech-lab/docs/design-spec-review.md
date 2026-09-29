# Biomech Lab - Design Spec Review

**Reviewed:** 2026-09-29
**Scope:** `design-spec.md` v1 proposal

## Summary

The proposal has a strong foundation: browser-local pose processing, pure scoring modules,
deterministic results, and graceful coach failure handling. The principal v1 risk is the
reliability of measurements from real-world camera angles. The decisions below should be
made before implementation so a polished UI does not present unreliable scores as facts.

## Priority Findings

### 1. Make camera orientation an explicit input

Warrior II and Tree require a front view, while Downward Dog requires a side view. The
spec sends `view` to the coach API but does not say how the application determines or
collects it.

Add a required, pose-specific capture guide and a front/side selection control. Define
mirrored-camera handling and how left/right landmarks are canonicalized before any
classification or scoring.

**Acceptance criteria**

- Each pose states its accepted view and rejects incompatible framing.
- Mirrored and non-mirrored camera feeds yield the same score.
- The scorer can identify the front or standing leg deterministically.

### 2. Gate scoring on measurement readiness

Excluding unmeasured checks from the denominator can produce a high score based on a
small visible subset of joints. A numeric score should only appear when enough of the
pose can be measured reliably.

Add an `AssessmentReadiness` result before scoring:

```ts
type AssessmentReadiness = {
  canScore: boolean;
  view: "front" | "side";
  coverage: number;
  reasons: Array<
    "low_visibility" | "wrong_view" | "multiple_people" | "bad_framing"
  >;
};
```

Use the required landmark weights to calculate coverage. If coverage is below an agreed
threshold, such as 70%, show a clear reframe prompt rather than a score.

**Acceptance criteria**

- An empty or low-coverage measurement cannot yield a score.
- Results show measurement confidence separately from posture score.
- Every check declares its required landmarks.

### 3. Define the geometry contract precisely

Terms including "near the floor line", "aligned", "low", and "front knee" are not yet
executable definitions. The geometry module should define coordinate orientation, angle
ranges, signed versus unsigned tilts, normalization bases, landmark dependencies, and
the exact test for each qualitative condition.

Do not claim that a feature is measured if it cannot be reliably inferred from a 2D
camera. For example, reframe "head relaxed" as a measurable head-to-arm alignment check.

**Acceptance criteria**

- Each check has a named measurement function with documented units and bounds.
- Every qualitative target has a numerical rule and tolerance.
- Camera rotation and out-of-plane poses trigger a readiness failure where needed.

### 4. Resolve the multi-person behavior

Multi-person scenes are a v1 non-goal, but the error handling proposes selecting the
most visible person. This creates avoidable ambiguity.

Reject multi-person frames and ask the visitor to be alone in the image. Configure the
pose detector and UI around that rule.

### 5. Separate photo and live processing paths

A static photo cannot collect a three-second window. Specify photo and sample processing
as `detect -> classify -> readiness -> single-frame score`. Only live mode should run the
temporal aggregation, stability check, and countdown.

### 6. Harden the coach API boundary

The browser should not be authoritative for `score` or `target`. The API should map known
pose and check identifiers to server-owned targets, cues, and allowed ranges. Client
values can remain inputs for a best-effort coaching demo, but all prompt text should be
assembled from server-owned mappings.

Reserve the per-IP and global daily quota atomically before starting an LLM stream. Define
the global daily-cap timezone and fail closed, with a friendly unavailable state, if Redis
cannot enforce a limit.

### 7. Clarify privacy and coaching safety

The statement that camera data never leaves the device is correct for images and video,
but derived measurements and the request IP reach Vercel when a visitor requests coaching.
Use wording such as: "Images and video stay on your device; only anonymous measurement
results are sent when you request coaching." Link to a short privacy note.

Use a deterministic, allowlisted exercise catalog mapped to check IDs. Let the LLM explain
the selected exercises rather than inventing them. Keep the explicit non-diagnostic,
non-medical framing in the results and coach output.

### 8. Expand validation beyond static fixtures

The planned fixtures are useful regression tests but do not establish reliable behavior
across common capture failures. Add golden cases for mirrored inputs, left/right variants,
partial occlusion, wrong views, bad framing, multiple people, and insufficient coverage.

Add one browser-level flow test with a mocked pose engine to cover camera denial,
countdown, score gating, and coach fallback. Assert that image bytes are never included in
the coach request.

## Recommended Implementation Order

1. Define the geometry, view, and readiness contracts, then unit test them.
2. Implement photo and sample scoring against known-good fixtures.
3. Add live capture, temporal aggregation, and framing feedback.
4. Add the rate-limited coach API using server-owned check definitions.
5. Finish accessibility, browser compatibility, and privacy-network checks before launch.

## Launch Gates

- No numeric score is shown for an unsupported view or inadequate landmark coverage.
- All three samples produce stable, documented expected score ranges.
- The app handles camera denial, model load failure, multi-person input, and coach limits.
- Network inspection confirms images and video do not leave the browser.
- The user can operate input selection, retry, and results with keyboard and non-color-only
  status cues.
