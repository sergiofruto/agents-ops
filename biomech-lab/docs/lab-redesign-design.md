# Biomech Lab — "Lab Instrument" Redesign

**Date:** 2026-10-07 · **Status:** Approved by Sergio (visual companion: direction B, layout, hero option 2)
**Replaces:** the light health-tech styling in `homepage-design.md` (structure and data helpers carry over).

## Goal

Make Biomech Lab read as a technical analysis product: dark instrument UI, mono technical labels, real overlays (dots + lines + angles) and real-data charts. Every number and chart is computed from real data — nothing decorative or invented.

## Pages

### `/` — home
1. **Nav (sticky):** `◉ biomech_lab` + version in mono; links: analyze · reports · pipeline · checks · privacy · github ↗ (links other than github and reports hidden < sm).
2. **Hero:** eyebrow `POSE ANALYSIS · IN-BROWSER · MEDIAPIPE`, H1 "Biomechanics, measured.", one-line pitch, buttons "Run analysis ↓" (→ `#analyze`) and "Upload photo" (opens upload tab, existing event), stat row computed from data: 33 landmarks · 14 checks · 3 poses · 0 bytes uploaded. Visual: Sergio's illustration (`HERO_IMAGE`) in a dark bordered frame, rendered with CSS `filter: invert(1) hue-rotate(180deg)` (controlled by `HERO_IMAGE.invertOnDark`).
3. **Analyze (`#analyze`):** the existing tool, restyled. Results add: an **angle gauge** per degree check (target band ± tol, partial band to ± 2·tol, measured marker), a credit bar per check, a confidence meter, and **measured detection time** (ms around `detectImage`, shown as `detect 41 ms`).
4. **Reports teaser:** panel linking to `/reports` with the three sample scores (computed).
5. **Pipeline (`#pipeline`):** flow diagram — image → MediaPipe (33 pts) → pixel space → view + framing → classify → readiness gate (≥ 70% coverage) → checks → score.
6. **Check spec (`#checks`):** table of every photo-mode check — pose, check id, label, target, tolerance, weight — generated from `POSES` (no hand-written rows).
7. **Privacy (`#privacy`) + About:** on-device processing, 0 bytes uploaded, MediaPipe telemetry blocked by CSP `connect-src`; built by Sergio Fruto with GitHub/LinkedIn links.
8. **Footer:** educational feedback, not medical advice · pose detection by MediaPipe.

### `/reports` — sample reports (new, statically rendered)
- One report per sample (Warrior II, Tree, Downward Dog): photo with **server-rendered SVG overlay** from stored landmarks (bones incl. feet, joints), a row of status chips for failing/partial checks (check id + measured value), score, confidence, pose/view, and per-check rows with an **angle gauge** (degree range checks) or a **credit bar** (other checks) plus earned/available points.
- **Score by iteration** chart: one series per pose across photo iterations (iteration 1 = 2026-10-01, Osmo Pocket 3, intentionally imperfect form). With one iteration it shows points plus "next shoot pending".
- Method note linking to the pipeline and check spec.

## Data

- Landmark files move from `test/fixtures/` to `data/samples/` (`warrior2.json`, `tree.json`, `downdog.json`); golden tests read from the new path. Production code never imports from `test/`.
- `data/iterations.ts` lists iterations: `{ id, date, device, note, samples: Record<PoseId, string /* landmark file id */> }`.
- `lib/sample-reports.ts` builds reports at build time with the existing `assessPhoto` → identical scores to the golden tests (50 / 55 / 46).
- `lib/overlay.ts` (pure): bone list + landmarks → pixel-space line/joint geometry (shared by the server overlay and the live canvas).
- `CheckResult` gains `range: { target; tol } | null` so gauges can be drawn (output-only addition; scoring unchanged).
- `lib/gauge.ts` (pure): maps a degree check (target, tol, value) to gauge geometry (domain 0–180°).
- `lib/check-spec.ts` (pure): rows for the check-spec table from `POSES`.

## Tokens

| Token | Value | Use | Contrast on bg |
|---|---|---|---|
| bg | `#0b0f14` | page (+ faint 18px grid) | — |
| surface | `#0f172a` | panels | — |
| line / line-strong | `#1e293b` / `#334155` | borders, gauge tracks | — |
| fg-strong | `#f1f5f9` | headings, numbers | ≫ 7:1 |
| fg | `#cbd5e1` | body | 12.9:1 |
| fg-muted | `#94a3b8` | secondary | 7.5:1 |
| fg-subtle | `#8b9ab0` | labels, captions | 6.7:1 |
| accent | `#22d3ee` | skeleton, primary button, focus ring, pass | 10.6:1 |
| partial | `#fbbf24` | partial credit | 11.5:1 |
| fail | `#fb7185` | failing checks, angle tags | 7.1:1 |

Fonts: Inter (UI) + JetBrains Mono (labels, numbers, ids) via `next/font/google` (self-hosted; CSP unchanged). Status is always icon + text.

## Out of scope

AI coach, live camera, new poses, light mode, analytics.
