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
