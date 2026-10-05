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
