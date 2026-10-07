import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { ITERATIONS } from "@/data/iterations";
import { countWord } from "@/lib/format";
import { sampleReports } from "@/lib/sample-reports";
import { buttonSecondary, container, label, panel, sectionShell, sectionTitle } from "./ui/styles";

export function ReportsTeaser() {
  const reports = sampleReports();
  const latest = ITERATIONS[ITERATIONS.length - 1];
  return (
    <section aria-labelledby="reports-teaser-title" className={sectionShell}>
      <div className={`${container} py-16`}>
        <div className={`${panel} flex flex-wrap items-center justify-between gap-6 p-6`}>
          <div>
            <p className={label}>02 · Sample reports</p>
            <h2 id="reports-teaser-title" className={sectionTitle}>
              {countWord(reports.length)} real photos, fully measured
            </h2>
            <p className="mt-2 max-w-xl text-fg-muted">
              Skeleton overlays, angle gauges and score breakdowns from iteration {latest.id} of
              Sergio&apos;s practice shots.
            </p>
          </div>
          <dl className="flex gap-6">
            {reports.map((r) => (
              <div key={r.id}>
                <dt className="font-mono text-[11px] text-fg-subtle">{r.label}</dt>
                <dd className="font-mono text-3xl font-semibold text-fg-strong">{r.score}</dd>
              </div>
            ))}
          </dl>
          <Link href="/reports" className={buttonSecondary}>
            Open reports
            <ArrowRight aria-hidden="true" className="size-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}
