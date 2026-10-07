import type { PoseId } from "@/lib/poses";

export type Iteration = {
  id: number;
  date: string;
  device: string;
  note: string;
  /** Landmark file id (key of LANDMARK_FILES) per pose. */
  samples: Record<PoseId, string>;
};

/** Photo iterations of Sergio's practice. Append a new entry (and landmark files) per reshoot. */
export const ITERATIONS: Iteration[] = [
  {
    id: 1,
    date: "2026-10-01",
    device: "DJI Osmo Pocket 3",
    note: "Intentionally imperfect form: the baseline to improve on.",
    samples: { warrior2: "warrior2", tree: "tree", downdog: "downdog" },
  },
];
