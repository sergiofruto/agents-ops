"use client";

import { Badge } from "@tremor/react";

type Mode = "LIVE" | "DRY RUN" | "OFFLINE";

export function StatusBadge({ mode }: { mode: Mode }) {
  if (mode === "LIVE")     return <Badge color="red">● LIVE</Badge>;
  if (mode === "DRY RUN")  return <Badge color="blue">○ DRY RUN</Badge>;
  return <Badge color="gray">○ OFFLINE</Badge>;
}
