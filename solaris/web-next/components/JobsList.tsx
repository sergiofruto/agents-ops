import type { Job, PipelineCounts } from "@/lib/types";

const PIPE_ORDER: { key: keyof PipelineCounts; label: string }[] = [
  { key: "bookmarked", label: "Bookmarked" },
  { key: "applied",    label: "Applied" },
  { key: "phone",      label: "Phone" },
  { key: "technical",  label: "Technical" },
  { key: "final",      label: "Final" },
  { key: "offer",      label: "Offer" },
  { key: "rejected",   label: "Rejected" },
];

function pillClass(key: keyof PipelineCounts): string {
  if (key === "offer")    return "bg-[#064e3b] border-[#065f46] text-[#34d399]";
  if (key === "rejected") return "bg-[#450a0a] border-[#7f1d1d] text-[#f87171]";
  return "bg-[#0a1628] border-[#1e3a5f] text-[#f1f5f9]";
}

function fmtSalary(min: number | null, max: number | null): string {
  if (min == null && max == null) return "—";
  if (min != null && max != null) return `$${min}K–$${max}K`;
  return `$${(min ?? max)!}K`;
}

export function JobsList({ jobs, pipeline }: { jobs: Job[]; pipeline: PipelineCounts }) {
  return (
    <div className="bg-[#0f1a2e] border border-[#1e3a5f] rounded-lg p-4 flex flex-col gap-4">
      <span className="text-[11.5px] font-medium text-[#60a5fa] tracking-[0.06em] uppercase">
        Job Pipeline
      </span>

      {/* Stage pills */}
      <div className="grid grid-cols-7 gap-2">
        {PIPE_ORDER.map(({ key, label }) => (
          <div
            key={key}
            className={`border rounded-md py-2 px-1 text-center ${pillClass(key)}`}
          >
            <div className="text-[16px] font-bold">{pipeline[key]}</div>
            <div className="text-[10.5px] text-[#475569] mt-0.5 uppercase">{label}</div>
          </div>
        ))}
      </div>

      {/* Jobs table */}
      <div className="overflow-x-auto rounded-md border border-[#1e3a5f]">
        <table className="w-full text-[11.5px]">
          <thead className="bg-[#0a1628] text-left">
            <tr>
              {["Company", "Role", "Status", "Salary", "Location", "Updated"].map((h) => (
                <th key={h} className="px-3 py-2 font-medium text-[#475569]">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e3a5f]">
            {jobs.slice(0, 50).map((j) => (
              <tr key={j.id} className="text-[#94a3b8] hover:bg-[#0a1628] transition-colors">
                <td className="px-3 py-2 font-medium text-[#f1f5f9]">{j.company}</td>
                <td className="px-3 py-2">{j.role}</td>
                <td className="px-3 py-2">
                  <span className="rounded bg-[#0a1628] border border-[#1e3a5f] px-1.5 py-0.5 text-[10.5px] uppercase text-[#60a5fa]">
                    {j.status}
                  </span>
                </td>
                <td className="px-3 py-2">{fmtSalary(j.salary_min, j.salary_max)}</td>
                <td className="px-3 py-2 text-[#475569]">{j.location || "—"}</td>
                <td className="px-3 py-2 text-[#475569]">{(j.updated_at ?? "").slice(0, 10)}</td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-4 text-center text-[#475569] italic">
                  No jobs yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {jobs.length > 50 && (
        <p className="text-[11.5px] text-[#475569]">Showing 50 of {jobs.length}.</p>
      )}
    </div>
  );
}
