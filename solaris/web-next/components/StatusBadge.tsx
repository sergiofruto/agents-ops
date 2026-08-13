"use client";

import { Badge } from "@tremor/react";

type Mode = "LIVE" | "DRY RUN" | "OFFLINE";
type BetStatus = "open" | "won" | "lost" | "void";

const COLORS: Record<Mode | BetStatus, "red" | "blue" | "gray" | "emerald"> = {
  LIVE: "red",
  "DRY RUN": "blue",
  OFFLINE: "gray",
  open: "blue",
  won: "emerald",
  lost: "red",
  void: "gray",
};

const LABELS: Partial<Record<Mode, string>> = {
  LIVE: "● LIVE",
  "DRY RUN": "○ DRY RUN",
  OFFLINE: "○ OFFLINE",
};

export function StatusBadge({ status }: { status: Mode | BetStatus }) {
  return <Badge color={COLORS[status]}>{LABELS[status as Mode] ?? status}</Badge>;
}
