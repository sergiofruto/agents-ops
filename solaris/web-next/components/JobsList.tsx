import type { Job, PipelineCounts } from "@/lib/types";

const PIPE_ORDER: (keyof PipelineCounts)[] = [
  "bookmarked", "applied", "phone", "technical", "final", "offer", "rejected",
];

function fmtSalary(min: number | null, max: number | null): string {
  if (min == null && max == null) return "—";
  if (min != null && max != null) return `$${min}K–$${max}K`;
  return `$${(min ?? max)!}K`;
}

export function JobsList({ jobs, pipeline }: { jobs: Job[]; pipeline: PipelineCounts }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {PIPE_ORDER.map((k) => (
          <div key={k} className="rounded-md bg-white/5 px-2.5 py-1.5 text-xs">
            <span className="uppercase tracking-wide text-zinc-500">{k}</span>{" "}
            <span className="font-semibold text-zinc-100">{pipeline[k]}</span>
          </div>
        ))}
      </div>

      <div className="overflow-x-auto rounded-md border border-white/10">
        <table className="w-full text-xs">
          <thead className="bg-white/5 text-left text-zinc-400">
            <tr>
              <th className="px-3 py-2 font-medium">Company</th>
              <th className="px-3 py-2 font-medium">Role</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Salary</th>
              <th className="px-3 py-2 font-medium">Location</th>
              <th className="px-3 py-2 font-medium">Updated</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {jobs.slice(0, 50).map((j) => (
              <tr key={j.id} className="text-zinc-200">
                <td className="px-3 py-2 font-medium">{j.company}</td>
                <td className="px-3 py-2 text-zinc-300">{j.role}</td>
                <td className="px-3 py-2"><span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] uppercase">{j.status}</span></td>
                <td className="px-3 py-2 text-zinc-300">{fmtSalary(j.salary_min, j.salary_max)}</td>
                <td className="px-3 py-2 text-zinc-400">{j.location || "—"}</td>
                <td className="px-3 py-2 text-zinc-500">{(j.updated_at ?? "").slice(0, 10)}</td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr><td colSpan={6} className="px-3 py-4 text-center text-zinc-500 italic">No jobs.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {jobs.length > 50 && (
        <p className="text-xs text-zinc-500">Showing 50 of {jobs.length}.</p>
      )}
    </div>
  );
}
