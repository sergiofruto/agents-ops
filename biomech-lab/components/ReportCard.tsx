import { viewLabel } from "@/lib/pose-summaries";
import type { SampleReport } from "@/lib/sample-reports";
import { panel } from "./ui/styles";
import { CheckRow, formatValue, ScoreBasis } from "./viz/CheckRow";
import { ScoreHeader } from "./viz/ScoreHeader";
import { SkeletonOverlay } from "./viz/SkeletonOverlay";
import { StatusBadge } from "./viz/StatusBadge";

export function ReportCard({ report }: { report: SampleReport }) {
  const flagged = report.checks.filter((c) => c.status === "fail" || c.status === "partial");
  return (
    <article aria-labelledby={`report-${report.id}`} className={`${panel} grid gap-6 p-5 lg:grid-cols-[1.25fr_1fr]`}>
      <div>
        <div className="mb-2 flex justify-between font-mono text-[11px] text-fg-subtle">
          <span>
            <span aria-hidden="true" className="text-accent">
              ●
            </span>{" "}
            {report.id}.jpg
          </span>
          <span>
            {report.width}×{report.height} · {viewLabel(report.view).toLowerCase()}
          </span>
        </div>
        <SkeletonOverlay
          src={report.imageSrc}
          alt={`${report.label} sample photo with the detected skeleton`}
          width={report.width}
          height={report.height}
          landmarks={report.landmarks}
          sizes="(min-width: 1024px) 640px, 100vw"
        />
        {flagged.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2" aria-label="Checks that need work">
            {flagged.map((c) => (
              <li key={c.id} className="flex items-center gap-2 rounded border border-line-strong bg-bg px-2 py-1">
                <StatusBadge status={c.status} />
                <span className="font-mono text-xs text-fg-strong">
                  {c.id} {formatValue(c)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <h2 id={`report-${report.id}`} className="sr-only">
          {report.label} report
        </h2>
        <ScoreHeader label={report.label} score={report.score} coverage={report.coverage} />
        <ul className="mt-4 divide-y divide-line">
          {report.checks.map((c) => (
            <CheckRow key={c.id} check={c} />
          ))}
        </ul>
        <ScoreBasis checks={report.checks} />
      </div>
    </article>
  );
}
