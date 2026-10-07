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
