import { downdog } from "./downdog";
import { tree } from "./tree";
import type { PoseDef, PoseId } from "./types";
import { warrior2 } from "./warrior2";

export const POSES: Record<PoseId, PoseDef> = { warrior2, tree, downdog };

/** Display order used across the UI and reports. */
export const POSE_ORDER: PoseId[] = ["warrior2", "tree", "downdog"];

export type { CheckDef, Mode, PoseDef, PoseId, Roles } from "./types";
