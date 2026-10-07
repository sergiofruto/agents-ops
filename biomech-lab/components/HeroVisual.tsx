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
