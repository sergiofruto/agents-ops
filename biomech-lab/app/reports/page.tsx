import type { Metadata } from "next";
import Link from "next/link";
import { ReportCard } from "@/components/ReportCard";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteNav } from "@/components/SiteNav";
import { container, focusRing, label, panel } from "@/components/ui/styles";
import { IterationChart } from "@/components/viz/IterationChart";
import { ITERATIONS } from "@/data/iterations";
import { countWord } from "@/lib/format";
import { iterationSeries, sampleReports } from "@/lib/sample-reports";

export const metadata: Metadata = {
  title: "Sample reports · Biomech Lab",
  description:
    "Full pose analyses of three real photos: skeleton overlays, joint-angle gauges and score breakdowns, computed in the browser pipeline.",
};

export default function ReportsPage() {
  const reports = sampleReports();
  const series = iterationSeries();
  const latest = ITERATIONS[ITERATIONS.length - 1];
  return (
    <>
      <SiteNav />
      <main className={`${container} py-14`}>
        <p className={label}>Sample reports · iteration {latest.id}</p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight text-fg-strong md:text-5xl">
          {countWord(reports.length)} real photos, fully measured
        </h1>
        <p className="mt-4 max-w-2xl text-fg-muted">
          {latest.date} · {latest.device}. {latest.note} Scores come from the same code that runs in
          the analyzer.
        </p>
        <div className="mt-12 space-y-10">
          {reports.map((r) => (
            <ReportCard key={r.id} report={r} />
          ))}
        </div>
        <section aria-labelledby="iterations-title" className={`${panel} mt-12 p-6`}>
          <p className={label}>Progress</p>
          <h2 id="iterations-title" className="mt-2 text-xl font-bold text-fg-strong">
            Score by iteration
          </h2>
          <div className="mt-6">
            <IterationChart points={series} />
          </div>
        </section>
        <p className="mt-10 font-mono text-sm text-fg-muted">
          method:{" "}
          <Link href="/#pipeline" className={`rounded text-accent hover:underline ${focusRing}`}>
            pipeline
          </Link>{" "}
          ·{" "}
          <Link href="/#checks" className={`rounded text-accent hover:underline ${focusRing}`}>
            check spec
          </Link>
        </p>
      </main>
      <SiteFooter />
    </>
  );
}
