"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Job, Interview, JobStatus, PipelineCounts } from "@/lib/types";

interface JobTrackerProps {
  initialJobs: Job[];
  pipeline: PipelineCounts;
}

const STATUS_COLORS: Record<string, { color: string; border: string }> = {
  bookmarked:  { color: "#666666", border: "#333333" },
  interested:  { color: "#D4A843", border: "#D4A843" },
  applied:     { color: "#5B9BF6", border: "#5B9BF6" },
  phone:       { color: "#D4A843", border: "#D4A843" },
  technical:   { color: "#D4A843", border: "#D4A843" },
  final:       { color: "#E8E8E8", border: "#666666" },
  offer:       { color: "#4A9E5C", border: "#4A9E5C" },
  rejected:    { color: "#D71921", border: "#D71921" },
};
const FALLBACK_COLOR = { color: "#666666", border: "#333333" };

const ALL_STATUSES: JobStatus[] = [
  "bookmarked", "applied", "phone", "technical", "final", "offer", "rejected",
];

function StatusPill({ status }: { status: JobStatus }) {
  const { color, border } = STATUS_COLORS[status] ?? FALLBACK_COLOR;
  return (
    <span style={{
      fontFamily: "var(--font-mono), monospace",
      fontSize: "10px",
      letterSpacing: "0.06em",
      color,
      border: `1px solid ${border}`,
      borderRadius: "999px",
      padding: "2px 8px",
      display: "inline-block",
    }}>
      {status.toUpperCase()}
    </span>
  );
}

interface JobFormData {
  company: string;
  role: string;
  url: string;
  location: string;
  salary_min: string;
  salary_max: string;
  status: JobStatus;
  notes: string;
}

const emptyForm: JobFormData = {
  company: "",
  role: "",
  url: "",
  location: "Remote",
  salary_min: "",
  salary_max: "",
  status: "bookmarked",
  notes: "",
};

export default function JobTracker({ initialJobs, pipeline }: JobTrackerProps) {
  const [jobs, setJobs] = useState<Job[]>(initialJobs);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editJob, setEditJob] = useState<Job | null>(null);
  const [interviewJob, setInterviewJob] = useState<Job | null>(null);
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [form, setForm] = useState<JobFormData>(emptyForm);
  const [newStage, setNewStage] = useState("");
  const [newNotes, setNewNotes] = useState("");

  const refresh = useCallback(async () => {
    const res = await fetch("/api/jobs");
    if (res.ok) setJobs(await res.json());
  }, []);

  async function addJob(e: React.FormEvent) {
    e.preventDefault();
    const body: Record<string, string | number | undefined> = {
      company: form.company,
      role: form.role,
      url: form.url || undefined,
      location: form.location,
      status: form.status,
      notes: form.notes || undefined,
      salary_min: form.salary_min ? Number(form.salary_min) : undefined,
      salary_max: form.salary_max ? Number(form.salary_max) : undefined,
    };
    await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setForm(emptyForm);
    setShowAddForm(false);
    await refresh();
  }

  async function updateJob(e: React.FormEvent) {
    e.preventDefault();
    if (!editJob) return;
    await fetch(`/api/jobs/${editJob.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company: form.company,
        role: form.role,
        url: form.url || null,
        location: form.location,
        status: form.status,
        notes: form.notes || null,
        salary_min: form.salary_min ? Number(form.salary_min) : null,
        salary_max: form.salary_max ? Number(form.salary_max) : null,
      }),
    });
    setEditJob(null);
    await refresh();
  }

  async function deleteJob(id: number) {
    if (!confirm("Delete this job?")) return;
    await fetch(`/api/jobs/${id}`, { method: "DELETE" });
    await refresh();
  }

  async function openInterviews(job: Job) {
    setInterviewJob(job);
    const res = await fetch(`/api/jobs/${job.id}/interviews`);
    if (res.ok) setInterviews(await res.json());
  }

  async function addInterview(e: React.FormEvent) {
    e.preventDefault();
    if (!interviewJob || !newStage) return;
    await fetch(`/api/jobs/${interviewJob.id}/interviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stage: newStage, notes: newNotes || undefined }),
    });
    setNewStage("");
    setNewNotes("");
    const res = await fetch(`/api/jobs/${interviewJob.id}/interviews`);
    if (res.ok) setInterviews(await res.json());
    await refresh();
  }

  function startEdit(job: Job) {
    setForm({
      company: job.company,
      role: job.role,
      url: job.url ?? "",
      location: job.location,
      salary_min: job.salary_min?.toString() ?? "",
      salary_max: job.salary_max?.toString() ?? "",
      status: job.status,
      notes: job.notes ?? "",
    });
    setEditJob(job);
  }

  // Compute live pipeline counts from current jobs
  const livePipeline: PipelineCounts = { ...pipeline };
  ALL_STATUSES.forEach((s) => {
    livePipeline[s] = jobs.filter((j) => j.status === s).length;
  });

  return (
    <div className="space-y-4">
      {/* Pipeline counts */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "16px" }}>
        {ALL_STATUSES.map((s) => (
          <div key={s} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <StatusPill status={s} />
            <span style={{ fontFamily: "var(--font-mono), monospace", fontSize: "12px", color: "#E8E8E8" }}>
              {livePipeline[s]}
            </span>
          </div>
        ))}
      </div>

      {/* Add job toggle */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "12px" }}>
        <button
          onClick={() => setShowAddForm((v) => !v)}
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "11px",
            letterSpacing: "0.06em",
            color: "#E8E8E8",
            border: "1px solid #333333",
            background: "transparent",
            padding: "6px 16px",
            borderRadius: "999px",
            cursor: "pointer",
            transition: "border-color 150ms",
          }}
        >
          {showAddForm ? "CANCEL" : "+ ADD JOB"}
        </button>
      </div>

      {/* Add job form */}
      {showAddForm && (
        <form onSubmit={addJob} className="space-y-3 rounded-lg bg-white/5 p-4">
          <div className="grid grid-cols-2 gap-3">
            <input
              required
              placeholder="Company"
              value={form.company}
              onChange={(e) => setForm({ ...form, company: e.target.value })}
              className="col-span-1 rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50"
            />
            <input
              required
              placeholder="Role"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="col-span-1 rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50"
            />
            <input
              placeholder="URL"
              value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })}
              className="col-span-2 rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50"
            />
            <input
              placeholder="Location"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
              className="rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50"
            />
            <select
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value as JobStatus })}
              className="rounded-md bg-zinc-800 border border-white/10 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-violet-500/50"
            >
              {ALL_STATUSES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <input
              type="number"
              placeholder="Salary min"
              value={form.salary_min}
              onChange={(e) => setForm({ ...form, salary_min: e.target.value })}
              className="rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50"
            />
            <input
              type="number"
              placeholder="Salary max"
              value={form.salary_max}
              onChange={(e) => setForm({ ...form, salary_max: e.target.value })}
              className="rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50"
            />
            <textarea
              placeholder="Notes"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={2}
              className="col-span-2 rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50 resize-none"
            />
          </div>
          <div className="flex justify-end">
            <Button type="submit" size="sm" className="bg-violet-600 hover:bg-violet-700 text-white">
              Save Job
            </Button>
          </div>
        </form>
      )}

      {/* Jobs table */}
      <div style={{ overflowX: "auto", border: "1px solid #222222", borderRadius: "8px" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #333333" }}>
              {["Company", "Role", "Location", "Status", "Salary", "Interviews", ""].map((h) => (
                <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontFamily: "var(--font-mono), monospace", fontSize: "10px", letterSpacing: "0.08em", color: "#666666", fontWeight: 400 }}>
                  {h.toUpperCase()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: "24px 16px", textAlign: "center", fontFamily: "var(--font-mono), monospace", fontSize: "12px", color: "#666666" }}>
                  [NO JOBS TRACKED]
                </td>
              </tr>
            ) : (
              jobs.map((job) => (
                <tr key={job.id} style={{ borderBottom: "1px solid #222222" }} className="nd-row">
                  <td style={{ padding: "10px 16px", fontFamily: "var(--font-sans), system-ui", fontSize: "13px", fontWeight: 500, color: "#E8E8E8" }}>
                    {job.url ? (
                      <a href={job.url} target="_blank" rel="noreferrer" style={{ color: "#5B9BF6", textDecoration: "none", transition: "color 150ms" }}
                        className="hover:text-white">
                        {job.company}
                      </a>
                    ) : job.company}
                  </td>
                  <td style={{ padding: "10px 16px", fontFamily: "var(--font-sans), system-ui", fontSize: "13px", color: "#999999" }}>{job.role}</td>
                  <td style={{ padding: "10px 16px", fontFamily: "var(--font-mono), monospace", fontSize: "11px", color: "#666666" }}>{job.location}</td>
                  <td style={{ padding: "10px 16px" }}>
                    <StatusPill status={job.status} />
                  </td>
                  <td style={{ padding: "10px 16px", fontFamily: "var(--font-mono), monospace", fontSize: "12px", color: "#666666" }}>
                    {job.salary_min || job.salary_max ? `$${job.salary_min ?? "?"} – $${job.salary_max ?? "?"}` : "—"}
                  </td>
                  <td style={{ padding: "10px 16px", textAlign: "center" }}>
                    <button onClick={() => openInterviews(job)}
                      style={{ fontFamily: "var(--font-mono), monospace", fontSize: "11px", color: "#666666", background: "none", border: "none", cursor: "pointer", letterSpacing: "0.04em" }}
                      className="hover:text-white">
                      {job.interview_count > 0 ? `${job.interview_count}` : "+"}
                    </button>
                  </td>
                  <td style={{ padding: "10px 16px", textAlign: "right" }}>
                    <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
                      <button onClick={() => startEdit(job)}
                        style={{ fontFamily: "var(--font-mono), monospace", fontSize: "11px", color: "#666666", background: "none", border: "none", cursor: "pointer", letterSpacing: "0.04em" }}
                        className="hover:text-white">EDIT</button>
                      <button onClick={() => deleteJob(job.id)}
                        style={{ fontFamily: "var(--font-mono), monospace", fontSize: "11px", color: "#333333", background: "none", border: "none", cursor: "pointer", letterSpacing: "0.04em" }}
                        className="hover:text-red-500">DEL</button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Edit modal */}
      <Dialog open={!!editJob} onOpenChange={(open) => !open && setEditJob(null)}>
        <DialogContent className="bg-zinc-900 border-white/10 text-zinc-100">
          <DialogHeader>
            <DialogTitle>Edit Job</DialogTitle>
          </DialogHeader>
          <form onSubmit={updateJob} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <input
                required
                placeholder="Company"
                value={form.company}
                onChange={(e) => setForm({ ...form, company: e.target.value })}
                className="col-span-1 rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50"
              />
              <input
                required
                placeholder="Role"
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                className="col-span-1 rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50"
              />
              <input
                placeholder="URL"
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
                className="col-span-2 rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50"
              />
              <input
                placeholder="Location"
                value={form.location}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
                className="rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50"
              />
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value as JobStatus })}
                className="rounded-md bg-zinc-800 border border-white/10 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-violet-500/50"
              >
                {ALL_STATUSES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <textarea
                placeholder="Notes"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                rows={2}
                className="col-span-2 rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50 resize-none"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" onClick={() => setEditJob(null)}>
                Cancel
              </Button>
              <Button type="submit" className="bg-violet-600 hover:bg-violet-700 text-white">
                Save
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Interviews modal */}
      <Dialog open={!!interviewJob} onOpenChange={(open) => !open && setInterviewJob(null)}>
        <DialogContent className="bg-zinc-900 border-white/10 text-zinc-100 max-w-lg">
          <DialogHeader>
            <DialogTitle>
              Interviews — {interviewJob?.company} ({interviewJob?.role})
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            {interviews.length === 0 ? (
              <p className="text-sm text-zinc-500 italic">No interviews logged yet.</p>
            ) : (
              <div className="space-y-2">
                {interviews.map((iv) => (
                  <div
                    key={iv.id}
                    className="flex items-start gap-3 rounded-md bg-white/5 px-3 py-2"
                  >
                    <div className="flex-1">
                      <p className="text-sm font-medium text-zinc-200">{iv.stage}</p>
                      {iv.scheduled_at && (
                        <p className="text-xs text-zinc-400">{iv.scheduled_at}</p>
                      )}
                      {iv.notes && (
                        <p className="text-xs text-zinc-400 mt-0.5">{iv.notes}</p>
                      )}
                    </div>
                    <span
                      className={`text-xs font-medium ${
                        iv.outcome === "passed"
                          ? "text-emerald-400"
                          : iv.outcome === "failed"
                          ? "text-red-400"
                          : "text-zinc-400"
                      }`}
                    >
                      {iv.outcome}
                    </span>
                  </div>
                ))}
              </div>
            )}
            <form onSubmit={addInterview} className="space-y-2 border-t border-white/10 pt-3">
              <input
                required
                placeholder="Stage (e.g. Phone Screen)"
                value={newStage}
                onChange={(e) => setNewStage(e.target.value)}
                className="w-full rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50"
              />
              <textarea
                placeholder="Notes"
                value={newNotes}
                onChange={(e) => setNewNotes(e.target.value)}
                rows={2}
                className="w-full rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-violet-500/50 resize-none"
              />
              <div className="flex justify-end">
                <Button type="submit" size="sm" className="bg-violet-600 hover:bg-violet-700 text-white">
                  Log Interview
                </Button>
              </div>
            </form>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
