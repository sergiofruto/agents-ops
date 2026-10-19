import { POSE_ORDER, POSES, type PoseId } from "./poses";

export type CheckSpecRow = {
  poseId: PoseId;
  pose: string;
  id: string;
  label: string;
  unit: "deg" | "ratio";
  target: string;
  tolerance: string;
  weight: number;
};

/** Every photo-mode check as a table row, generated from the scoring definitions. */
export function checkSpecRows(): CheckSpecRow[] {
  return POSE_ORDER.flatMap((poseId) =>
    POSES[poseId].checks
      .filter((c) => c.source === "frame")
      .map((c) => {
        const u = c.unit === "deg" ? "°" : "";
        return {
          poseId,
          pose: POSES[poseId].label,
          id: c.id,
          label: c.label,
          unit: c.unit,
          target: c.kind === "range" ? `${c.target}${u}` : `≥ ${c.min}${u}`,
          tolerance: c.kind === "range" ? `± ${c.tol}${u}` : "—",
          weight: c.weight,
        };
      }),
  );
}
