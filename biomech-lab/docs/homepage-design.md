# Biomech Lab — Homepage Design

**Date:** 2026-10-05 · **Status:** Approved by Sergio (visual companion session)

## Goal

Turn the bare tool page into a one-page product site that explains Biomech Lab to a recruiter in ten seconds and lets them run the demo without leaving the page.

## Decisions

- **Structure:** one page — nav → hero → the lab (existing tool) → how it works → what we check → privacy + about → footer.
- **Visual style:** light health-tech. Warm off-white paper, ink text, Fraunces serif display headings, Inter body, one burnt-orange accent, pill buttons, white rounded cards, Lucide line icons. No gradients or heavy shadows.
- **Hero visual:** Sergio's illustration `public/hero-image-temp.png` (690×440), behind a single swappable constant (`HERO_IMAGE` in `lib/site.ts`). Metadata stripped before commit.
- **Hero buttons:** "Try a sample" scrolls to `#lab`; "Upload a photo" scrolls to `#lab` and switches the lab to its upload tab (window event `biomech:open-upload`).
- **"What we check"** is generated from the pose definitions (`POSES`), not hand-written, so the copy can never drift from the scoring. Live-only checks (Tree stability) are excluded; ratio targets are not shown (they mean nothing to visitors).
- **Copy stays truthful:** no AI-coach or live-camera claims (not built yet); privacy text says the photo never leaves the device and that MediaPipe's telemetry is blocked by the CSP.

## Tokens

| Token | Value | Use |
|---|---|---|
| paper | `#faf7f2` | page background |
| ink | `#1c1917` | text, primary button |
| ink-muted | `#57534e` | body copy |
| ink-subtle | `#78716c` | captions |
| line / line-strong | `#e7e5e4` / `#d6d3d1` | borders |
| accent / accent-soft | `#c2410c` / `#ffedd5` | eyebrows, icons, focus ring, skeleton |
| pass / partial / fail | `#15803d` / `#b45309` / `#b91c1c` | check status (always with icon + text) |

Fonts load via `next/font/google` (self-hosted at build — no new runtime origins, CSP unchanged).

## Sections

1. **Nav (sticky):** logo (PersonStanding icon + "Biomech Lab"), How it works · Poses · Privacy (hidden < sm), GitHub ↗.
2. **Hero:** eyebrow "Movement · Kinesiology · AI", H1 "Move better. / See why.", one-line explanation, two buttons, three chips (photo stays on device · no sign-up · "3 poses · 14 checks" derived from data), hero image.
3. **The lab (`#lab`):** heading + guidance; segmented tabs (Samples / Upload a photo); sample cards with photo, name and view; dashed upload dropzone; spinner while analyzing; results grid (photo + skeleton | score card with per-check rows using status icons).
4. **How it works (`#how`):** Detect → Measure → Score cards.
5. **What we check (`#poses`):** one card per pose: sample photo, view, check list with degree targets.
6. **Privacy (`#privacy`) + About:** "Private by design" card; "Built by Sergio Fruto" card with GitHub and LinkedIn links.
7. **Footer:** "Educational feedback, not medical advice." · "Pose detection by MediaPipe · © 2026 Sergio Fruto".

## Accessibility

Keyboard-reachable controls with a visible accent focus ring; status never by color alone; one H1, H2 per section, H3 for result cards; decorative icons `aria-hidden`; result regions keep `role="status"`; the file input stays focusable (`sr-only`) inside its dropzone label.

## Out of scope

AI coach, live camera, dark mode, new poses, analytics.
