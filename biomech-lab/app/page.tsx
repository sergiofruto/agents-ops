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
