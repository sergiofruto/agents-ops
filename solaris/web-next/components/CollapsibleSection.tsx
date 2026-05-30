"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

interface CollapsibleSectionProps {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  className?: string;
  headerExtra?: React.ReactNode;
}

export default function CollapsibleSection({
  title,
  defaultOpen = true,
  children,
  className,
  headerExtra,
}: CollapsibleSectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={cn("w-full", className)} style={{ borderTop: "1px solid #222222", paddingTop: "24px", marginTop: "24px" }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between transition-colors group"
        style={{ marginBottom: open ? "20px" : "0" }}
      >
        <div className="flex items-center gap-4">
          <span
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "11px",
              fontWeight: 400,
              letterSpacing: "0.08em",
              color: open ? "#E8E8E8" : "#666666",
              transition: "color 150ms",
            }}
          >
            {title.toUpperCase()}
          </span>
          {headerExtra}
        </div>
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "11px",
            color: "#666666",
            letterSpacing: "0.04em",
            transition: "color 150ms",
          }}
          className="group-hover:text-white"
        >
          {open ? "[ − ]" : "[ + ]"}
        </span>
      </button>
      {open && <div>{children}</div>}
    </div>
  );
}
