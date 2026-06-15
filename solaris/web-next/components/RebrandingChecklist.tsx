"use client";

import { useState, useEffect } from "react";
import { ProgressBar } from "@tremor/react";

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
      try { setChecked(JSON.parse(saved)); } catch { /* ignore */ }
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
    <div className="bg-[#0f1a2e] border border-[#1e3a5f] rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11.5px] font-medium text-[#60a5fa] tracking-[0.06em] uppercase">
          Rebranding Checklist
        </span>
        <span className="text-[11.5px] text-[#475569]">{done}/{total}</span>
      </div>
      <ProgressBar value={Math.round((done / total) * 100)} color="blue" className="mb-4" />
      <div className="flex flex-col gap-1">
        {ITEMS.map((item) => (
          <label
            key={item}
            className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-1.5 hover:bg-[#0a1628] transition-colors"
          >
            <input
              type="checkbox"
              checked={!!checked[item]}
              onChange={() => toggle(item)}
              className="h-4 w-4 rounded border-[#1e3a5f] bg-[#0a1628] accent-[#60a5fa]"
            />
            <span className={`text-[13px] ${checked[item] ? "line-through text-[#475569]" : "text-[#94a3b8]"}`}>
              {item}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
