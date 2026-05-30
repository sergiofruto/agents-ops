"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { GoodMorningReport } from "@/lib/types";

const GM_KEY = "solaris_gm_date";

const QUOTES = [
  "Ship it, iterate, improve.",
  "Consistency beats intensity.",
  "One small step every day.",
  "Progress over perfection.",
  "Build momentum, not excuses.",
];

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

interface WaterTrackerProps {
  cups: number;
  onToggle: (i: number) => void;
}

function WaterTracker({ cups, onToggle }: WaterTrackerProps) {
  return (
    <div className="space-y-1">
      <p className="text-xs uppercase tracking-wide text-zinc-500">Hydration</p>
      <div className="flex gap-1.5">
        {Array.from({ length: 8 }, (_, i) => (
          <button
            key={i}
            onClick={() => onToggle(i)}
            className={`h-8 w-8 rounded-md text-lg transition-colors ${
              i < cups ? "bg-blue-500/30 text-blue-300" : "bg-white/5 text-zinc-600"
            }`}
            title={`Cup ${i + 1}`}
          >
            💧
          </button>
        ))}
      </div>
      <p className="text-xs text-zinc-400">{cups}/8 cups</p>
    </div>
  );
}

export default function GoodMorningModal() {
  const [open, setOpen] = useState(false);
  const [report, setReport] = useState<GoodMorningReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [cups, setCups] = useState(0);
  const [runningAgent, setRunningAgent] = useState<string | null>(null);

  const WATER_KEY = `solaris_water_${todayKey()}`;

  useEffect(() => {
    const lastGm = localStorage.getItem(GM_KEY);
    const today = todayKey();
    if (lastGm !== today) {
      setOpen(true);
      localStorage.setItem(GM_KEY, today);
    }
    const saved = localStorage.getItem(WATER_KEY);
    if (saved) setCups(Number(saved));
  }, [WATER_KEY]);

  useEffect(() => {
    if (open && !report) {
      setLoading(true);
      fetch("/api/good-morning")
        .then((r) => r.json())
        .then(setReport)
        .finally(() => setLoading(false));
    }
  }, [open, report]);

  function toggleCup(i: number) {
    const next = i < cups ? i : i + 1;
    setCups(next);
    localStorage.setItem(WATER_KEY, String(next));
  }

  async function runTask(agent: string, action: string) {
    setRunningAgent(agent);
    if (action === "start") {
      await fetch(`/api/good-morning/start/${agent}`, { method: "POST" });
    } else if (action === "backtest") {
      await fetch("/api/good-morning/backtest", { method: "POST" });
    }
    setRunningAgent(null);
  }

  const quote = QUOTES[new Date().getDate() % QUOTES.length];

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen(true)}
        className="text-amber-300 hover:text-amber-200 hover:bg-amber-500/10"
      >
        ☀️ Good Morning
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="bg-zinc-900 border-white/10 text-zinc-100 max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-amber-300">
              ☀️ Good Morning{report ? ` — ${report.date}` : ""}
            </DialogTitle>
          </DialogHeader>

          {loading ? (
            <p className="text-sm text-zinc-400 py-4 text-center">Loading…</p>
          ) : report ? (
            <div className="space-y-5 mt-2">
              {/* Tasks */}
              {report.tasks.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-wide text-zinc-500">Tasks</p>
                  {report.tasks.map((t, i) => (
                    <div key={i} className="flex items-center justify-between rounded-md bg-white/5 px-3 py-2">
                      <span className="text-sm text-zinc-200">{t.label}</span>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={runningAgent === t.agent}
                        onClick={() => runTask(t.agent, t.action)}
                        className="border-violet-500/40 text-violet-300 hover:bg-violet-500/10 text-xs"
                      >
                        {runningAgent === t.agent ? "Starting…" : "Run"}
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              {/* Agent status */}
              <div className="space-y-1">
                <p className="text-xs uppercase tracking-wide text-zinc-500">Agent Status</p>
                <div className="flex gap-3">
                  {Object.entries(report.agent_status).map(([name, running]) => (
                    <div key={name} className="flex items-center gap-2 rounded-md bg-white/5 px-3 py-2">
                      <span
                        className={`h-2 w-2 rounded-full ${
                          running ? "bg-emerald-400" : "bg-red-500"
                        }`}
                      />
                      <span className="text-sm capitalize text-zinc-300">{name}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Overnight activity */}
              <div className="space-y-1">
                <p className="text-xs uppercase tracking-wide text-zinc-500">Overnight Activity</p>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(report.overnight).map(([agent, stats]) => (
                    <div key={agent} className="rounded-md bg-white/5 px-3 py-2">
                      <p className="text-xs font-medium capitalize text-zinc-400 mb-1">{agent}</p>
                      {stats.available ? (
                        <div className="space-y-0.5 text-xs">
                          <p className="text-zinc-300">New bets: {stats.new_bets}</p>
                          <p className="text-zinc-300">Won: {stats.won} · Lost: {stats.lost}</p>
                          <p className={stats.pnl! >= 0 ? "text-emerald-400" : "text-red-400"}>
                            P&L: ${stats.pnl?.toFixed(2)}
                          </p>
                        </div>
                      ) : (
                        <p className="text-xs text-zinc-600 italic">Offline</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Water tracker */}
              <WaterTracker cups={cups} onToggle={toggleCup} />

              {/* Daily quote */}
              <div className="rounded-md bg-white/5 px-4 py-3 text-sm italic text-zinc-400 border-l-2 border-violet-500/50">
                "{quote}"
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  );
}
