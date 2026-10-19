# Biomech Lab — Lab Instrument Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle Biomech Lab as a dark "lab instrument" product with real-data overlays and charts, and add a `/reports` page with full analyses of the three sample photos.

**Architecture:** Real data only. Landmark files move to `data/samples/`; pure, tested helpers (`lib/overlay.ts`, `lib/gauge.ts`, `lib/check-spec.ts`, `lib/sample-reports.ts`) feed server-rendered SVG visual components (`components/viz/*`). Home sections and the live lab are rebuilt on new dark tokens; the lab's engine/analysis logic is preserved.

**Tech Stack:** Next.js 16.3.7, React 19, Tailwind v4, lucide-react 1.52.0, next/font (Inter + JetBrains Mono), Vitest 5.

**Spec:** `docs/lab-redesign-design.md`

## Global Constraints

- Paths relative to `biomech-lab/`; run commands there. Branch `feat/lab-redesign` (created by the controller). Commit at each task's end; stage only `biomech-lab/` paths; Co-Authored-By trailer naming the model you actually are; no amend, no push.
- Real data only: no invented numbers. The only numeric literals allowed in UI copy are those derived from code (`LANDMARK_COUNT`, `checkSpecRows().length`, `MIN_COVERAGE`, computed scores) and the literal `0` for "bytes uploaded".
- Scoring/classification/readiness logic and thresholds must not change. The only allowed change in `lib/score.ts` is the additive `range` field (Task 1).
- Next 16: `next/image` uses `preload`, not `priority`. No new runtime network origins (CSP unchanged); fonts via `next/font/google` only.
- Status is never conveyed by color alone (icon + text). Decorative icons/SVG get `aria-hidden="true"`; data SVGs get `role="img"` with a descriptive `aria-label`.
- TypeScript strict, no `any`; `npm run lint` clean. Port 3000 may be taken: use `PORT=3100` and stop servers you start.

---

### Task 1: Real-data layer — samples, overlay, gauge, check spec, reports

**Files:**
- Move: `test/fixtures/{warrior2,tree,downdog}.json` → `data/samples/` (`git mv`)
- Create: `data/samples/index.ts`, `data/iterations.ts`, `lib/overlay.ts`, `lib/gauge.ts`, `lib/check-spec.ts`, `lib/sample-reports.ts`
- Modify: `lib/poses/index.ts` (add `POSE_ORDER`), `lib/pose-summaries.ts` (use `POSE_ORDER`), `lib/score.ts` (add `range` to `CheckResult`), `test/golden.test.ts` (fixture path), `components/dev/Extractor.tsx` (heading path text)
- Test: `test/overlay.test.ts`, `test/gauge.test.ts`, `test/check-spec.test.ts`, `test/sample-reports.test.ts`

**Interfaces (produces):**
- `LANDMARK_FILES: Record<string, LandmarkFile>`, `type LandmarkFile = { sample: string; width: number; height: number; people: RawLandmark[][] }`
- `ITERATIONS: Iteration[]`, `type Iteration = { id: number; date: string; device: string; note: string; samples: Record<PoseId, string> }`
- `POSE_ORDER: PoseId[]` = `["warrior2", "tree", "downdog"]`
- `BONES: [Joint, Joint][]`, `OVERLAY_JOINTS: Joint[]`, `overlayGeometry(raw, width, height): { width; height; bones: { x1; y1; x2; y2 }[]; joints: { id: Joint; x; y }[] }`
- `GAUGE_MAX_DEG = 180`, `gaugeGeometry(target, tol, value): { value: number; band: [number, number]; partial: [number, number] }` (all 0..1)
- `checkSpecRows(): CheckSpecRow[]`, `type CheckSpecRow = { poseId: PoseId; pose: string; id: string; label: string; unit: "deg" | "ratio"; target: string; tolerance: string; weight: number }`
- `CheckResult.range: { target: number; tol: number } | null`
- `sampleReports(): SampleReport[]`, `iterationSeries(): IterationPoint[]`, `type SampleReport = { id: PoseId; label: string; view: "front" | "side"; imageSrc: string; width: number; height: number; landmarks: RawLandmark[]; score: number; coverage: number; checks: CheckResult[] }`, `type IterationPoint = { iteration: number; date: string; scores: Record<PoseId, number> }`

- [ ] **Step 1: Move the landmark files and point the golden test at them**

```bash
mkdir -p data/samples
git mv test/fixtures/warrior2.json data/samples/warrior2.json
git mv test/fixtures/tree.json data/samples/tree.json
git mv test/fixtures/downdog.json data/samples/downdog.json
```

In `test/golden.test.ts`, change the `load` function's path and message to:

```ts
  const file = path.join(process.cwd(), "data", "samples", `${id}.json`);
  if (!existsSync(file)) throw new Error(`missing fixture data/samples/${id}.json`);
```

In `components/dev/Extractor.tsx`, change the heading text `test/fixtures/{r.id}.json` to `data/samples/{r.id}.json`.

Run: `npx vitest run test/golden.test.ts` → PASS (same scores).

- [ ] **Step 2: Add `POSE_ORDER`** — append to `lib/poses/index.ts`:

```ts
/** Display order used across the UI and reports. */
export const POSE_ORDER: PoseId[] = ["warrior2", "tree", "downdog"];
```

In `lib/pose-summaries.ts`: delete the local `const ORDER: PoseId[] = [...]`, import `POSE_ORDER` from `./poses`, and use `POSE_ORDER.map(...)` in `poseSummaries()`.

- [ ] **Step 3: Add `range` to `CheckResult`** in `lib/score.ts`: add the field to the type

```ts
  /** Numeric target/tolerance for range checks (null for min checks); used to draw gauges. */
  range: { target: number; tol: number } | null;
```

and in `scoreMeasurements`' returned object add `range: c.kind === "range" ? { target: c.target, tol: c.tol } : null,`. Nothing else in the file changes. Run `npm test` → all pass.

- [ ] **Step 4: Write the failing tests**

`test/gauge.test.ts`:

```ts
import { expect, test } from "vitest";
import { gaugeGeometry } from "@/lib/gauge";

test("maps band, partial band and value onto 0..180°", () => {
  expect(gaugeGeometry(90, 10, 167)).toEqual({
    value: 167 / 180,
    band: [80 / 180, 100 / 180],
    partial: [70 / 180, 110 / 180],
  });
});

test("clamps to the 0..180° domain", () => {
  expect(gaugeGeometry(180, 10, 200)).toEqual({ value: 1, band: [170 / 180, 1], partial: [160 / 180, 1] });
  expect(gaugeGeometry(0, 10, -5)).toEqual({ value: 0, band: [0, 10 / 180], partial: [0, 20 / 180] });
});
```

`test/check-spec.test.ts`:

```ts
import { describe, expect, test } from "vitest";
import { checkSpecRows } from "@/lib/check-spec";

describe("checkSpecRows", () => {
  const rows = checkSpecRows();

  test("one row per photo-mode check, in pose order", () => {
    expect(rows).toHaveLength(14);
    expect(rows[0]).toEqual({
      poseId: "warrior2",
      pose: "Warrior II",
      id: "frontKneeBend",
      label: "Front knee bend",
      unit: "deg",
      target: "90°",
      tolerance: "± 10°",
      weight: 30,
    });
    expect(rows.map((r) => r.id)).not.toContain("stability");
  });

  test("min checks have no tolerance", () => {
    expect(rows.find((r) => r.id === "footOffKnee")).toMatchObject({ target: "≥ 0.15", tolerance: "—" });
  });

  test("weights per pose", () => {
    const sum = (id: string) => rows.filter((r) => r.poseId === id).reduce((n, r) => n + r.weight, 0);
    expect([sum("warrior2"), sum("tree"), sum("downdog")]).toEqual([100, 80, 100]);
  });
});
```

`test/overlay.test.ts`:

```ts
import { expect, test } from "vitest";
import { LANDMARK_FILES } from "@/data/samples";
import { overlayGeometry } from "@/lib/overlay";
import { H, W, WARRIOR2_PX, occlude, rawFromPixels } from "./helpers/synthetic";

test("synthetic figure: pixel-space bones between usable joints only", () => {
  const g = overlayGeometry(rawFromPixels(WARRIOR2_PX), W, H);
  expect(g.width).toBe(W);
  expect(g.bones).toHaveLength(12); // no feet landmarks in the synthetic figure
  expect(g.joints).toHaveLength(13); // nose + 12 limb/torso joints (ears are not drawn)
  const shoulders = g.bones[0];
  expect(shoulders.x1).toBeCloseTo(720, 6);
  expect(shoulders.y1).toBeCloseTo(300, 6);
  expect(shoulders.x2).toBeCloseTo(880, 6);
});

test("occluded joints drop their bones", () => {
  const g = overlayGeometry(occlude(rawFromPixels(WARRIOR2_PX), ["leftKnee"]), W, H);
  expect(g.bones).toHaveLength(10);
  expect(g.joints.map((j) => j.id)).not.toContain("leftKnee");
});

test("real Warrior II sample: full skeleton including feet", () => {
  const f = LANDMARK_FILES.warrior2;
  const g = overlayGeometry(f.people[0], f.width, f.height);
  expect(g.bones).toHaveLength(18);
  expect(g.joints).toHaveLength(17);
});
```

`test/sample-reports.test.ts`:

```ts
import { describe, expect, test } from "vitest";
import { iterationSeries, sampleReports } from "@/lib/sample-reports";

describe("sampleReports", () => {
  const reports = sampleReports();

  test("three reports with the golden scores", () => {
    expect(reports.map((r) => [r.id, r.score])).toEqual([
      ["warrior2", 50],
      ["tree", 55],
      ["downdog", 46],
    ]);
  });

  test("check credits reproduce each score", () => {
    for (const r of reports) {
      const measured = r.checks.filter((c) => c.credit !== null);
      const earned = measured.reduce((s, c) => s + c.weight * (c.credit ?? 0), 0);
      const total = measured.reduce((s, c) => s + c.weight, 0);
      expect(Math.round((100 * earned) / total)).toBe(r.score);
    }
  });

  test("tree flags the foot on the knee", () => {
    const tree = reports.find((r) => r.id === "tree");
    expect(tree?.checks.find((c) => c.id === "footOffKnee")?.status).toBe("fail");
  });

  test("reports carry landmarks and image metadata", () => {
    for (const r of reports) {
      expect(r.landmarks).toHaveLength(33);
      expect(r.imageSrc).toBe(`/samples/${r.id}.jpg`);
      expect([r.width, r.height]).toEqual([1280, 720]);
      expect(r.coverage).toBe(1);
    }
  });
});

test("iterationSeries: iteration 1 matches the reports", () => {
  expect(iterationSeries()).toEqual([
    { iteration: 1, date: "2026-10-01", scores: { warrior2: 50, tree: 55, downdog: 46 } },
  ]);
});
```

- [ ] **Step 5: Run them to verify they fail** — `npx vitest run test/gauge.test.ts test/check-spec.test.ts test/overlay.test.ts test/sample-reports.test.ts` → FAIL (modules missing).

- [ ] **Step 6: `data/samples/index.ts`**

```ts
import type { RawLandmark } from "@/lib/landmarks";
import downdog from "./downdog.json";
import tree from "./tree.json";
import warrior2 from "./warrior2.json";

export type LandmarkFile = { sample: string; width: number; height: number; people: RawLandmark[][] };

/** MediaPipe landmark extractions of the published sample photos (see /dev/extract). */
export const LANDMARK_FILES: Record<string, LandmarkFile> = { warrior2, tree, downdog };
```

(If TypeScript rejects the JSON shape, annotate each import as `warrior2 as LandmarkFile` — do not loosen types to `any`.)

- [ ] **Step 7: `data/iterations.ts`**

```ts
import type { PoseId } from "@/lib/poses";

export type Iteration = {
  id: number;
  date: string;
  device: string;
  note: string;
  /** Landmark file id (key of LANDMARK_FILES) per pose. */
  samples: Record<PoseId, string>;
};

/** Photo iterations of Sergio's practice. Append a new entry (and landmark files) per reshoot. */
export const ITERATIONS: Iteration[] = [
  {
    id: 1,
    date: "2026-10-01",
    device: "DJI Osmo Pocket 3",
    note: "Intentionally imperfect form: the baseline to improve on.",
    samples: { warrior2: "warrior2", tree: "tree", downdog: "downdog" },
  },
];
```

- [ ] **Step 8: `lib/gauge.ts`**

```ts
export const GAUGE_MAX_DEG = 180;

export type GaugeGeometry = { value: number; band: [number, number]; partial: [number, number] };

const unit = (deg: number) => Math.min(GAUGE_MAX_DEG, Math.max(0, deg)) / GAUGE_MAX_DEG;

/** Positions along a 0..180° track (0..1): full-credit band, partial-credit band, measured marker. */
export function gaugeGeometry(target: number, tol: number, value: number): GaugeGeometry {
  return {
    value: unit(value),
    band: [unit(target - tol), unit(target + tol)],
    partial: [unit(target - 2 * tol), unit(target + 2 * tol)],
  };
}
```

- [ ] **Step 9: `lib/check-spec.ts`**

```ts
import { POSE_ORDER, POSES, type PoseId } from "./poses";

export type CheckSpecRow = {
  poseId: PoseId;
  pose: string;
  id: string;
  label: string;
  unit: "deg" | "ratio";
  target: string;
  tolerance: string;
  weight: number;
};

/** Every photo-mode check as a table row, generated from the scoring definitions. */
export function checkSpecRows(): CheckSpecRow[] {
  return POSE_ORDER.flatMap((poseId) =>
    POSES[poseId].checks
      .filter((c) => c.source === "frame")
      .map((c) => {
        const u = c.unit === "deg" ? "°" : "";
        return {
          poseId,
          pose: POSES[poseId].label,
          id: c.id,
          label: c.label,
          unit: c.unit,
          target: c.kind === "range" ? `${c.target}${u}` : `≥ ${c.min}${u}`,
          tolerance: c.kind === "range" ? `± ${c.tol}${u}` : "—",
          weight: c.weight,
        };
      }),
  );
}
```

- [ ] **Step 10: `lib/overlay.ts`**

```ts
import { toBody } from "./body";
import { ALL_JOINTS, type Joint, type RawLandmark } from "./landmarks";

export const BONES: [Joint, Joint][] = [
  ["leftShoulder", "rightShoulder"],
  ["leftShoulder", "leftElbow"],
  ["leftElbow", "leftWrist"],
  ["rightShoulder", "rightElbow"],
  ["rightElbow", "rightWrist"],
  ["leftShoulder", "leftHip"],
  ["rightShoulder", "rightHip"],
  ["leftHip", "rightHip"],
  ["leftHip", "leftKnee"],
  ["leftKnee", "leftAnkle"],
  ["rightHip", "rightKnee"],
  ["rightKnee", "rightAnkle"],
  ["leftAnkle", "leftHeel"],
  ["leftHeel", "leftFootIndex"],
  ["leftAnkle", "leftFootIndex"],
  ["rightAnkle", "rightHeel"],
  ["rightHeel", "rightFootIndex"],
  ["rightAnkle", "rightFootIndex"],
];

/** Joints drawn as dots (ears are omitted to keep the head uncluttered). */
export const OVERLAY_JOINTS: Joint[] = ALL_JOINTS.filter((j) => j !== "leftEar" && j !== "rightEar");

export type OverlayGeometry = {
  width: number;
  height: number;
  bones: { x1: number; y1: number; x2: number; y2: number }[];
  joints: { id: Joint; x: number; y: number }[];
};

/** Pixel-space skeleton geometry; only usable landmarks (visible, inside the frame) are drawn. */
export function overlayGeometry(raw: RawLandmark[], width: number, height: number): OverlayGeometry {
  const body = toBody(raw, width, height);
  const bones = BONES.filter(([a, b]) => body.usable(a) && body.usable(b)).map(([a, b]) => {
    const p = body.point(a);
    const q = body.point(b);
    return { x1: p.x, y1: p.y, x2: q.x, y2: q.y };
  });
  const joints = OVERLAY_JOINTS.filter((j) => body.usable(j)).map((j) => ({ id: j, ...body.point(j) }));
  return { width, height, bones, joints };
}
```

- [ ] **Step 11: `lib/sample-reports.ts`**

```ts
import { ITERATIONS } from "@/data/iterations";
import { LANDMARK_FILES } from "@/data/samples";
import { assessPhoto } from "./assess";
import type { RawLandmark } from "./landmarks";
import { POSE_ORDER, POSES, type PoseId } from "./poses";
import { SAMPLES } from "./samples";
import type { CheckResult } from "./score";

export type SampleReport = {
  id: PoseId;
  label: string;
  view: "front" | "side";
  imageSrc: string;
  width: number;
  height: number;
  landmarks: RawLandmark[];
  score: number;
  coverage: number;
  checks: CheckResult[];
};

export type IterationPoint = { iteration: number; date: string; scores: Record<PoseId, number> };

/** Runs the real assessment pipeline on a stored landmark file. Throws if the sample does not score. */
export function buildReport(id: PoseId, fileId: string = id): SampleReport {
  const file = LANDMARK_FILES[fileId];
  if (!file) throw new Error(`unknown landmark file "${fileId}"`);
  const a = assessPhoto(file.people, file.width, file.height);
  if (a.kind !== "scored" || a.result.score === null) {
    throw new Error(`sample "${fileId}" did not score (${a.kind})`);
  }
  if (a.pose !== id) throw new Error(`sample "${fileId}" classified as ${a.pose}, expected ${id}`);
  return {
    id,
    label: POSES[id].label,
    view: POSES[id].view,
    imageSrc: SAMPLES.find((s) => s.id === id)?.src ?? `/samples/${id}.jpg`,
    width: file.width,
    height: file.height,
    landmarks: file.people[0],
    score: a.result.score,
    coverage: a.readiness.coverage,
    checks: a.result.checks,
  };
}

export function sampleReports(): SampleReport[] {
  const latest = ITERATIONS[ITERATIONS.length - 1];
  return POSE_ORDER.map((id) => buildReport(id, latest.samples[id]));
}

export function iterationSeries(): IterationPoint[] {
  return ITERATIONS.map((it) => ({
    iteration: it.id,
    date: it.date,
    scores: Object.fromEntries(
      POSE_ORDER.map((id) => [id, buildReport(id, it.samples[id]).score]),
    ) as Record<PoseId, number>,
  }));
}
```

- [ ] **Step 12: Run the tests** — the four new files PASS; then `npm test && npm run typecheck && npm run lint` → all pass.

- [ ] **Step 13: Commit** — `feat(biomech-lab): real-data layer — sample landmarks, overlay, gauge, check spec, reports`

---

### Task 2: Dark theme foundation and visualization components

**Files:**
- Modify (replace): `app/globals.css`, `app/layout.tsx`, `components/ui/styles.ts`; modify `lib/site.ts`
- Create: `components/viz/SkeletonOverlay.tsx`, `components/viz/AngleGauge.tsx`, `components/viz/CreditBar.tsx`, `components/viz/StatusBadge.tsx`, `components/viz/CheckRow.tsx`, `components/viz/ScoreHeader.tsx`, `components/viz/IterationChart.tsx`

**Interfaces:**
- Consumes (Task 1): `overlayGeometry`, `gaugeGeometry`, `CheckResult.range`, `IterationPoint`, `POSE_ORDER`.
- Produces: theme colors `bg surface line line-strong fg-strong fg fg-muted fg-subtle accent accent-ink pass partial fail`, fonts `font-sans` (Inter) / `font-mono` (JetBrains Mono); style strings `focusRing buttonPrimary buttonSecondary panel label sectionTitle sectionShell container` (plus temporary aliases `card`, `eyebrow`, `iconTile` until Task 3/4 remove them); `NAV_LINKS`, `APP_VERSION`, `HERO_IMAGE.invertOnDark`; components `<SkeletonOverlay src alt width height landmarks sizes />`, `<AngleGauge target tol value label />`, `<CreditBar earned weight status />`, `<StatusBadge status />`, `<CheckRow check showCue? />` (+ `formatValue`, `earnedPoints`), `<ScoreHeader label score coverage meta? />`, `<IterationChart points />`.

- [ ] **Step 1: Replace `app/globals.css`**

```css
@import "tailwindcss";

@theme {
  --color-bg: #0b0f14;
  --color-surface: #0f172a;
  --color-line: #1e293b;
  --color-line-strong: #334155;
  --color-fg-strong: #f1f5f9;
  --color-fg: #cbd5e1;
  --color-fg-muted: #94a3b8;
  --color-fg-subtle: #8b9ab0;
  --color-accent: #22d3ee;
  --color-accent-ink: #04232a;
  --color-pass: #22d3ee;
  --color-partial: #fbbf24;
  --color-fail: #fb7185;

  --font-sans: var(--font-inter), ui-sans-serif, system-ui, sans-serif;
  --font-mono: var(--font-jetbrains), ui-monospace, SFMono-Regular, Menlo, monospace;
}

html {
  color-scheme: dark;
}

@media (prefers-reduced-motion: no-preference) {
  html {
    scroll-behavior: smooth;
  }
}

body {
  background-color: var(--color-bg);
  background-image:
    linear-gradient(rgb(255 255 255 / 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgb(255 255 255 / 0.03) 1px, transparent 1px);
  background-size: 18px 18px;
  color: var(--color-fg);
  font-family: var(--font-sans);
}
```

- [ ] **Step 2: Replace `app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { HERO_IMAGE, SITE_URL } from "@/lib/site";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains", display: "swap" });

const description =
  "In-browser pose analysis: 33 body landmarks become joint angles and an auditable form score for Warrior II, Tree and Downward Dog. Nothing is uploaded.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "Biomech Lab · Pose analysis in your browser",
  description,
  openGraph: {
    title: "Biomech Lab",
    description,
    images: [{ url: HERO_IMAGE.src, width: HERO_IMAGE.width, height: HERO_IMAGE.height, alt: HERO_IMAGE.alt }],
  },
  twitter: { card: "summary_large_image", title: "Biomech Lab", description, images: [HERO_IMAGE.src] },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
```

- [ ] **Step 3: Replace `components/ui/styles.ts`**

```ts
export const focusRing =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

export const buttonPrimary = `inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-accent-ink transition-colors hover:bg-accent/85 ${focusRing}`;

export const buttonSecondary = `inline-flex items-center gap-2 rounded-md border border-line-strong bg-surface px-4 py-2.5 text-sm font-medium text-fg-strong transition-colors hover:border-accent ${focusRing}`;

export const panel = "rounded-lg border border-line bg-surface";

export const label = "font-mono text-xs uppercase tracking-[0.14em] text-accent";

export const sectionTitle = "mt-2 text-2xl font-bold tracking-tight text-fg-strong md:text-3xl";

export const sectionShell = "scroll-mt-20 border-t border-line";

export const container = "mx-auto max-w-6xl px-6";

/** @deprecated Temporary aliases for components rebuilt in Tasks 3–4; removed there. */
export const card = panel;
export const eyebrow = label;
export const iconTile =
  "inline-flex size-10 items-center justify-center rounded-md border border-line-strong bg-bg text-accent";
```

- [ ] **Step 4: Update `lib/site.ts`** — add `invertOnDark: true,` to `HERO_IMAGE` (with comment `/** Light artwork is inverted + hue-rotated so it reads on the dark theme. */` above it), and append:

```ts
export const APP_VERSION = "v1.1";

export const NAV_LINKS = [
  { href: "/#analyze", label: "analyze" },
  { href: "/reports", label: "reports" },
  { href: "/#pipeline", label: "pipeline" },
  { href: "/#checks", label: "checks" },
  { href: "/#privacy", label: "privacy" },
] as const;
```

- [ ] **Step 5: `components/viz/SkeletonOverlay.tsx`**

```tsx
import Image from "next/image";
import type { RawLandmark } from "@/lib/landmarks";
import { overlayGeometry } from "@/lib/overlay";

export function SkeletonOverlay({
  src,
  alt,
  width,
  height,
  landmarks,
  sizes,
}: {
  src: string;
  alt: string;
  width: number;
  height: number;
  landmarks: RawLandmark[];
  sizes: string;
}) {
  const g = overlayGeometry(landmarks, width, height);
  return (
    <div className="relative overflow-hidden rounded-md border border-line bg-bg">
      <Image
        src={src}
        alt={alt}
        width={width}
        height={height}
        sizes={sizes}
        className="block h-auto w-full brightness-[0.6] saturate-[0.4]"
      />
      <svg viewBox={`0 0 ${width} ${height}`} className="absolute inset-0 h-full w-full" aria-hidden="true">
        <g className="stroke-accent" strokeWidth={4} strokeLinecap="round">
          {g.bones.map((b, i) => (
            <line key={i} x1={b.x1} y1={b.y1} x2={b.x2} y2={b.y2} />
          ))}
        </g>
        <g className="fill-bg stroke-accent" strokeWidth={3}>
          {g.joints.map((j) => (
            <circle key={j.id} cx={j.x} cy={j.y} r={7} />
          ))}
        </g>
      </svg>
    </div>
  );
}
```

- [ ] **Step 6: `components/viz/StatusBadge.tsx`**

```tsx
import { CircleAlert, CircleCheck, CircleMinus, CircleX, type LucideIcon } from "lucide-react";
import type { CheckStatus } from "@/lib/score";

export const STATUS: Record<CheckStatus, { Icon: LucideIcon; text: string; className: string }> = {
  pass: { Icon: CircleCheck, text: "pass", className: "text-pass" },
  partial: { Icon: CircleAlert, text: "partial", className: "text-partial" },
  fail: { Icon: CircleX, text: "fail", className: "text-fail" },
  not_measured: { Icon: CircleMinus, text: "not measured", className: "text-fg-subtle" },
};

export function StatusBadge({ status }: { status: CheckStatus }) {
  const s = STATUS[status];
  return (
    <span className={`inline-flex items-center gap-1 font-mono text-xs ${s.className}`}>
      <s.Icon aria-hidden="true" className="size-3.5" />
      {s.text}
    </span>
  );
}
```

- [ ] **Step 7: `components/viz/AngleGauge.tsx`**

```tsx
import { gaugeGeometry } from "@/lib/gauge";

const TRACK = 200;

export function AngleGauge({
  target,
  tol,
  value,
  label,
}: {
  target: number;
  tol: number;
  value: number | null;
  label: string;
}) {
  const g = gaugeGeometry(target, tol, value ?? target);
  const x = (f: number) => f * TRACK;
  const description =
    value === null
      ? `${label}: not measured; target ${target}° ± ${tol}°`
      : `${label}: measured ${Math.round(value)}°, target ${target}° ± ${tol}°`;
  return (
    <svg viewBox={`0 0 ${TRACK} 24`} className="h-6 w-full" role="img" aria-label={description}>
      <rect x={0} y={9} width={TRACK} height={6} rx={3} className="fill-line" />
      <rect x={x(g.partial[0])} y={9} width={x(g.partial[1]) - x(g.partial[0])} height={6} className="fill-partial/25" />
      <rect x={x(g.band[0])} y={9} width={Math.max(2, x(g.band[1]) - x(g.band[0]))} height={6} className="fill-accent/50" />
      {value !== null && (
        <rect x={Math.min(TRACK - 3, Math.max(0, x(g.value) - 1.5))} y={3} width={3} height={18} rx={1.5} className="fill-fg-strong" />
      )}
    </svg>
  );
}
```

- [ ] **Step 8: `components/viz/CreditBar.tsx`**

```tsx
import type { CheckStatus } from "@/lib/score";

const FILL: Record<CheckStatus, string> = {
  pass: "bg-pass",
  partial: "bg-partial",
  fail: "bg-fail",
  not_measured: "bg-line-strong",
};

export function CreditBar({ earned, weight, status }: { earned: number; weight: number; status: CheckStatus }) {
  const pct = weight === 0 ? 0 : Math.round((earned / weight) * 100);
  return (
    <div className="h-1.5 w-full rounded-full bg-line" role="img" aria-label={`${earned} of ${weight} points`}>
      <div className={`h-full rounded-full ${FILL[status]}`} style={{ width: `${pct}%` }} />
    </div>
  );
}
```

- [ ] **Step 9: `components/viz/CheckRow.tsx`**

```tsx
import type { CheckResult } from "@/lib/score";
import { AngleGauge } from "./AngleGauge";
import { CreditBar } from "./CreditBar";
import { StatusBadge } from "./StatusBadge";

export function formatValue(c: CheckResult): string {
  if (c.value === null) return "—";
  return c.unit === "deg" ? `${Math.round(c.value)}°` : c.value.toFixed(2);
}

export function earnedPoints(c: CheckResult): number {
  return c.credit === null ? 0 : Math.round(c.weight * c.credit * 10) / 10;
}

export function CheckRow({ check, showCue = true }: { check: CheckResult; showCue?: boolean }) {
  const earned = earnedPoints(check);
  const needsWork = check.status === "partial" || check.status === "fail";
  return (
    <li className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1.5 py-3">
      <div>
        <p className="text-sm font-medium text-fg-strong">{check.label}</p>
        {showCue && needsWork && <p className="text-xs text-fg-muted">{check.cue}</p>}
      </div>
      <div className="text-right">
        <p className="font-mono text-sm tabular-nums text-fg-strong">
          {formatValue(check)} <span className="text-fg-subtle">/ {check.targetText}</span>
        </p>
        <StatusBadge status={check.status} />
      </div>
      <div className="col-span-2">
        {check.unit === "deg" && check.range ? (
          <AngleGauge target={check.range.target} tol={check.range.tol} value={check.value} label={check.label} />
        ) : (
          <CreditBar earned={earned} weight={check.weight} status={check.status} />
        )}
      </div>
      <p className="col-span-2 font-mono text-[11px] text-fg-subtle">
        {earned} / {check.weight} pts
      </p>
    </li>
  );
}
```

- [ ] **Step 10: `components/viz/ScoreHeader.tsx`**

```tsx
export function ScoreHeader({
  label,
  score,
  coverage,
  meta,
}: {
  label: string;
  score: number;
  coverage: number;
  meta?: string;
}) {
  const pct = Math.round(coverage * 100);
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="font-mono text-xs uppercase tracking-[0.14em] text-fg-subtle">{label}</p>
        <p className="font-mono text-5xl font-semibold leading-none text-fg-strong">
          {score}
          <span className="ml-1 text-base text-fg-subtle">/100</span>
        </p>
      </div>
      <div className="w-44">
        <p className="font-mono text-xs text-fg-subtle">
          confidence {pct}%{meta ? ` · ${meta}` : ""}
        </p>
        <div className="mt-1 h-1.5 rounded-full bg-line" role="img" aria-label={`Measurement confidence ${pct}%`}>
          <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 11: `components/viz/IterationChart.tsx`**

```tsx
import { POSE_ORDER, POSES, type PoseId } from "@/lib/poses";
import type { IterationPoint } from "@/lib/sample-reports";

const SERIES: Record<PoseId, string> = {
  warrior2: "text-accent",
  tree: "text-partial",
  downdog: "text-fg-strong",
};

const W = 560;
const H = 220;
const PAD = { l: 36, r: 130, t: 12, b: 30 };

export function IterationChart({ points }: { points: IterationPoint[] }) {
  if (points.length === 0) return null;
  const xs = (i: number) =>
    points.length === 1 ? PAD.l + (W - PAD.l - PAD.r) / 2 : PAD.l + (i * (W - PAD.l - PAD.r)) / (points.length - 1);
  const ys = (v: number) => PAD.t + ((100 - v) * (H - PAD.t - PAD.b)) / 100;
  const last = points[points.length - 1];

  // Direct labels at the last point, nudged apart so they never overlap.
  const labels = POSE_ORDER.map((id) => ({ id, y: ys(last.scores[id]) })).sort((a, b) => a.y - b.y);
  for (let i = 1; i < labels.length; i++) {
    if (labels[i].y - labels[i - 1].y < 14) labels[i].y = labels[i - 1].y + 14;
  }

  const description = points
    .map((p) => `iteration ${p.iteration}: ${POSE_ORDER.map((id) => `${POSES[id].label} ${p.scores[id]}`).join(", ")}`)
    .join("; ");

  return (
    <figure>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={`Score by iteration. ${description}`}>
        {[0, 25, 50, 75, 100].map((v) => (
          <g key={v}>
            <line x1={PAD.l} x2={W - PAD.r} y1={ys(v)} y2={ys(v)} className="stroke-line" />
            <text x={PAD.l - 8} y={ys(v) + 4} textAnchor="end" className="fill-fg-subtle font-mono text-[10px]">
              {v}
            </text>
          </g>
        ))}
        {points.map((p, i) => (
          <text key={p.iteration} x={xs(i)} y={H - 8} textAnchor="middle" className="fill-fg-subtle font-mono text-[10px]">
            it.{p.iteration} · {p.date}
          </text>
        ))}
        {POSE_ORDER.map((id) => (
          <g key={id} className={SERIES[id]}>
            {points.length > 1 && (
              <polyline
                points={points.map((p, i) => `${xs(i)},${ys(p.scores[id])}`).join(" ")}
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
              />
            )}
            {points.map((p, i) => (
              <circle key={p.iteration} cx={xs(i)} cy={ys(p.scores[id])} r={4} fill="currentColor" />
            ))}
          </g>
        ))}
        {labels.map(({ id, y }) => (
          <text key={id} x={xs(points.length - 1) + 12} y={y + 4} className={`${SERIES[id]} font-mono text-[11px]`} fill="currentColor">
            {POSES[id].label} {last.scores[id]}
          </text>
        ))}
      </svg>
      {points.length === 1 && (
        <figcaption className="mt-2 font-mono text-xs text-fg-subtle">1 iteration so far · next shoot pending</figcaption>
      )}
    </figure>
  );
}
```

- [ ] **Step 12: Verify and commit** — `npm test && npm run typecheck && npm run lint && npm run build` (the page will look half-restyled; expected). Commit: `feat(biomech-lab): dark lab theme and visualization components`

---

### Task 3: Home page sections

**Files:**
- Modify (replace): `components/SiteNav.tsx`, `components/Hero.tsx`, `components/HeroVisual.tsx`, `components/PrivacyAbout.tsx`, `components/SiteFooter.tsx`, `app/page.tsx`; modify `components/OpenUploadButton.tsx` (scroll target id)
- Create: `components/ReportsTeaser.tsx`, `components/Pipeline.tsx`, `components/CheckSpec.tsx`
- Delete: `components/HowItWorks.tsx`, `components/PoseChecks.tsx`
- Modify: `components/ui/styles.ts` — remove the `eyebrow` and `iconTile` aliases (keep `card` until Task 4)

**Interfaces:** consumes Task 1–2 exports. Section ids: `top`, `analyze`, `pipeline`, `checks`, `privacy`.

- [ ] **Step 1: `components/OpenUploadButton.tsx`** — change `document.getElementById("lab")` to `document.getElementById("analyze")`. Nothing else.

- [ ] **Step 2: Replace `components/SiteNav.tsx`**

```tsx
import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { APP_VERSION, LINKS, NAV_LINKS } from "@/lib/site";
import { container, focusRing } from "./ui/styles";

export function SiteNav() {
  return (
    <header className="sticky top-0 z-10 border-b border-line bg-bg/85 backdrop-blur">
      <nav aria-label="Main" className={`${container} flex items-center justify-between py-3`}>
        <Link href="/" className={`flex items-center gap-2 rounded font-mono text-sm text-fg-strong ${focusRing}`}>
          <span aria-hidden="true" className="text-accent">
            ◉
          </span>
          biomech_lab <span className="text-fg-subtle">{APP_VERSION}</span>
        </Link>
        <ul className="flex items-center gap-5 font-mono text-xs text-fg-muted">
          {NAV_LINKS.map((l) => (
            <li key={l.href} className={l.href === "/reports" ? "" : "hidden md:block"}>
              <Link href={l.href} className={`rounded hover:text-fg-strong ${focusRing}`}>
                {l.label}
              </Link>
            </li>
          ))}
          <li>
            <a
              href={LINKS.github}
              target="_blank"
              rel="noreferrer"
              className={`inline-flex items-center gap-1 rounded text-fg-strong hover:text-accent ${focusRing}`}
            >
              github
              <ArrowUpRight aria-hidden="true" className="size-3.5" />
            </a>
          </li>
        </ul>
      </nav>
    </header>
  );
}
```

- [ ] **Step 3: Replace `components/HeroVisual.tsx`**

```tsx
import Image from "next/image";
import { HERO_IMAGE } from "@/lib/site";
import { panel } from "./ui/styles";

/** Swappable hero artwork — change HERO_IMAGE in lib/site.ts. */
export function HeroVisual() {
  return (
    <figure className={`${panel} overflow-hidden p-2`}>
      <figcaption className="flex items-center justify-between px-2 pb-2 font-mono text-[11px] text-fg-subtle">
        <span>
          <span aria-hidden="true" className="text-accent">
            ●
          </span>{" "}
          reference_figure
        </span>
        <span>illustration</span>
      </figcaption>
      <Image
        src={HERO_IMAGE.src}
        width={HERO_IMAGE.width}
        height={HERO_IMAGE.height}
        alt={HERO_IMAGE.alt}
        preload
        sizes="(min-width: 1152px) 600px, (min-width: 768px) 52vw, 100vw"
        className={`h-auto w-full rounded ${HERO_IMAGE.invertOnDark ? "invert hue-rotate-180" : ""}`}
      />
    </figure>
  );
}
```

- [ ] **Step 4: Replace `components/Hero.tsx`**

```tsx
import { ArrowDown } from "lucide-react";
import { checkSpecRows } from "@/lib/check-spec";
import { LANDMARK_COUNT } from "@/lib/landmarks";
import { POSE_ORDER } from "@/lib/poses";
import { HeroVisual } from "./HeroVisual";
import { OpenUploadButton } from "./OpenUploadButton";
import { buttonPrimary, container, label } from "./ui/styles";

export function Hero() {
  const stats = [
    { value: LANDMARK_COUNT, name: "landmarks" },
    { value: checkSpecRows().length, name: "checks" },
    { value: POSE_ORDER.length, name: "poses" },
    { value: 0, name: "bytes uploaded" },
  ];
  return (
    <section
      id="top"
      className={`${container} grid scroll-mt-20 items-center gap-12 pb-20 pt-14 md:grid-cols-[1fr_1.15fr] md:pt-20`}
    >
      <div>
        <p className={label}>Pose analysis · in-browser · MediaPipe</p>
        <h1 className="mt-4 text-4xl font-bold leading-[1.05] tracking-tight text-fg-strong md:text-6xl">
          Biomechanics,
          <br />
          measured.
        </h1>
        <p className="mt-5 max-w-md text-lg text-fg-muted">
          Body landmarks become joint angles, and joint angles become a score you can audit check by
          check. Your photo never leaves your device.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <a href="#analyze" className={buttonPrimary}>
            Run analysis
            <ArrowDown aria-hidden="true" className="size-4" />
          </a>
          <OpenUploadButton />
        </div>
        <dl className="mt-10 grid max-w-md grid-cols-2 gap-4 sm:grid-cols-4">
          {stats.map((s) => (
            <div key={s.name}>
              <dt className="font-mono text-[11px] text-fg-subtle">{s.name}</dt>
              <dd className="font-mono text-2xl font-semibold text-fg-strong">{s.value}</dd>
            </div>
          ))}
        </dl>
      </div>
      <HeroVisual />
    </section>
  );
}
```

- [ ] **Step 5: `components/ReportsTeaser.tsx`**

```tsx
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { sampleReports } from "@/lib/sample-reports";
import { buttonSecondary, container, label, panel, sectionShell, sectionTitle } from "./ui/styles";

export function ReportsTeaser() {
  const reports = sampleReports();
  return (
    <section aria-labelledby="reports-teaser-title" className={sectionShell}>
      <div className={`${container} py-16`}>
        <div className={`${panel} flex flex-wrap items-center justify-between gap-6 p-6`}>
          <div>
            <p className={label}>02 · Sample reports</p>
            <h2 id="reports-teaser-title" className={sectionTitle}>
              Three real photos, fully measured
            </h2>
            <p className="mt-2 max-w-xl text-fg-muted">
              Skeleton overlays, angle gauges and score breakdowns from iteration 1 of Sergio&apos;s
              practice shots.
            </p>
          </div>
          <dl className="flex gap-6">
            {reports.map((r) => (
              <div key={r.id}>
                <dt className="font-mono text-[11px] text-fg-subtle">{r.label}</dt>
                <dd className="font-mono text-3xl font-semibold text-fg-strong">{r.score}</dd>
              </div>
            ))}
          </dl>
          <Link href="/reports" className={buttonSecondary}>
            Open reports
            <ArrowRight aria-hidden="true" className="size-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 6: `components/Pipeline.tsx`**

```tsx
import { LANDMARK_COUNT } from "@/lib/landmarks";
import { MIN_COVERAGE } from "@/lib/readiness";
import { container, label, panel, sectionShell, sectionTitle } from "./ui/styles";

const STEPS = [
  { key: "input", text: "photo" },
  { key: "detect", text: `MediaPipe · ${LANDMARK_COUNT} landmarks` },
  { key: "project", text: "pixel space (aspect-correct)" },
  { key: "frame", text: "view + framing" },
  { key: "classify", text: "rule-based pose" },
  { key: "gate", text: `readiness ≥ ${Math.round(MIN_COVERAGE * 100)}% coverage` },
  { key: "score", text: "weighted checks → 0–100" },
];

export function Pipeline() {
  return (
    <section id="pipeline" aria-labelledby="pipeline-title" className={sectionShell}>
      <div className={`${container} py-20`}>
        <p className={label}>03 · Pipeline</p>
        <h2 id="pipeline-title" className={sectionTitle}>
          How a score is computed
        </h2>
        <p className="mt-3 max-w-2xl text-fg-muted">
          Deterministic and explainable: the same photo always gets the same score. If the camera
          view, framing or landmark coverage isn&apos;t good enough, the gate returns a prompt
          instead of a number.
        </p>
        <ol className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-7">
          {STEPS.map((s, i) => (
            <li key={s.key} className={`${panel} p-4`}>
              <p className="font-mono text-[11px] text-accent">
                {String(i + 1).padStart(2, "0")} · {s.key}
              </p>
              <p className="mt-2 text-sm text-fg-strong">{s.text}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
```

- [ ] **Step 7: `components/CheckSpec.tsx`**

```tsx
import { checkSpecRows } from "@/lib/check-spec";
import { container, label, panel, sectionShell, sectionTitle } from "./ui/styles";

export function CheckSpec() {
  const rows = checkSpecRows();
  return (
    <section id="checks" aria-labelledby="checks-title" className={sectionShell}>
      <div className={`${container} py-20`}>
        <p className={label}>04 · Check spec</p>
        <h2 id="checks-title" className={sectionTitle}>
          Every rule, in the open
        </h2>
        <p className="mt-3 max-w-2xl text-fg-muted">
          Generated from the scoring code. Full credit inside the tolerance, partial credit up to
          twice the tolerance, zero beyond.
        </p>
        <div className={`${panel} mt-10 overflow-x-auto`}>
          <table className="w-full min-w-[640px] text-left text-sm">
            <caption className="sr-only">Scoring checks per pose</caption>
            <thead className="border-b border-line font-mono text-[11px] uppercase tracking-wider text-fg-subtle">
              <tr>
                <th scope="col" className="px-4 py-3">pose</th>
                <th scope="col" className="px-4 py-3">check_id</th>
                <th scope="col" className="px-4 py-3">measures</th>
                <th scope="col" className="px-4 py-3">target</th>
                <th scope="col" className="px-4 py-3">tolerance</th>
                <th scope="col" className="px-4 py-3 text-right">weight</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map((r) => (
                <tr key={`${r.poseId}-${r.id}`}>
                  <td className="px-4 py-2.5 text-fg-muted">{r.pose}</td>
                  <td className="px-4 py-2.5 font-mono text-accent">{r.id}</td>
                  <td className="px-4 py-2.5 text-fg-strong">{r.label}</td>
                  <td className="px-4 py-2.5 font-mono">{r.target}</td>
                  <td className="px-4 py-2.5 font-mono">{r.tolerance}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{r.weight}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 8: Replace `components/PrivacyAbout.tsx`**

```tsx
import { ArrowUpRight, ShieldCheck, UserRound } from "lucide-react";
import { LINKS } from "@/lib/site";
import { buttonSecondary, container, label, panel, sectionShell, sectionTitle } from "./ui/styles";

const STACK = ["Next.js 16", "TypeScript", "MediaPipe", "Tailwind v4", "Vitest"];

export function PrivacyAbout() {
  return (
    <section id="privacy" aria-labelledby="privacy-title" className={sectionShell}>
      <div className={`${container} py-20`}>
        <p className={label}>05 · Privacy &amp; about</p>
        <h2 id="privacy-title" className={sectionTitle}>
          On-device by design
        </h2>
        <div className="mt-10 grid gap-5 md:grid-cols-2">
          <article className={`${panel} p-6`}>
            <ShieldCheck aria-hidden="true" className="size-5 text-accent" />
            <h3 className="mt-3 font-semibold text-fg-strong">Private</h3>
            <ul className="mt-3 space-y-2 font-mono text-sm text-fg-muted">
              <li>› pose detection runs in your browser</li>
              <li>› 0 bytes of image data uploaded</li>
              <li>› MediaPipe usage telemetry blocked (CSP connect-src)</li>
            </ul>
          </article>
          <article className={`${panel} p-6`}>
            <UserRound aria-hidden="true" className="size-5 text-accent" />
            <h3 className="mt-3 font-semibold text-fg-strong">Built by Sergio Fruto</h3>
            <p className="mt-3 text-sm text-fg-muted">
              Product engineer and kinesiology student, combining biomechanics with applied AI.
            </p>
            <ul className="mt-4 flex flex-wrap gap-2 font-mono text-xs">
              {STACK.map((t) => (
                <li key={t} className="rounded border border-line-strong px-2 py-1 text-fg">
                  {t}
                </li>
              ))}
            </ul>
            <div className="mt-6 flex flex-wrap gap-3">
              <a href={LINKS.github} target="_blank" rel="noreferrer" className={buttonSecondary}>
                Source on GitHub
                <ArrowUpRight aria-hidden="true" className="size-4" />
              </a>
              <a href={LINKS.linkedin} target="_blank" rel="noreferrer" className={buttonSecondary}>
                LinkedIn
                <ArrowUpRight aria-hidden="true" className="size-4" />
              </a>
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 9: Replace `components/SiteFooter.tsx`**

```tsx
import { container } from "./ui/styles";

export function SiteFooter() {
  return (
    <footer className="border-t border-line">
      <div className={`${container} flex flex-wrap justify-between gap-2 py-8 font-mono text-xs text-fg-muted`}>
        <p>educational feedback, not medical advice</p>
        <p>pose detection by MediaPipe · © 2026 Sergio Fruto</p>
      </div>
    </footer>
  );
}
```

- [ ] **Step 10: Replace `app/page.tsx`**

```tsx
import { CheckSpec } from "@/components/CheckSpec";
import { Hero } from "@/components/Hero";
import { PhotoLab } from "@/components/PhotoLab";
import { Pipeline } from "@/components/Pipeline";
import { PrivacyAbout } from "@/components/PrivacyAbout";
import { ReportsTeaser } from "@/components/ReportsTeaser";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteNav } from "@/components/SiteNav";
import { container, label, sectionShell, sectionTitle } from "@/components/ui/styles";

export default function Home() {
  return (
    <>
      <SiteNav />
      <main>
        <Hero />
        <section id="analyze" aria-labelledby="analyze-title" className={sectionShell}>
          <div className={`${container} py-20`}>
            <p className={label}>01 · Analyze</p>
            <h2 id="analyze-title" className={sectionTitle}>
              Run it on a sample or your photo
            </h2>
            <p className="mt-3 max-w-2xl text-fg-muted">
              Warrior II and Tree facing the camera, Downward Dog from the side. Full body in frame.
            </p>
            <div className="mt-10">
              <PhotoLab />
            </div>
          </div>
        </section>
        <ReportsTeaser />
        <Pipeline />
        <CheckSpec />
        <PrivacyAbout />
      </main>
      <SiteFooter />
    </>
  );
}
```

- [ ] **Step 11: Delete the retired sections and aliases**

```bash
git rm components/HowItWorks.tsx components/PoseChecks.tsx
```

Remove the `eyebrow` and `iconTile` exports from `components/ui/styles.ts` (keep `card`). `grep -rn "eyebrow\|iconTile\|HowItWorks\|PoseChecks" app components lib` must return nothing.

- [ ] **Step 12: Verify and commit** — `npm test && npm run typecheck && npm run lint && npm run build`. Commit: `feat(biomech-lab): dark home — hero, reports teaser, pipeline, check spec, privacy`

---

### Task 4: Restyle the live lab (PhotoLab, AssessmentView, StageCanvas)

**Files:** modify `components/PhotoLab.tsx`, replace `components/AssessmentView.tsx` and `components/StageCanvas.tsx`; remove the `card` alias from `components/ui/styles.ts`.

**Must preserve (byte-for-byte except where stated):** in PhotoLab — `getEngine` and its `.catch` cache reset, both `requestIdRef` guards in `analyze`, `onFile` (object-URL lifecycle and `e.target.value = ""`), both effects (cleanup and `OPEN_UPLOAD_EVENT`). In AssessmentView — every `Assessment` branch, the `result.score === null` branch, the `never` guard, `role="status"` on result regions; `role="alert"` on PhotoLab's error.

- [ ] **Step 1: PhotoLab — measure detection time.** Extend the `done` state type with `detectMs: number`. In `analyze`, replace only the line `const detection = engine.detectImage(image);` with:

```tsx
      const t0 = performance.now();
      const detection = engine.detectImage(image);
      const detectMs = Math.round(performance.now() - t0);
```

and add `detectMs,` to the `setState({ status: "done", ... })` object. No other changes to `analyze`.

- [ ] **Step 2: PhotoLab — restyle.** Change the imports from `./ui/styles` to `buttonSecondary, focusRing, panel`. Replace the `tabClass` helper and the returned JSX with:

```tsx
  const tabClass = (active: boolean) =>
    `rounded px-3 py-1.5 font-mono text-xs transition-colors ${focusRing} ${
      active ? "bg-accent text-accent-ink" : "text-fg-muted hover:text-fg-strong"
    }`;

  return (
    <div>
      <div role="group" aria-label="Choose input" className="inline-flex rounded-md border border-line bg-surface p-1">
        <button type="button" aria-pressed={tab === "samples"} className={tabClass(tab === "samples")} onClick={() => setTab("samples")}>
          samples
        </button>
        <button type="button" aria-pressed={tab === "upload"} className={tabClass(tab === "upload")} onClick={() => setTab("upload")}>
          upload photo
        </button>
      </div>

      <div className="mt-6">
        {tab === "samples" ? (
          <div className="grid gap-4 sm:grid-cols-3">
            {SAMPLES.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => void analyze(s.src)}
                className={`${panel} overflow-hidden text-left transition-colors hover:border-accent ${focusRing}`}
              >
                <Image
                  src={s.src}
                  alt=""
                  width={640}
                  height={360}
                  sizes="(min-width: 640px) 360px, 100vw"
                  className="aspect-video w-full object-cover brightness-[0.8]"
                />
                <span className="flex items-center justify-between gap-2 px-4 py-3">
                  <span className="text-sm font-medium text-fg-strong">{s.label}</span>
                  <span className="font-mono text-[11px] text-fg-subtle">{viewLabel(POSES[s.id].view).toLowerCase()}</span>
                </span>
              </button>
            ))}
          </div>
        ) : (
          <label className="flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed border-line-strong bg-surface px-6 py-12 text-center transition-colors hover:border-accent has-[input:focus-visible]:outline-2 has-[input:focus-visible]:outline-offset-2 has-[input:focus-visible]:outline-accent">
            <ImageUp aria-hidden="true" className="size-8 text-accent" />
            <span className="font-medium text-fg-strong">Choose a full-body photo</span>
            <span className="max-w-md text-sm text-fg-muted">
              Warrior II and Tree facing the camera, Downward Dog from the side. Processed locally;
              nothing is uploaded.
            </span>
            <input type="file" accept="image/*" onChange={onFile} className="sr-only" />
          </label>
        )}
      </div>

      {state.status === "working" && (
        <p role="status" className="mt-8 flex items-center gap-2 font-mono text-sm text-fg-muted">
          <LoaderCircle aria-hidden="true" className="size-4 animate-spin text-accent" />
          analyzing… the first run downloads the pose model
        </p>
      )}
      {state.status === "error" && (
        <div role="alert" className={`mt-8 flex flex-wrap items-center gap-4 ${panel} border-fail/40 p-5`}>
          <TriangleAlert aria-hidden="true" className="size-5 text-fail" />
          <p className="flex-1 text-fg-strong">{state.message}</p>
          {lastSrc && (
            <button type="button" className={buttonSecondary} onClick={() => void analyze(lastSrc)}>
              <RotateCcw aria-hidden="true" className="size-4" />
              Try again
            </button>
          )}
        </div>
      )}
      {state.status === "done" && (
        <div className="mt-8 grid items-start gap-6 lg:grid-cols-[1.15fr_1fr]">
          <StageCanvas image={state.image} person={state.person} />
          <AssessmentView assessment={state.assessment} meta={`detect ${state.detectMs} ms`} />
        </div>
      )}
    </div>
  );
```

- [ ] **Step 3: Replace `components/StageCanvas.tsx`** (draws the same geometry as the reports via `overlayGeometry`)

```tsx
"use client";

import { useEffect, useRef } from "react";
import type { RawLandmark } from "@/lib/landmarks";
import { overlayGeometry } from "@/lib/overlay";

const MAX_WIDTH = 720;
const ACCENT = "#22d3ee";
const BG = "#0b0f14";

export function StageCanvas({ image, person }: { image: HTMLImageElement; person: RawLandmark[] | null }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const scale = Math.min(1, MAX_WIDTH / image.naturalWidth);
    canvas.width = Math.round(image.naturalWidth * scale);
    canvas.height = Math.round(image.naturalHeight * scale);
    ctx.filter = "brightness(0.65) saturate(0.5)";
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    ctx.filter = "none";
    if (!person) return;

    const g = overlayGeometry(person, canvas.width, canvas.height);
    ctx.lineCap = "round";
    ctx.lineWidth = 3;
    ctx.strokeStyle = ACCENT;
    for (const b of g.bones) {
      ctx.beginPath();
      ctx.moveTo(b.x1, b.y1);
      ctx.lineTo(b.x2, b.y2);
      ctx.stroke();
    }
    ctx.fillStyle = BG;
    ctx.lineWidth = 2;
    for (const j of g.joints) {
      ctx.beginPath();
      ctx.arc(j.x, j.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
  }, [image, person]);

  return (
    <canvas
      ref={ref}
      role="img"
      aria-label="Your photo with the detected skeleton"
      className="w-full rounded-md border border-line bg-bg"
    />
  );
}
```

- [ ] **Step 4: Replace `components/AssessmentView.tsx`**

```tsx
import { Info, TriangleAlert } from "lucide-react";
import type { Assessment } from "@/lib/assess";
import { POSES } from "@/lib/poses";
import { CheckRow } from "./viz/CheckRow";
import { ScoreHeader } from "./viz/ScoreHeader";

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div role="status" className="flex gap-3 rounded-lg border border-line bg-surface p-5">
      <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-accent" />
      <p className="text-fg-strong">{children}</p>
    </div>
  );
}

export function AssessmentView({ assessment, meta }: { assessment: Assessment; meta?: string }) {
  switch (assessment.kind) {
    case "no_person":
      return <Notice>We couldn&apos;t find a person. Step back so your whole body is in frame.</Notice>;
    case "multiple_people":
      return <Notice>Make sure you&apos;re alone in the frame.</Notice>;
    case "unknown_pose":
      return (
        <Notice>
          We didn&apos;t recognize the pose. Try Warrior II or Tree facing the camera, or Downward
          Dog from the side.
        </Notice>
      );
    case "not_ready":
      return (
        <section role="status" className="rounded-lg border border-partial/40 bg-surface p-6">
          <div className="flex items-center gap-2">
            <TriangleAlert aria-hidden="true" className="size-5 text-partial" />
            <h3 className="font-semibold text-fg-strong">
              {POSES[assessment.pose].label} detected — we can&apos;t score it yet
            </h3>
          </div>
          <ul className="mt-3 list-disc space-y-1 pl-6 text-fg-muted">
            {assessment.messages.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </section>
      );
    case "scored": {
      const { result, readiness } = assessment;
      if (result.score === null) {
        return (
          <Notice>
            We couldn&apos;t measure enough of your pose to score it. Adjust your position or
            lighting.
          </Notice>
        );
      }
      return (
        <section role="status" className="rounded-lg border border-line bg-surface p-6">
          <h3 className="sr-only">{POSES[assessment.pose].label} result</h3>
          <ScoreHeader label={POSES[assessment.pose].label} score={result.score} coverage={readiness.coverage} meta={meta} />
          <ul className="mt-4 divide-y divide-line">
            {result.checks.map((c) => (
              <CheckRow key={c.id} check={c} />
            ))}
          </ul>
        </section>
      );
    }
    default: {
      const _exhaustive: never = assessment;
      return _exhaustive;
    }
  }
}
```

- [ ] **Step 5: Remove the `card` alias** from `components/ui/styles.ts` (and its `@deprecated` comment if no aliases remain). `grep -rn "\bcard\b" components app` must show no import of it.

- [ ] **Step 6: Verify and commit** — `npm test && npm run typecheck && npm run lint && npm run build`. Commit: `feat(biomech-lab): lab instrument styling for the live analyzer (gauges, credit bars, detect time)`

---

### Task 5: `/reports` page

**Files:** create `components/ReportCard.tsx`, `app/reports/page.tsx`.

- [ ] **Step 1: `components/ReportCard.tsx`**

```tsx
import { viewLabel } from "@/lib/pose-summaries";
import type { SampleReport } from "@/lib/sample-reports";
import { panel } from "./ui/styles";
import { CheckRow, formatValue } from "./viz/CheckRow";
import { ScoreHeader } from "./viz/ScoreHeader";
import { SkeletonOverlay } from "./viz/SkeletonOverlay";
import { StatusBadge } from "./viz/StatusBadge";

export function ReportCard({ report }: { report: SampleReport }) {
  const flagged = report.checks.filter((c) => c.status === "fail" || c.status === "partial");
  return (
    <article aria-labelledby={`report-${report.id}`} className={`${panel} grid gap-6 p-5 lg:grid-cols-[1.25fr_1fr]`}>
      <div>
        <div className="mb-2 flex justify-between font-mono text-[11px] text-fg-subtle">
          <span>
            <span aria-hidden="true" className="text-accent">
              ●
            </span>{" "}
            {report.id}.jpg
          </span>
          <span>
            {report.width}×{report.height} · {viewLabel(report.view).toLowerCase()}
          </span>
        </div>
        <SkeletonOverlay
          src={report.imageSrc}
          alt={`${report.label} sample photo with the detected skeleton`}
          width={report.width}
          height={report.height}
          landmarks={report.landmarks}
          sizes="(min-width: 1024px) 640px, 100vw"
        />
        {flagged.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2" aria-label="Checks that need work">
            {flagged.map((c) => (
              <li key={c.id} className="flex items-center gap-2 rounded border border-line-strong bg-bg px-2 py-1">
                <StatusBadge status={c.status} />
                <span className="font-mono text-xs text-fg-strong">
                  {c.id} {formatValue(c)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <h2 id={`report-${report.id}`} className="sr-only">
          {report.label} report
        </h2>
        <ScoreHeader label={report.label} score={report.score} coverage={report.coverage} />
        <ul className="mt-4 divide-y divide-line">
          {report.checks.map((c) => (
            <CheckRow key={c.id} check={c} />
          ))}
        </ul>
      </div>
    </article>
  );
}
```

- [ ] **Step 2: `app/reports/page.tsx`**

```tsx
import type { Metadata } from "next";
import Link from "next/link";
import { ReportCard } from "@/components/ReportCard";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteNav } from "@/components/SiteNav";
import { container, focusRing, label, panel } from "@/components/ui/styles";
import { IterationChart } from "@/components/viz/IterationChart";
import { ITERATIONS } from "@/data/iterations";
import { iterationSeries, sampleReports } from "@/lib/sample-reports";

export const metadata: Metadata = {
  title: "Sample reports · Biomech Lab",
  description:
    "Full pose analyses of three real photos: skeleton overlays, joint-angle gauges and score breakdowns, computed in the browser pipeline.",
};

export default function ReportsPage() {
  const reports = sampleReports();
  const series = iterationSeries();
  const latest = ITERATIONS[ITERATIONS.length - 1];
  return (
    <>
      <SiteNav />
      <main className={`${container} py-14`}>
        <p className={label}>Sample reports · iteration {latest.id}</p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight text-fg-strong md:text-5xl">
          Three real photos, fully measured
        </h1>
        <p className="mt-4 max-w-2xl text-fg-muted">
          {latest.date} · {latest.device}. {latest.note} Scores come from the same code that runs in
          the analyzer.
        </p>
        <div className="mt-12 space-y-10">
          {reports.map((r) => (
            <ReportCard key={r.id} report={r} />
          ))}
        </div>
        <section aria-labelledby="iterations-title" className={`${panel} mt-12 p-6`}>
          <p className={label}>Progress</p>
          <h2 id="iterations-title" className="mt-2 text-xl font-bold text-fg-strong">
            Score by iteration
          </h2>
          <div className="mt-6">
            <IterationChart points={series} />
          </div>
        </section>
        <p className="mt-10 font-mono text-sm text-fg-muted">
          method:{" "}
          <Link href="/#pipeline" className={`rounded text-accent hover:underline ${focusRing}`}>
            pipeline
          </Link>{" "}
          ·{" "}
          <Link href="/#checks" className={`rounded text-accent hover:underline ${focusRing}`}>
            check spec
          </Link>
        </p>
      </main>
      <SiteFooter />
    </>
  );
}
```

- [ ] **Step 3: Verify and commit** — `npm test && npm run typecheck && npm run lint && npm run build` (the build output must list `/reports` as a static route). Commit: `feat(biomech-lab): /reports page with sample analyses and iteration chart`

---

### Task 6: Verification (controller) and release

- [ ] Production build on :3100 — home: hero (inverted illustration), analyze (three samples score 50 / 55 / 46 with gauges, credit bars, `detect N ms`), reports teaser, pipeline, check spec (14 rows), privacy; `/reports`: three report cards with overlays and flagged chips, iteration chart; nav links work from both pages; 390 px iframe has no horizontal overflow; keyboard focus visible; console clean; external requests only jsDelivr + Google Storage.
- [ ] Final whole-branch review → fix wave → push branch (Vercel preview, login-protected) → on approval merge to `main` and verify production.
