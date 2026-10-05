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
