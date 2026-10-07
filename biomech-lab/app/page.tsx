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
