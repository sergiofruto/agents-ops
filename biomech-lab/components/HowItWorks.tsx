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
