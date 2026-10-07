import { POSES, type PoseId } from "./poses";
import { targetText } from "./score";

export type PoseSummary = {
  id: PoseId;
  label: string;
  viewLabel: string;
  checks: { id: string; label: string; target: string | null }[];
};

const ORDER: PoseId[] = ["warrior2", "tree", "downdog"];

export function viewLabel(view: "front" | "side"): string {
  return view === "front" ? "Facing the camera" : "Side view";
}

/** Human-facing summary of each pose's photo-mode checks, derived from the scoring definitions. */
export function poseSummaries(): PoseSummary[] {
  return ORDER.map((id) => {
    const pose = POSES[id];
    return {
      id,
      label: pose.label,
      viewLabel: viewLabel(pose.view),
      checks: pose.checks
        .filter((c) => c.source === "frame")
        .map((c) => ({ id: c.id, label: c.label, target: c.unit === "deg" ? targetText(c) : null })),
    };
  });
}
