import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type BetStatus = "open" | "won" | "lost" | "void";
type AgentMode = "LIVE" | "DRY RUN" | "OFFLINE";

interface StatusBadgeProps {
  status: BetStatus | AgentMode | string;
  className?: string;
}

const betStatusStyles: Record<string, string> = {
  open: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  won: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  lost: "bg-red-500/20 text-red-300 border-red-500/30",
  void: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
  LIVE: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  "DRY RUN": "bg-amber-500/20 text-amber-300 border-amber-500/30",
  OFFLINE: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const style = betStatusStyles[status] ?? "bg-zinc-500/20 text-zinc-400 border-zinc-500/30";
  return (
    <Badge
      variant="outline"
      className={cn("text-xs font-medium border", style, className)}
    >
      {status}
    </Badge>
  );
}
