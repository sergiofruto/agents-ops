import type { CoordinatorAgent } from "@/lib/types";

function statusColor(status: CoordinatorAgent["last_status"]) {
  if (status === "ok")      return "bg-emerald-500";
  if (status === "error")   return "bg-red-500";
  if (status === "timeout") return "bg-amber-500";
  return "bg-zinc-600";
}

function statusLabel(status: CoordinatorAgent["last_status"]) {
  if (status === "ok")      return "OK";
  if (status === "error")   return "ERROR";
  if (status === "timeout") return "TIMEOUT";
  return "NEVER";
}

function TaskBar({ tasks }: { tasks: CoordinatorAgent["tasks"] }) {
  const total = tasks.active + tasks.done + tasks.blocked + tasks.skipped;
  if (total === 0) return null;

  return (
    <div className="space-y-1">
      <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-white/10">
        <div
          className="bg-emerald-500"
          style={{ width: `${(tasks.done / total) * 100}%` }}
        />
        <div
          className="bg-violet-500"
          style={{ width: `${(tasks.active / total) * 100}%` }}
        />
        <div
          className="bg-red-500"
          style={{ width: `${(tasks.blocked / total) * 100}%` }}
        />
      </div>
      <div className="flex gap-3 text-[10px] text-zinc-500">
        <span><span className="text-emerald-400">{tasks.done}</span> done</span>
        <span><span className="text-violet-400">{tasks.active}</span> active</span>
        {tasks.blocked > 0 && (
          <span><span className="text-red-400">{tasks.blocked}</span> blocked</span>
        )}
      </div>
    </div>
  );
}

function OutputChips({ output }: { output: Record<string, unknown> }) {
  const entries = Object.entries(output).filter(([k]) => !k.startsWith("__"));
  if (entries.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5">
      {entries.map(([key, val]) => (
        <span
          key={key}
          className="rounded bg-white/5 px-2 py-0.5 text-[10px] text-zinc-400"
        >
          {key}: <span className="text-zinc-200">{String(val)}</span>
        </span>
      ))}
    </div>
  );
}

function AgentRow({ agent }: { agent: CoordinatorAgent }) {
  const disabled = !agent.enabled;

  return (
    <div className={`rounded-lg border border-white/5 bg-white/[0.03] p-3 space-y-2 ${disabled ? "opacity-50" : ""}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          {/* Status dot */}
          <span className={`shrink-0 h-2 w-2 rounded-full ${statusColor(agent.last_status)}`} />
          <span className="truncate text-sm font-medium text-zinc-100">{agent.name}</span>
          {disabled && (
            <span className="shrink-0 rounded bg-zinc-700 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-zinc-400">
              disabled
            </span>
          )}
        </div>
        <div className="shrink-0 flex items-center gap-2">
          {agent.last_run_ago && (
            <span className="text-[10px] text-zinc-500">{agent.last_run_ago}</span>
          )}
          <span className={`rounded px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wide
            ${agent.last_status === "ok"      ? "bg-emerald-500/10 text-emerald-400" :
              agent.last_status === "error"   ? "bg-red-500/10 text-red-400" :
              agent.last_status === "timeout" ? "bg-amber-500/10 text-amber-400" :
                                                "bg-zinc-700 text-zinc-500"}`}
          >
            {statusLabel(agent.last_status)}
          </span>
        </div>
      </div>

      <TaskBar tasks={agent.tasks} />

      {agent.blocked.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {agent.blocked.map((t) => (
            <span key={t} className="rounded bg-red-500/10 px-1.5 py-0.5 text-[10px] text-red-400">
              blocked: {t}
            </span>
          ))}
        </div>
      )}

      <OutputChips output={agent.last_output} />
    </div>
  );
}

export default function CoordinatorSection({ agents }: { agents: CoordinatorAgent[] }) {
  if (!agents || agents.length === 0) {
    return (
      <p className="text-sm text-zinc-500 italic">
        No roadmap.yaml files found — coordinator has not run yet.
      </p>
    );
  }

  const lastRun = agents
    .map((a) => a.last_run)
    .filter(Boolean)
    .sort()
    .at(-1);

  const errorCount   = agents.filter((a) => a.last_status === "error").length;
  const blockedCount = agents.reduce((n, a) => n + a.blocked.length, 0);

  return (
    <div className="rounded-xl border border-white/10 bg-white/5">
      <div className="pb-3 p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-zinc-100">
            Coordinator
          </h3>
          <div className="flex items-center gap-3 text-[11px] text-zinc-500">
            {errorCount > 0 && (
              <span className="text-red-400">{errorCount} error{errorCount > 1 ? "s" : ""}</span>
            )}
            {blockedCount > 0 && (
              <span className="text-amber-400">{blockedCount} blocked</span>
            )}
            {lastRun && (
              <span>last run: {new Date(lastRun).toLocaleString()}</span>
            )}
          </div>
        </div>
      </div>
      <div className="space-y-2 px-4 pb-4">
        {agents.map((agent) => (
          <AgentRow key={agent.id} agent={agent} />
        ))}
      </div>
    </div>
  );
}
