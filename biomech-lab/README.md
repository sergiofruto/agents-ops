# Biomech Lab

Upload a photo of a yoga pose and get a posture score. MediaPipe's pose
detector finds your joints and a geometry-based scorer checks them against
the pose's target angles — all in the browser, nothing uploaded anywhere.

## Privacy

Your photo never leaves your device: detection and scoring both run
client-side. The only network calls are fetching the MediaPipe WASM runtime
and model files. MediaPipe's built-in usage-telemetry endpoint is blocked by
this app's Content-Security-Policy (see `lib/csp.ts`).

## How scoring works

Three poses are supported today: Warrior II, Tree, and Downward Dog. For
each pose, the detected landmarks are turned into joint angles and
distances, and each one is checked against a target (e.g. "front knee bent
to 90° ± 10°"). Before any score is shown, a readiness gate checks that
enough of the required joints are visible and in frame — if coverage is too
low, or the pose/view doesn't match, you get specific feedback instead of a
number. No numeric score is ever shown when the readiness gate fails.

## Dev commands

```bash
npm install
npm run dev        # http://localhost:3000
npm test           # vitest
npm run typecheck
npm run lint
npm run build
```

`/dev/extract` is a dev-only page that runs MediaPipe against the sample
photos in `public/samples` and prints the landmark JSON used to (re)build
the fixtures in `test/fixtures/`.

## Status

**Day 1 (this branch):** upload-a-photo path — detect, classify, readiness
check, single-frame score.

**Day 2 (planned):** live camera feed, an AI coach, and deployment.

See `docs/design-spec.md` for the full design spec.
