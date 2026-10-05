# Biomech Lab — Homepage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bare tool page with a one-page product site (nav, hero, lab, how it works, what we check, privacy/about, footer) in the approved light health-tech style.

**Architecture:** Server components for static sections; the existing client `PhotoLab` restyled in place. Design tokens live in `app/globals.css` (Tailwind v4 `@theme`); shared class strings in `components/ui/styles.ts`; site constants in `lib/site.ts`; "What we check" is generated from `POSES` via a tested pure helper.

**Tech Stack:** Next.js 16.3.7, React 19, Tailwind v4, `lucide-react` 1.52.0, `next/font/google` (Fraunces + Inter), Vitest 5.

**Spec:** `docs/homepage-design.md`

## Global Constraints

- All paths relative to `biomech-lab/`. Commands run from `biomech-lab/`.
- Work on branch `feat/homepage` (created by the controller). Commit at each task's end; stage only `biomech-lab/` paths; Co-Authored-By trailer naming the model you actually are; no amend, no push.
- Next 16: `next/image` uses `preload` (NOT the deprecated `priority`). Read `node_modules/next/dist/docs/` before using any other API you're unsure of.
- No new runtime network origins (the CSP `connect-src` must stay unchanged). Fonts via `next/font/google` only.
- Do not change any scoring logic, thresholds or tests other than those named here.
- Status is never conveyed by color alone (icon + text). Decorative icons get `aria-hidden="true"`.
- TypeScript strict, no `any`. `npm run lint` must be clean.

---

### Task 1: Foundation — tokens, fonts, constants, data helper

**Files:**
- Modify: `package.json` (add `lucide-react` 1.52.0), `app/globals.css`, `app/layout.tsx`, `lib/score.ts` (export `targetText`), `components/PhotoLab.tsx` and `components/dev/Extractor.tsx` (import `SAMPLES` from `lib/samples`)
- Create: `lib/site.ts`, `lib/samples.ts`, `lib/events.ts`, `lib/pose-summaries.ts`, `components/ui/styles.ts`
- Test: `test/pose-summaries.test.ts`
- Asset: strip metadata from `public/hero-image-temp.png`

**Interfaces:**
- Produces: `SITE_URL`, `LINKS.{github,linkedin}`, `HERO_IMAGE.{src,width,height,alt}`; `SAMPLES` (`{ id: PoseId; src; label }[]`); `OPEN_UPLOAD_EVENT`; `targetText(check)`; `viewLabel(view)`, `poseSummaries(): PoseSummary[]` with `PoseSummary = { id; label; viewLabel; checks: { id; label; target: string | null }[] }`; class strings `focusRing`, `buttonPrimary`, `buttonSecondary`, `card`, `eyebrow`, `iconTile`; Tailwind colors `paper ink ink-muted ink-subtle line line-strong accent accent-soft pass partial fail`, fonts `font-sans` (Inter) and `font-display` (Fraunces).

- [ ] **Step 1: Install the icon library (exact pin)**

```bash
npm install --save-exact lucide-react@1.52.0
```

- [ ] **Step 2: Write the failing test** — `test/pose-summaries.test.ts`

```ts
import { describe, expect, test } from "vitest";
import { poseSummaries, viewLabel } from "@/lib/pose-summaries";

describe("poseSummaries", () => {
  const s = poseSummaries();
  const pose = (id: string) => {
    const p = s.find((x) => x.id === id);
    if (!p) throw new Error(`missing ${id}`);
    return p;
  };

  test("three poses in display order", () => {
    expect(s.map((p) => p.id)).toEqual(["warrior2", "tree", "downdog"]);
  });

  test("lists photo-mode checks only (live-only stability excluded)", () => {
    expect(pose("tree").checks.map((c) => c.id)).toEqual([
      "standingLeg",
      "footOffKnee",
      "hipsLevel",
      "torsoUpright",
    ]);
    expect(pose("warrior2").checks).toHaveLength(5);
    expect(pose("downdog").checks).toHaveLength(5);
  });

  test("degree targets are human-readable; ratio targets are hidden", () => {
    expect(pose("warrior2").checks[0]).toEqual({
      id: "frontKneeBend",
      label: "Front knee bend",
      target: "90° ± 10°",
    });
    expect(pose("tree").checks.find((c) => c.id === "footOffKnee")?.target).toBeNull();
    expect(pose("downdog").checks.find((c) => c.id === "headAligned")?.target).toBeNull();
  });

  test("view labels", () => {
    expect(viewLabel("front")).toBe("Facing the camera");
    expect(pose("downdog").viewLabel).toBe("Side view");
  });
});
```

- [ ] **Step 3: Run it to verify it fails** — `npx vitest run test/pose-summaries.test.ts` → FAIL (cannot resolve `@/lib/pose-summaries`).

- [ ] **Step 4: Export `targetText` from `lib/score.ts`** — change `function targetText(c: CheckDef): string {` to `export function targetText(c: CheckDef): string {`. Nothing else in that file changes.

- [ ] **Step 5: Create `lib/pose-summaries.ts`**

```ts
import { POSES, type PoseId } from "./poses";
import { targetText } from "./score";

export type PoseSummary = {
  id: PoseId;
  label: string;
  viewLabel: string;
  checks: { id: string; label: string; target: string | null }[];
};

const ORDER: PoseId[] = ["warrior2", "tree", "downdog"];

export function viewLabel(view: "front" | "side"): string {
  return view === "front" ? "Facing the camera" : "Side view";
}

/** Human-facing summary of each pose's photo-mode checks, derived from the scoring definitions. */
export function poseSummaries(): PoseSummary[] {
  return ORDER.map((id) => {
    const pose = POSES[id];
    return {
      id,
      label: pose.label,
      viewLabel: viewLabel(pose.view),
      checks: pose.checks
        .filter((c) => c.source === "frame")
        .map((c) => ({ id: c.id, label: c.label, target: c.unit === "deg" ? targetText(c) : null })),
    };
  });
}
```

- [ ] **Step 6: Run the test to verify it passes** — `npx vitest run test/pose-summaries.test.ts` → PASS.

- [ ] **Step 7: Create `lib/site.ts`**

```ts
export const SITE_URL = "https://biomech-lab.vercel.app";

export const LINKS = {
  github: "https://github.com/sergiofruto/agents-ops/tree/main/biomech-lab",
  linkedin: "https://www.linkedin.com/in/sergio-gabriel-fruto/",
} as const;

/** Hero artwork. Swap the file and these values when the final image is ready. */
export const HERO_IMAGE = {
  src: "/hero-image-temp.png",
  width: 690,
  height: 440,
  alt: "Illustration of a person in Warrior II with a skeleton overlay and joint-angle annotations",
} as const;
```

- [ ] **Step 8: Create `lib/samples.ts`** and point both consumers at it

```ts
import type { PoseId } from "./poses";

export const SAMPLES: readonly { id: PoseId; src: string; label: string }[] = [
  { id: "warrior2", src: "/samples/warrior2.jpg", label: "Warrior II" },
  { id: "tree", src: "/samples/tree.jpg", label: "Tree" },
  { id: "downdog", src: "/samples/downdog.jpg", label: "Downward Dog" },
];
```

In `components/PhotoLab.tsx`: delete the local `export const SAMPLES = [...] as const;` block and add `import { SAMPLES } from "@/lib/samples";`. In `components/dev/Extractor.tsx`: change `import { SAMPLES } from "@/components/PhotoLab";` to `import { SAMPLES } from "@/lib/samples";`. (Reason: server components will import `SAMPLES`; values exported from a `"use client"` module can't be used as data on the server.)

- [ ] **Step 9: Create `lib/events.ts`**

```ts
/** Dispatched on window by the hero's "Upload a photo" button; the lab switches to its upload tab. */
export const OPEN_UPLOAD_EVENT = "biomech:open-upload";
```

- [ ] **Step 10: Create `components/ui/styles.ts`**

```ts
export const focusRing =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

export const buttonPrimary = `inline-flex items-center gap-2 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-paper transition-colors hover:bg-ink/85 ${focusRing}`;

export const buttonSecondary = `inline-flex items-center gap-2 rounded-full border border-line-strong bg-white px-5 py-3 text-sm font-semibold text-ink transition-colors hover:border-ink ${focusRing}`;

export const card = "rounded-2xl border border-line bg-white";

export const eyebrow = "text-xs font-semibold uppercase tracking-[0.18em] text-accent";

export const iconTile =
  "inline-flex size-10 items-center justify-center rounded-xl bg-accent-soft text-accent";
```

- [ ] **Step 11: Replace `app/globals.css`**

```css
@import "tailwindcss";

@theme {
  --color-paper: #faf7f2;
  --color-ink: #1c1917;
  --color-ink-muted: #57534e;
  --color-ink-subtle: #78716c;
  --color-line: #e7e5e4;
  --color-line-strong: #d6d3d1;
  --color-accent: #c2410c;
  --color-accent-soft: #ffedd5;
  --color-pass: #15803d;
  --color-partial: #b45309;
  --color-fail: #b91c1c;

  --font-sans: var(--font-inter), ui-sans-serif, system-ui, sans-serif;
  --font-display: var(--font-fraunces), ui-serif, Georgia, serif;
}

html {
  scroll-behavior: smooth;
}

body {
  background: var(--color-paper);
  color: var(--color-ink);
  font-family: var(--font-sans);
}
```

- [ ] **Step 12: Replace `app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Fraunces, Inter } from "next/font/google";
import { HERO_IMAGE, SITE_URL } from "@/lib/site";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces", display: "swap" });

const description =
  "Upload a yoga pose. Biomech Lab detects 33 body landmarks, measures your joint angles and scores your form, privately in your browser.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "Biomech Lab · Score your yoga form in the browser",
  description,
  openGraph: {
    title: "Biomech Lab",
    description,
    images: [{ url: HERO_IMAGE.src, width: HERO_IMAGE.width, height: HERO_IMAGE.height, alt: HERO_IMAGE.alt }],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${fraunces.variable}`}>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
```

- [ ] **Step 13: Strip the hero image's metadata** (it carries an embedded EXIF text profile)

```bash
python3 -c "from PIL import Image; im=Image.open('public/hero-image-temp.png'); im.load(); Image.frombytes(im.mode, im.size, im.tobytes()).save('public/hero-image-temp.png', optimize=True)"
python3 -c "from PIL import Image; im=Image.open('public/hero-image-temp.png'); print(im.size, list(im.info.keys()))"
```

Expected: `(690, 440)` and no `Raw profile type …` key.

- [ ] **Step 14: Verify and commit**

Run: `npm test && npm run typecheck && npm run lint && npm run build` — all pass (the page still renders the old layout with new fonts/colors; that's expected).
Commit (include `public/hero-image-temp.png`): `feat(biomech-lab): homepage foundation — tokens, fonts, site constants, pose summaries`

---

### Task 2: Static page sections and composition

**Files:**
- Create: `components/SiteNav.tsx`, `components/Hero.tsx`, `components/HeroVisual.tsx`, `components/OpenUploadButton.tsx`, `components/HowItWorks.tsx`, `components/PoseChecks.tsx`, `components/PrivacyAbout.tsx`, `components/SiteFooter.tsx`
- Modify (replace): `app/page.tsx`

**Interfaces:**
- Consumes (Task 1): `LINKS`, `HERO_IMAGE`, `SAMPLES`, `OPEN_UPLOAD_EVENT`, `poseSummaries`, style strings, theme colors/fonts. `PhotoLab` (existing client component) is rendered inside `#lab`.
- Section ids: `top` (hero), `lab`, `how`, `poses`, `privacy`.

- [ ] **Step 1: `components/OpenUploadButton.tsx`**

```tsx
"use client";

import { Upload } from "lucide-react";
import { OPEN_UPLOAD_EVENT } from "@/lib/events";
import { buttonSecondary } from "./ui/styles";

export function OpenUploadButton() {
  return (
    <button
      type="button"
      className={buttonSecondary}
      onClick={() => {
        window.dispatchEvent(new Event(OPEN_UPLOAD_EVENT));
        document.getElementById("lab")?.scrollIntoView({ behavior: "smooth" });
      }}
    >
      <Upload aria-hidden="true" className="size-4" />
      Upload a photo
    </button>
  );
}
```

- [ ] **Step 2: `components/HeroVisual.tsx`**

```tsx
import Image from "next/image";
import { HERO_IMAGE } from "@/lib/site";

/** Swappable hero artwork — change HERO_IMAGE in lib/site.ts. */
export function HeroVisual() {
  return (
    <div className="overflow-hidden rounded-3xl border border-line bg-white">
      <Image
        src={HERO_IMAGE.src}
        width={HERO_IMAGE.width}
        height={HERO_IMAGE.height}
        alt={HERO_IMAGE.alt}
        preload
        sizes="(min-width: 768px) 560px, 100vw"
        className="h-auto w-full"
      />
    </div>
  );
}
```

- [ ] **Step 3: `components/Hero.tsx`**

```tsx
import { Activity, ArrowDown, Lock, UserRound } from "lucide-react";
import { poseSummaries } from "@/lib/pose-summaries";
import { HeroVisual } from "./HeroVisual";
import { OpenUploadButton } from "./OpenUploadButton";
import { buttonPrimary, eyebrow } from "./ui/styles";

export function Hero() {
  const poses = poseSummaries();
  const checkCount = poses.reduce((n, p) => n + p.checks.length, 0);
  const chips = [
    { Icon: Lock, text: "Your photo stays on your device" },
    { Icon: UserRound, text: "No sign-up" },
    { Icon: Activity, text: `${poses.length} poses · ${checkCount} checks` },
  ];

  return (
    <section
      id="top"
      className="mx-auto grid max-w-6xl items-center gap-12 px-6 pb-20 pt-12 md:grid-cols-2 md:pt-20"
    >
      <div>
        <p className={eyebrow}>Movement · Kinesiology · AI</p>
        <h1 className="mt-4 font-display text-5xl leading-[1.05] tracking-tight md:text-6xl">
          Move better.
          <br />
          See why.
        </h1>
        <p className="mt-6 max-w-md text-lg text-ink-muted">
          Upload a yoga pose. Biomech Lab detects 33 body landmarks, measures your joint angles and
          scores your form, all in your browser.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <a href="#lab" className={buttonPrimary}>
            Try a sample
            <ArrowDown aria-hidden="true" className="size-4" />
          </a>
          <OpenUploadButton />
        </div>
        <ul className="mt-8 flex flex-wrap gap-2" aria-label="Highlights">
          {chips.map(({ Icon, text }) => (
            <li
              key={text}
              className="inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1.5 text-sm text-ink-muted"
            >
              <Icon aria-hidden="true" className="size-4 text-accent" />
              {text}
            </li>
          ))}
        </ul>
      </div>
      <HeroVisual />
    </section>
  );
}
```

- [ ] **Step 4: `components/SiteNav.tsx`**

```tsx
import { ArrowUpRight, PersonStanding } from "lucide-react";
import { LINKS } from "@/lib/site";
import { focusRing } from "./ui/styles";

const NAV = [
  { href: "#how", label: "How it works" },
  { href: "#poses", label: "Poses" },
  { href: "#privacy", label: "Privacy" },
];

export function SiteNav() {
  return (
    <header className="sticky top-0 z-10 border-b border-line bg-paper/90 backdrop-blur">
      <nav aria-label="Main" className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <a href="#top" className={`flex items-center gap-2 rounded-md font-display text-lg ${focusRing}`}>
          <PersonStanding aria-hidden="true" className="size-5 text-accent" />
          Biomech Lab
        </a>
        <ul className="flex items-center gap-6 text-sm text-ink-muted">
          {NAV.map((l) => (
            <li key={l.href} className="hidden sm:block">
              <a href={l.href} className={`rounded-md hover:text-ink ${focusRing}`}>
                {l.label}
              </a>
            </li>
          ))}
          <li>
            <a
              href={LINKS.github}
              target="_blank"
              rel="noreferrer"
              className={`inline-flex items-center gap-1 rounded-md font-medium text-ink hover:text-accent ${focusRing}`}
            >
              GitHub
              <ArrowUpRight aria-hidden="true" className="size-4" />
            </a>
          </li>
        </ul>
      </nav>
    </header>
  );
}
```

- [ ] **Step 5: `components/HowItWorks.tsx`**

```tsx
import { ClipboardCheck, Ruler, ScanLine } from "lucide-react";
import { card, eyebrow, iconTile } from "./ui/styles";

const STEPS = [
  {
    Icon: ScanLine,
    title: "Detect",
    text: "MediaPipe finds 33 body landmarks in your photo, right on your device.",
  },
  {
    Icon: Ruler,
    title: "Measure",
    text: "Joint angles, alignment and balance are measured in pixel space, so the photo's shape never skews them.",
  },
  {
    Icon: ClipboardCheck,
    title: "Score",
    text: "Each check earns full, partial or no credit. If we can't measure reliably, you get a tip instead of a number.",
  },
];

export function HowItWorks() {
  return (
    <section id="how" aria-labelledby="how-title" className="scroll-mt-20 border-t border-line">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <p className={eyebrow}>How it works</p>
        <h2 id="how-title" className="mt-3 font-display text-3xl md:text-4xl">
          From photo to feedback in three steps
        </h2>
        <ol className="mt-10 grid gap-5 md:grid-cols-3">
          {STEPS.map(({ Icon, title, text }, i) => (
            <li key={title} className={`${card} p-6`}>
              <span className={iconTile}>
                <Icon aria-hidden="true" className="size-5" />
              </span>
              <h3 className="mt-4 font-semibold">
                {i + 1} · {title}
              </h3>
              <p className="mt-2 text-sm text-ink-muted">{text}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
```

- [ ] **Step 6: `components/PoseChecks.tsx`**

```tsx
import Image from "next/image";
import { poseSummaries } from "@/lib/pose-summaries";
import { SAMPLES } from "@/lib/samples";
import { card, eyebrow } from "./ui/styles";

export function PoseChecks() {
  const poses = poseSummaries();
  return (
    <section id="poses" aria-labelledby="poses-title" className="scroll-mt-20 border-t border-line">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <p className={eyebrow}>The poses</p>
        <h2 id="poses-title" className="mt-3 font-display text-3xl md:text-4xl">
          What we check
        </h2>
        <p className="mt-3 max-w-2xl text-ink-muted">
          Every score comes from explicit, measurable checks. No black box: you see the angle we
          measured and the target.
        </p>
        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {poses.map((p) => {
            const sample = SAMPLES.find((s) => s.id === p.id);
            return (
              <article key={p.id} className={`${card} overflow-hidden`}>
                {sample && (
                  <Image
                    src={sample.src}
                    alt=""
                    width={640}
                    height={360}
                    sizes="(min-width: 768px) 360px, 100vw"
                    className="aspect-video w-full object-cover"
                  />
                )}
                <div className="p-6">
                  <h3 className="font-display text-xl">{p.label}</h3>
                  <p className="text-sm text-ink-subtle">{p.viewLabel}</p>
                  <ul className="mt-4 space-y-2 text-sm">
                    {p.checks.map((c) => (
                      <li key={c.id} className="flex justify-between gap-3 border-t border-line pt-2">
                        <span>{c.label}</span>
                        {c.target && <span className="tabular-nums text-ink-subtle">{c.target}</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 7: `components/PrivacyAbout.tsx`**

```tsx
import { ArrowUpRight, ShieldCheck, UserRound } from "lucide-react";
import { LINKS } from "@/lib/site";
import { buttonSecondary, card, iconTile } from "./ui/styles";

export function PrivacyAbout() {
  return (
    <section id="privacy" aria-label="Privacy and about" className="scroll-mt-20 border-t border-line">
      <div className="mx-auto grid max-w-6xl gap-5 px-6 py-20 md:grid-cols-2">
        <article className={`${card} p-8`}>
          <span className={iconTile}>
            <ShieldCheck aria-hidden="true" className="size-5" />
          </span>
          <h2 className="mt-4 font-display text-2xl">Private by design</h2>
          <p className="mt-3 text-ink-muted">
            Your photo never leaves your device: pose detection runs locally in your browser and
            nothing is uploaded.
          </p>
          <p className="mt-3 text-ink-muted">
            Google&apos;s MediaPipe library tries to send anonymous usage statistics. Our Content
            Security Policy blocks it.
          </p>
        </article>
        <article className={`${card} p-8`}>
          <span className={iconTile}>
            <UserRound aria-hidden="true" className="size-5" />
          </span>
          <h2 className="mt-4 font-display text-2xl">Built by Sergio Fruto</h2>
          <p className="mt-3 text-ink-muted">
            Product engineer and kinesiology student, combining biomechanics with applied AI. Built
            with Next.js, TypeScript and MediaPipe.
          </p>
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
    </section>
  );
}
```

- [ ] **Step 8: `components/SiteFooter.tsx`**

```tsx
export function SiteFooter() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-wrap justify-between gap-2 px-6 py-8 text-sm text-ink-subtle">
        <p>Educational feedback, not medical advice.</p>
        <p>Pose detection by MediaPipe · © 2026 Sergio Fruto</p>
      </div>
    </footer>
  );
}
```

- [ ] **Step 9: Replace `app/page.tsx`**

```tsx
import { Hero } from "@/components/Hero";
import { HowItWorks } from "@/components/HowItWorks";
import { PhotoLab } from "@/components/PhotoLab";
import { PoseChecks } from "@/components/PoseChecks";
import { PrivacyAbout } from "@/components/PrivacyAbout";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteNav } from "@/components/SiteNav";
import { eyebrow } from "@/components/ui/styles";

export default function Home() {
  return (
    <>
      <SiteNav />
      <main>
        <Hero />
        <section id="lab" aria-labelledby="lab-title" className="scroll-mt-20 border-t border-line bg-white/60">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <p className={eyebrow}>The lab</p>
            <h2 id="lab-title" className="mt-3 font-display text-3xl md:text-4xl">
              Try it
            </h2>
            <p className="mt-3 max-w-2xl text-ink-muted">
              Pick a sample or upload a full-body photo: Warrior II and Tree facing the camera,
              Downward Dog from the side.
            </p>
            <div className="mt-10">
              <PhotoLab />
            </div>
          </div>
        </section>
        <HowItWorks />
        <PoseChecks />
        <PrivacyAbout />
      </main>
      <SiteFooter />
    </>
  );
}
```

- [ ] **Step 10: Verify and commit**

Run: `npm test && npm run typecheck && npm run lint && npm run build`. Then `npm run dev` (use `PORT=3100` if 3000 is taken), `curl -s localhost:<port> | grep -c "What we check"` → ≥ 1, stop the server.
Commit: `feat(biomech-lab): homepage sections — nav, hero, how it works, poses, privacy, footer`

---

### Task 3: Restyle the lab (PhotoLab, AssessmentView, StageCanvas)

**Files:**
- Modify: `components/PhotoLab.tsx`, `components/AssessmentView.tsx`, `components/StageCanvas.tsx`

**Interfaces:**
- Consumes: `OPEN_UPLOAD_EVENT`, `SAMPLES`, `viewLabel`, `POSES`, style strings, theme colors.
- Must preserve (behavior already reviewed — do not change): engine caching and `.catch` reset in `getEngine`, the `requestIdRef` stale-result guard on both success and error paths, object-URL lifecycle in `onFile` and the unmount cleanup, `e.target.value = ""`, every `Assessment` branch including `result.score === null` and the `never` exhaustiveness guard, `role="status"` on result regions, `role="alert"` on errors.

- [ ] **Step 1: PhotoLab — listen for the hero's upload button.** Add `import { OPEN_UPLOAD_EVENT } from "@/lib/events";` and, after the existing cleanup `useEffect`, add:

```tsx
  useEffect(() => {
    const openUpload = () => setTab("upload");
    window.addEventListener(OPEN_UPLOAD_EVENT, openUpload);
    return () => window.removeEventListener(OPEN_UPLOAD_EVENT, openUpload);
  }, []);
```

- [ ] **Step 2: PhotoLab — replace the `tabClass` helper and the returned JSX** with the following (imports to add: `ImageUp, LoaderCircle, RotateCcw, TriangleAlert` from `lucide-react`; `POSES` from `@/lib/poses`; `viewLabel` from `@/lib/pose-summaries`; `buttonSecondary, card, focusRing` from `./ui/styles`):

```tsx
  const tabClass = (active: boolean) =>
    `rounded-full px-4 py-2 text-sm font-medium transition-colors ${focusRing} ${
      active ? "bg-ink text-paper" : "text-ink-muted hover:text-ink"
    }`;

  return (
    <div>
      <div role="group" aria-label="Choose input" className="inline-flex rounded-full border border-line bg-white p-1">
        <button type="button" aria-pressed={tab === "samples"} className={tabClass(tab === "samples")} onClick={() => setTab("samples")}>
          Samples
        </button>
        <button type="button" aria-pressed={tab === "upload"} className={tabClass(tab === "upload")} onClick={() => setTab("upload")}>
          Upload a photo
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
                className={`${card} overflow-hidden text-left transition-colors hover:border-ink ${focusRing}`}
              >
                <Image
                  src={s.src}
                  alt={`${s.label} sample photo`}
                  width={640}
                  height={360}
                  sizes="(min-width: 640px) 360px, 100vw"
                  className="aspect-video w-full object-cover"
                />
                <span className="flex items-center justify-between gap-2 px-4 py-3">
                  <span className="font-medium">{s.label}</span>
                  <span className="text-sm text-ink-subtle">{viewLabel(POSES[s.id].view)}</span>
                </span>
              </button>
            ))}
          </div>
        ) : (
          <label className="flex cursor-pointer flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-line-strong bg-white px-6 py-12 text-center transition-colors hover:border-ink focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-accent">
            <ImageUp aria-hidden="true" className="size-8 text-accent" />
            <span className="font-medium">Choose a full-body photo</span>
            <span className="max-w-md text-sm text-ink-muted">
              Warrior II and Tree facing the camera, Downward Dog from the side. Your photo stays on
              your device.
            </span>
            <input type="file" accept="image/*" onChange={onFile} className="sr-only" />
          </label>
        )}
      </div>

      {state.status === "working" && (
        <p role="status" className="mt-8 flex items-center gap-2 text-ink-muted">
          <LoaderCircle aria-hidden="true" className="size-5 animate-spin text-accent" />
          Analyzing your pose… The first run downloads the pose model.
        </p>
      )}
      {state.status === "error" && (
        <div role="alert" className={`mt-8 flex flex-wrap items-center gap-4 ${card} p-5`}>
          <TriangleAlert aria-hidden="true" className="size-5 text-fail" />
          <p className="flex-1">{state.message}</p>
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
          <AssessmentView assessment={state.assessment} />
        </div>
      )}
    </div>
  );
```

- [ ] **Step 3: StageCanvas — match the palette.** Set `MAX_WIDTH = 720`. In the effect: bones `ctx.strokeStyle = "#ea580c"` and `ctx.lineWidth = 4`; joints drawn as white fill plus accent stroke:

```tsx
    ctx.fillStyle = "#ffffff";
    ctx.strokeStyle = "#ea580c";
    ctx.lineWidth = 2;
    for (const j of ALL_JOINTS) {
      if (!body.usable(j)) continue;
      const p = body.point(j);
      ctx.beginPath();
      ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
```

Canvas `className="w-full rounded-2xl border border-line bg-white"` (keep `role="img"` and the aria-label).

- [ ] **Step 4: Replace `components/AssessmentView.tsx`**

```tsx
import {
  CircleAlert,
  CircleCheck,
  CircleMinus,
  CircleX,
  Info,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import type { Assessment } from "@/lib/assess";
import { POSES } from "@/lib/poses";
import type { CheckResult, CheckStatus } from "@/lib/score";

const STATUS: Record<CheckStatus, { Icon: LucideIcon; text: string; className: string }> = {
  pass: { Icon: CircleCheck, text: "Pass", className: "text-pass" },
  partial: { Icon: CircleAlert, text: "Partial", className: "text-partial" },
  fail: { Icon: CircleX, text: "Needs work", className: "text-fail" },
  not_measured: { Icon: CircleMinus, text: "Not measured", className: "text-ink-subtle" },
};

function formatValue(c: CheckResult): string {
  if (c.value === null) return "—";
  return c.unit === "deg" ? `${Math.round(c.value)}°` : c.value.toFixed(2);
}

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div role="status" className="flex gap-3 rounded-2xl border border-line bg-white p-5">
      <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-accent" />
      <p>{children}</p>
    </div>
  );
}

export function AssessmentView({ assessment }: { assessment: Assessment }) {
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
        <section role="status" className="rounded-2xl border border-partial/30 bg-white p-6">
          <div className="flex items-center gap-2">
            <TriangleAlert aria-hidden="true" className="size-5 text-partial" />
            <h3 className="font-semibold">
              {POSES[assessment.pose].label} detected — we can&apos;t score it yet
            </h3>
          </div>
          <ul className="mt-3 list-disc space-y-1 pl-6 text-ink-muted">
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
        <section role="status" className="rounded-2xl border border-line bg-white p-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h3 className="text-sm font-medium text-ink-subtle">{POSES[assessment.pose].label}</h3>
              <p className="font-display text-6xl leading-none">
                {result.score}
                <span className="ml-1 font-sans text-base text-ink-subtle">/ 100</span>
              </p>
            </div>
            <p className="text-sm text-ink-subtle">
              Measurement confidence {Math.round(readiness.coverage * 100)}%
            </p>
          </div>
          <ul className="mt-6 divide-y divide-line">
            {result.checks.map((c) => {
              const s = STATUS[c.status];
              return (
                <li key={c.id} className="flex items-start gap-3 py-3">
                  <s.Icon aria-hidden="true" className={`mt-0.5 size-5 shrink-0 ${s.className}`} />
                  <div className="flex-1">
                    <p className="font-medium">{c.label}</p>
                    {c.status !== "pass" && c.status !== "not_measured" && (
                      <p className="text-sm text-ink-muted">{c.cue}</p>
                    )}
                  </div>
                  <div className="text-right text-sm">
                    <p className="tabular-nums">
                      {formatValue(c)} <span className="text-ink-subtle">/ {c.targetText}</span>
                    </p>
                    <p className={s.className}>{s.text}</p>
                  </div>
                </li>
              );
            })}
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

- [ ] **Step 5: Verify and commit**

Run: `npm test && npm run typecheck && npm run lint && npm run build`.
Commit: `feat(biomech-lab): restyle the lab — tabs, sample cards, dropzone, result card`

---

### Task 4: Verification (controller) and release

- [ ] Browser check on `npm run build && PORT=3100 npm run start`: desktop (1440 px) and mobile (390 px) screenshots of every section; nav anchors scroll correctly under the sticky header; "Upload a photo" in the hero opens the upload tab; the three samples still score **50 / 55 / 46** with per-check rows; keyboard-only tab order with a visible focus ring; console clean; external requests still only jsDelivr + Google Storage (fonts self-hosted).
- [ ] Push `feat/homepage` for a Vercel preview; on approval merge to `main` and push (production deploy), then re-run the production checks.
