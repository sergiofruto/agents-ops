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
