import type { Metadata } from "next";
import { PostureCheck } from "@/components/posture/PostureCheck";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteNav } from "@/components/SiteNav";
import { container, label } from "@/components/ui/styles";

export const metadata: Metadata = {
  title: "Posture check · Biomech Lab",
  description:
    "A guided standing posture screening from front, side and back photos: head, shoulder, trunk and hip alignment with exercises, computed in your browser.",
};

export default function PosturePage() {
  return (
    <>
      <SiteNav />
      <main className={`${container} py-14`}>
        <p className={label}>Posture check</p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight text-fg-strong md:text-5xl">
          How do you stand?
        </h1>
        <p className="mt-4 max-w-2xl text-fg-muted">
          Three photos (front, side and back) and your height. We check how your head, shoulders,
          trunk and hips line up and suggest exercises. Everything runs on your device; nothing is
          uploaded.
        </p>
        <div className="mt-10">
          <PostureCheck />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
