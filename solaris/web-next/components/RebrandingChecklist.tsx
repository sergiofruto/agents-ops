"use client";

import { useState, useEffect } from "react";

const CHECKLIST_KEY = "solaris_rebranding_checklist";

const ITEMS = [
  "Update LinkedIn profile",
  "Update GitHub profile",
  "Update resume header",
  "Update portfolio site",
  "Update email signature",
  "Notify professional network",
];

export default function RebrandingChecklist() {
  const [checked, setChecked] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const saved = localStorage.getItem(CHECKLIST_KEY);
    if (saved) {
      try {
        setChecked(JSON.parse(saved));
      } catch {
        // ignore
      }
    }
  }, []);

  function toggle(item: string) {
    const next = { ...checked, [item]: !checked[item] };
    setChecked(next);
    localStorage.setItem(CHECKLIST_KEY, JSON.stringify(next));
  }

  const done = Object.values(checked).filter(Boolean).length;
  const total = ITEMS.length;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-3">
        <div className="h-1.5 flex-1 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full rounded-full bg-violet-500 transition-all"
            style={{ width: `${(done / total) * 100}%` }}
          />
        </div>
        <span className="text-xs text-zinc-400 whitespace-nowrap">
          {done}/{total}
        </span>
      </div>
      {ITEMS.map((item) => (
        <label
          key={item}
          className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 hover:bg-white/5 transition-colors"
        >
          <input
            type="checkbox"
            checked={!!checked[item]}
            onChange={() => toggle(item)}
            className="h-4 w-4 rounded border-zinc-600 bg-zinc-800 accent-violet-500"
          />
          <span
            className={`text-sm ${
              checked[item] ? "line-through text-zinc-500" : "text-zinc-200"
            }`}
          >
            {item}
          </span>
        </label>
      ))}
    </div>
  );
}
